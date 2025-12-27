# 스키마 진화 실패 문제 해결 가이드

## 문제

Debezium JDBC Sink Connector의 Task가 다음 오류로 실패합니다:

```
Cannot ALTER table 'fcms.ma_cylinders' because field 'WITHSTAND_PRESSURE_MAINTE_DATE' is not optional but has no default value
Cannot ALTER table 'fcms.tr_cylinder_status_histories' because field 'PROGRAM_ID' is not optional but has no default value
Cannot ALTER table 'fcms.tr_latest_cylinder_statuses' because field 'PROGRAM_ID' is not optional but has no default value
```

## 원인

Debezium JDBC Sink Connector가 `auto.evolve=true`로 설정되어 있을 때, Oracle 소스 테이블에 새 필드가 추가되면 PostgreSQL 테이블에도 자동으로 추가하려고 시도합니다. 하지만:

1. 새 필드가 NOT NULL 제약 조건을 가지고 있고
2. 기본값이 없는 경우
3. 기존 레코드에 값을 넣을 수 없어서 ALTER TABLE이 실패합니다

## 해결 방법

### 방법 1: auto.evolve 비활성화 (가장 빠른 해결) ⚡

**장점**: 즉시 문제 해결, 추가 작업 불필요  
**단점**: 스키마 변경 시 수동으로 PostgreSQL 테이블을 업데이트해야 함

```bash
# 실패한 커넥터 확인
curl -s http://localhost:8083/connectors | jq -r '.[]' | while read c; do
  STATE=$(curl -s http://localhost:8083/connectors/$c/status | jq -r '.tasks[0].state // "UNKNOWN"')
  if [ "$STATE" = "FAILED" ]; then
    echo "Failed: $c"
  fi
done

# 개별 수정
curl -X PUT http://localhost:8083/connectors/sink_dev_ma_cylinders/config \
  -H "Content-Type: application/json" \
  -d '{"auto.evolve": "false"}'

curl -X PUT http://localhost:8083/connectors/sink_dev_tr_cylinder_status_histories/config \
  -H "Content-Type: application/json" \
  -d '{"auto.evolve": "false"}'

curl -X PUT http://localhost:8083/connectors/sink_dev_tr_latest_cylinder_statuses/config \
  -H "Content-Type: application/json" \
  -d '{"auto.evolve": "false"}'

# Task 재시작
curl -X POST http://localhost:8083/connectors/sink_dev_ma_cylinders/tasks/0/restart
curl -X POST http://localhost:8083/connectors/sink_dev_tr_cylinder_status_histories/tasks/0/restart
curl -X POST http://localhost:8083/connectors/sink_dev_tr_latest_cylinder_statuses/tasks/0/restart
```

### 방법 2: 자동 수정 스크립트 사용 🚀

```bash
# 스크립트에 실행 권한 부여
chmod +x scripts/fix_schema_evolution.sh

# 실행
./scripts/fix_schema_evolution.sh

# 또는 Connect URL 지정
KAFKA_CONNECT_URL=http://localhost:8083 ./scripts/fix_schema_evolution.sh
```

### 방법 3: PostgreSQL에서 필드 수정 (영구 해결) 🔧

**장점**: 스키마 진화 기능 유지 가능  
**단점**: PostgreSQL 접근 권한 필요, 수동 작업 필요

#### 옵션 3-1: NULL 허용으로 변경

```sql
-- PostgreSQL에 접속
psql -h 10.78.30.98 -p 5434 -U postgres -d cynow

-- NULL 허용으로 변경
ALTER TABLE fcms.ma_cylinders 
  ALTER COLUMN "WITHSTAND_PRESSURE_MAINTE_DATE" DROP NOT NULL;

ALTER TABLE fcms.tr_cylinder_status_histories 
  ALTER COLUMN "PROGRAM_ID" DROP NOT NULL;

ALTER TABLE fcms.tr_latest_cylinder_statuses 
  ALTER COLUMN "PROGRAM_ID" DROP NOT NULL;
```

#### 옵션 3-2: 기본값 설정

```sql
-- 기본값 설정 (NULL)
ALTER TABLE fcms.ma_cylinders 
  ALTER COLUMN "WITHSTAND_PRESSURE_MAINTE_DATE" SET DEFAULT NULL;

-- 기본값 설정 (빈 문자열)
ALTER TABLE fcms.tr_cylinder_status_histories 
  ALTER COLUMN "PROGRAM_ID" SET DEFAULT '';

ALTER TABLE fcms.tr_latest_cylinder_statuses 
  ALTER COLUMN "PROGRAM_ID" SET DEFAULT '';

-- 또는 적절한 기본값 설정
ALTER TABLE fcms.tr_cylinder_status_histories 
  ALTER COLUMN "PROGRAM_ID" SET DEFAULT 'SYSTEM';
```

#### 옵션 3-3: 기존 레코드에 값 채우기 후 NOT NULL 유지

```sql
-- 1. 먼저 NULL 허용으로 변경
ALTER TABLE fcms.ma_cylinders 
  ALTER COLUMN "WITHSTAND_PRESSURE_MAINTE_DATE" DROP NOT NULL;

-- 2. 기존 레코드에 기본값 채우기
UPDATE fcms.ma_cylinders 
SET "WITHSTAND_PRESSURE_MAINTE_DATE" = CURRENT_DATE 
WHERE "WITHSTAND_PRESSURE_MAINTE_DATE" IS NULL;

-- 3. 다시 NOT NULL로 변경
ALTER TABLE fcms.ma_cylinders 
  ALTER COLUMN "WITHSTAND_PRESSURE_MAINTE_DATE" SET NOT NULL;
```

### 방법 4: Django Management Command 사용 🐍

```bash
# 진단 및 자동 수정
python manage.py check_kafka_sink --fix

# 특정 커넥터만 확인
python manage.py check_kafka_sink --connector-name sink_dev_ma_cylinders
```

## 검증

수정 후 커넥터 상태 확인:

```bash
# 모든 커넥터 상태 확인
curl -s http://localhost:8083/connectors | jq -r '.[]' | while read c; do
  echo "===== $c ====="
  curl -s http://localhost:8083/connectors/$c/status | jq '.tasks[].state'
done

# 특정 커넥터 상세 확인
curl -s http://localhost:8083/connectors/sink_dev_ma_cylinders/status | jq
```

## 예방 방법

### 1. auto.evolve 비활성화 (권장)

새 커넥터 생성 시:

```json
{
  "connector.class": "io.debezium.connector.jdbc.JdbcSinkConnector",
  "auto.evolve": "false",
  ...
}
```

### 2. 스키마 변경 프로세스 수립

Oracle 테이블에 새 필드를 추가할 때:

1. **NOT NULL 필드 추가 시**:
   - 기본값을 함께 지정하거나
   - 기존 레코드에 값을 채운 후 NOT NULL 제약 추가

2. **PostgreSQL 동기화**:
   - 수동으로 PostgreSQL 테이블에 필드 추가
   - 또는 `auto.evolve=true` 사용 시 NULL 허용/기본값 설정

### 3. 모니터링 설정

```bash
# 정기적으로 커넥터 상태 확인 (cron 등)
*/5 * * * * curl -s http://localhost:8083/connectors | jq -r '.[]' | while read c; do STATE=$(curl -s http://localhost:8083/connectors/$c/status | jq -r '.tasks[0].state'); if [ "$STATE" = "FAILED" ]; then echo "ALERT: $c is FAILED" | mail -s "Kafka Connector Alert" admin@example.com; fi; done
```

## 관련 문서

- [PostgreSQL Sink Connector 전체 문제 해결 가이드](postgresql_sink_troubleshooting.md)
- [빠른 해결 가이드](KAFKA_SINK_QUICK_FIX.md)












