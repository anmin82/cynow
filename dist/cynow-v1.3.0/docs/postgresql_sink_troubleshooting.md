# PostgreSQL Sink Connector Task 실패 문제 해결 가이드

## 문제 상황

- ✅ Oracle → Kafka (Debezium Source Connector): 정상 작동
- ❌ Kafka → PostgreSQL (JDBC Sink Connector): Task가 계속 죽어버림

## 1. 문제 진단

### 1.1 Sink Connector 상태 확인

```bash
# 모든 커넥터 목록 확인
curl -s http://localhost:8083/connectors | jq

# Sink 커넥터 이름 확인 (예: postgresql-sink-fcms)
# 커넥터 상태 확인
curl -s http://localhost:8083/connectors/postgresql-sink-fcms/status | jq

# 커넥터 설정 확인
curl -s http://localhost:8083/connectors/postgresql-sink-fcms/config | jq

# Task 오류 상세 확인
curl -s http://localhost:8083/connectors/postgresql-sink-fcms/status | jq '.tasks[].trace'
```

### 1.2 Kafka Connect 로그 확인

```bash
# Docker를 사용하는 경우
docker logs kafka-connect | grep -i error
docker logs kafka-connect | grep -i "postgresql-sink"

# 또는 Kafka Connect 서버 로그 직접 확인
# 일반적으로 /var/log/kafka-connect/ 또는 stdout
```

### 1.3 PostgreSQL 연결 확인

```bash
# PostgreSQL 연결 테스트
psql -h 10.78.30.98 -p 5434 -U postgres -d cynow

# 또는 Django 명령어 사용
python manage.py test_db_connection
```

## 2. 일반적인 원인 및 해결 방법

### 2.0 스키마 진화 실패 (가장 흔한 문제) ⚠️

**증상**: 
```
Cannot ALTER table 'fcms.ma_cylinders' because field 'WITHSTAND_PRESSURE_MAINTE_DATE' is not optional but has no default value
Cannot ALTER table 'fcms.tr_cylinder_status_histories' because field 'PROGRAM_ID' is not optional but has no default value
```

**원인**: Debezium JDBC Sink Connector가 `auto.evolve=true`일 때, Oracle에서 새 필드가 추가되면 PostgreSQL 테이블에 자동으로 추가하려고 시도합니다. 하지만 NOT NULL이고 기본값이 없는 필드는 기존 레코드에 값을 넣을 수 없어서 ALTER TABLE이 실패합니다.

**해결 방법 1: auto.evolve 비활성화 (권장 - 빠른 해결)**

```bash
# 실패한 커넥터들의 설정 확인
curl -s http://localhost:8083/connectors/sink_dev_ma_cylinders/config | jq
curl -s http://localhost:8083/connectors/sink_dev_tr_cylinder_status_histories/config | jq
curl -s http://localhost:8083/connectors/sink_dev_tr_latest_cylinder_statuses/config | jq

# auto.evolve를 false로 변경
curl -X PUT http://localhost:8083/connectors/sink_dev_ma_cylinders/config \
  -H "Content-Type: application/json" \
  -d '{
    "auto.evolve": "false"
  }'

curl -X PUT http://localhost:8083/connectors/sink_dev_tr_cylinder_status_histories/config \
  -H "Content-Type: application/json" \
  -d '{
    "auto.evolve": "false"
  }'

curl -X PUT http://localhost:8083/connectors/sink_dev_tr_latest_cylinder_statuses/config \
  -H "Content-Type: application/json" \
  -d '{
    "auto.evolve": "false"
  }'

# Task 재시작
curl -X POST http://localhost:8083/connectors/sink_dev_ma_cylinders/tasks/0/restart
curl -X POST http://localhost:8083/connectors/sink_dev_tr_cylinder_status_histories/tasks/0/restart
curl -X POST http://localhost:8083/connectors/sink_dev_tr_latest_cylinder_statuses/tasks/0/restart
```

**해결 방법 2: PostgreSQL에서 필드 수정 (영구 해결)**

```sql
-- PostgreSQL에 접속하여 해당 필드를 NULL 허용으로 변경
-- 또는 기본값 설정

-- 예시 1: NULL 허용으로 변경
ALTER TABLE fcms.ma_cylinders 
  ALTER COLUMN "WITHSTAND_PRESSURE_MAINTE_DATE" DROP NOT NULL;

ALTER TABLE fcms.tr_cylinder_status_histories 
  ALTER COLUMN "PROGRAM_ID" DROP NOT NULL;

ALTER TABLE fcms.tr_latest_cylinder_statuses 
  ALTER COLUMN "PROGRAM_ID" DROP NOT NULL;

-- 예시 2: 기본값 설정
ALTER TABLE fcms.ma_cylinders 
  ALTER COLUMN "WITHSTAND_PRESSURE_MAINTE_DATE" SET DEFAULT NULL;

ALTER TABLE fcms.tr_cylinder_status_histories 
  ALTER COLUMN "PROGRAM_ID" SET DEFAULT '';

ALTER TABLE fcms.tr_latest_cylinder_statuses 
  ALTER COLUMN "PROGRAM_ID" SET DEFAULT '';
```

**해결 방법 3: 일괄 수정 스크립트**

```bash
#!/bin/bash
# fix_schema_evolution.sh

CONNECT_URL="http://localhost:8083"
FAILED_CONNECTORS=(
  "sink_dev_ma_cylinders"
  "sink_dev_tr_cylinder_status_histories"
  "sink_dev_tr_latest_cylinder_statuses"
)

for connector in "${FAILED_CONNECTORS[@]}"; do
  echo "Fixing $connector..."
  
  # 현재 설정 가져오기
  CONFIG=$(curl -s "$CONNECT_URL/connectors/$connector/config")
  
  # auto.evolve를 false로 변경
  echo "$CONFIG" | jq '. + {"auto.evolve": "false"}' | \
    curl -X PUT "$CONNECT_URL/connectors/$connector/config" \
      -H "Content-Type: application/json" \
      -d @-
  
  # Task 재시작
  curl -X POST "$CONNECT_URL/connectors/$connector/tasks/0/restart"
  
  echo "Fixed $connector"
done
```

### 2.1 스키마 불일치 문제

**증상**: Debezium이 생성한 스키마와 PostgreSQL 테이블 스키마가 맞지 않음

**해결 방법**:

```bash
# 1. Debezium이 생성한 Kafka topic의 스키마 확인
# Schema Registry가 있는 경우
curl -s http://localhost:8081/subjects/fcms.FCMS.MA_CYLINDERS-value/versions/latest | jq

# 2. PostgreSQL 테이블 스키마 확인
psql -h 10.78.30.98 -p 5434 -U postgres -d cynow -c "\d \"FCMS\".\"MA_CYLINDERS\""

# 3. Sink Connector에 auto.create 설정 추가
curl -X PUT http://localhost:8083/connectors/postgresql-sink-fcms/config \
  -H "Content-Type: application/json" \
  -d '{
    "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
    "connection.url": "jdbc:postgresql://10.78.30.98:5434/cynow",
    "connection.user": "postgres",
    "connection.password": "postgres",
    "topics": "fcms.FCMS.MA_CYLINDERS,fcms.FCMS.MA_CYLINDER_SPECS,fcms.FCMS.MA_VALVE_SPECS,fcms.FCMS.TR_LATEST_CYLINDER_STATUSES,fcms.FCMS.MA_ITEMS,fcms.FCMS.MA_PARAMETERS,fcms.FCMS.TR_CYLINDER_STATUS_HISTORIES",
    "auto.create": "true",
    "auto.evolve": "true",
    "insert.mode": "upsert",
    "pk.mode": "record_value",
    "pk.fields": "__debezium_source_ts_ms",
    "table.name.format": "${topic}",
    "transforms": "unwrap,route",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.unwrap.drop.tombstones": "false",
    "transforms.unwrap.delete.handling.mode": "rewrite",
    "transforms.route.type": "org.apache.kafka.connect.transforms.RegexRouter",
    "transforms.route.regex": "fcms\\.FCMS\\.(.*)",
    "transforms.route.replacement": "$1"
  }'
```

### 2.2 메모리 부족 문제

**증상**: Task가 OOM(Out of Memory)으로 죽음

**해결 방법**:

```bash
# 1. Kafka Connect JVM 메모리 증가
# connect-distributed.properties 또는 환경 변수
export KAFKA_HEAP_OPTS="-Xmx2G -Xms1G"

# 2. 배치 크기 줄이기
curl -X PUT http://localhost:8083/connectors/postgresql-sink-fcms/config \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
  "connection.url": "jdbc:postgresql://10.78.30.98:5434/cynow",
  "connection.user": "postgres",
  "connection.password": "postgres",
  "batch.size": "100",
  "max.retries": "10",
  "retry.backoff.ms": "3000"
}
EOF
```

### 2.3 연결 타임아웃 문제

**증상**: PostgreSQL 연결이 타임아웃되어 Task 실패

**해결 방법**:

```bash
curl -X PUT http://localhost:8083/connectors/postgresql-sink-fcms/config \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
  "connection.url": "jdbc:postgresql://10.78.30.98:5434/cynow?connectTimeout=30&socketTimeout=60",
  "connection.user": "postgres",
  "connection.password": "postgres",
  "connection.attempts": "3",
  "connection.backoff.ms": "10000"
}
EOF
```

### 2.4 트랜잭션 및 데드락 문제

**증상**: PostgreSQL에서 데드락 또는 트랜잭션 충돌

**해결 방법**:

```bash
curl -X PUT http://localhost:8083/connectors/postgresql-sink-fcms/config \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
  "connection.url": "jdbc:postgresql://10.78.30.98:5434/cynow",
  "connection.user": "postgres",
  "connection.password": "postgres",
  "db.timezone": "UTC",
  "max.retries": "10",
  "retry.backoff.ms": "5000",
  "errors.tolerance": "all",
  "errors.log.enable": "true",
  "errors.log.include.messages": "true"
}
EOF
```

### 2.5 Debezium 스키마 변환 문제

**증상**: Debezium이 생성한 복잡한 스키마를 PostgreSQL로 변환 실패

**해결 방법**: SMT(Single Message Transform) 사용

```bash
curl -X PUT http://localhost:8083/connectors/postgresql-sink-fcms/config \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
  "connection.url": "jdbc:postgresql://10.78.30.98:5434/cynow",
  "connection.user": "postgres",
  "connection.password": "postgres",
  "topics": "fcms.FCMS.MA_CYLINDERS,fcms.FCMS.MA_CYLINDER_SPECS,fcms.FCMS.MA_VALVE_SPECS,fcms.FCMS.TR_LATEST_CYLINDER_STATUSES,fcms.FCMS.MA_ITEMS,fcms.FCMS.MA_PARAMETERS,fcms.FCMS.TR_CYLINDER_STATUS_HISTORIES",
  "auto.create": "true",
  "auto.evolve": "true",
  "insert.mode": "upsert",
  "pk.mode": "record_value",
  "pk.fields": "CYLINDER_NO",
  "table.name.format": "\${topic}",
  "transforms": "unwrap,route,flatten",
  "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
  "transforms.unwrap.drop.tombstones": "false",
  "transforms.unwrap.delete.handling.mode": "rewrite",
  "transforms.route.type": "org.apache.kafka.connect.transforms.RegexRouter",
  "transforms.route.regex": "fcms\\\\.FCMS\\\\.(.*)",
  "transforms.route.replacement": "\$1",
  "transforms.flatten.type": "org.apache.kafka.connect.transforms.Flatten\$Value",
  "transforms.flatten.delimiter": "_"
}
EOF
```

### 2.6 테이블명 대소문자 문제

**증상**: PostgreSQL에서 대소문자 구분으로 인한 테이블/컬럼 찾기 실패

**해결 방법**:

```bash
# 테이블명을 소문자로 변환하는 SMT 추가
curl -X PUT http://localhost:8083/connectors/postgresql-sink-fcms/config \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
  "connection.url": "jdbc:postgresql://10.78.30.98:5434/cynow",
  "connection.user": "postgres",
  "connection.password": "postgres",
  "table.name.format": "\${topic}",
  "transforms": "unwrap,route,lowercase",
  "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
  "transforms.route.type": "org.apache.kafka.connect.transforms.RegexRouter",
  "transforms.route.regex": "fcms\\\\.FCMS\\\\.(.*)",
  "transforms.route.replacement": "\$1",
  "transforms.lowercase.type": "org.apache.kafka.connect.transforms.RegexRouter",
  "transforms.lowercase.regex": "(.*)",
  "transforms.lowercase.replacement": "\${1,,}"
}
EOF
```

## 3. 권장 Sink Connector 설정 (완전한 예시)

```bash
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "name": "postgresql-sink-fcms",
  "config": {
    "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
    "tasks.max": "1",
    "connection.url": "jdbc:postgresql://10.78.30.98:5434/cynow",
    "connection.user": "postgres",
    "connection.password": "postgres",
    "topics": "fcms.FCMS.MA_CYLINDERS,fcms.FCMS.MA_CYLINDER_SPECS,fcms.FCMS.MA_VALVE_SPECS,fcms.FCMS.TR_LATEST_CYLINDER_STATUSES,fcms.FCMS.MA_ITEMS,fcms.FCMS.MA_PARAMETERS,fcms.FCMS.TR_CYLINDER_STATUS_HISTORIES",
    "auto.create": "true",
    "auto.evolve": "true",
    "insert.mode": "upsert",
    "pk.mode": "record_value",
    "pk.fields": "CYLINDER_NO",
    "table.name.format": "\${topic}",
    "batch.size": "3000",
    "max.retries": "10",
    "retry.backoff.ms": "3000",
    "connection.attempts": "3",
    "connection.backoff.ms": "10000",
    "errors.tolerance": "all",
    "errors.log.enable": "true",
    "errors.log.include.messages": "true",
    "errors.deadletterqueue.topic.name": "dlq-postgresql-sink-fcms",
    "errors.deadletterqueue.topic.replication.factor": "1",
    "transforms": "unwrap,route",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.unwrap.drop.tombstones": "false",
    "transforms.unwrap.delete.handling.mode": "rewrite",
    "transforms.route.type": "org.apache.kafka.connect.transforms.RegexRouter",
    "transforms.route.regex": "fcms\\\\.FCMS\\\\.(.*)",
    "transforms.route.replacement": "\$1"
  }
}
EOF
```

## 4. 문제 해결 체크리스트

- [ ] Sink Connector 상태 확인 (`/status` 엔드포인트)
- [ ] Task 오류 메시지 확인 (`trace` 필드)
- [ ] Kafka Connect 로그에서 상세 오류 확인
- [ ] PostgreSQL 연결 테스트
- [ ] PostgreSQL 테이블 존재 여부 확인
- [ ] 스키마 일치 여부 확인 (Kafka Schema Registry vs PostgreSQL)
- [ ] 메모리 사용량 확인 (JVM 힙 메모리)
- [ ] 네트워크 연결 확인 (방화벽, 포트)
- [ ] PostgreSQL 로그 확인 (데드락, 트랜잭션 오류)
- [ ] Kafka topic에 데이터가 있는지 확인

## 5. 커넥터 재시작 및 복구

```bash
# 1. 커넥터 일시 정지
curl -X PUT http://localhost:8083/connectors/postgresql-sink-fcms/pause

# 2. 설정 수정 (위의 해결 방법 중 하나 적용)

# 3. 커넥터 재개
curl -X PUT http://localhost:8083/connectors/postgresql-sink-fcms/resume

# 4. 특정 Task 재시작
curl -X POST http://localhost:8083/connectors/postgresql-sink-fcms/tasks/0/restart

# 5. 전체 커넥터 재시작
curl -X POST http://localhost:8083/connectors/postgresql-sink-fcms/restart

# 6. 커넥터 삭제 후 재생성 (최후의 수단)
curl -X DELETE http://localhost:8083/connectors/postgresql-sink-fcms
# 그 다음 위의 권장 설정으로 재생성
```

## 6. 모니터링 및 알림

### 6.1 커넥터 상태 모니터링 스크립트

```bash
#!/bin/bash
# check_sink_connector.sh

CONNECTOR_NAME="postgresql-sink-fcms"
CONNECT_URL="http://localhost:8083"

STATUS=$(curl -s "$CONNECT_URL/connectors/$CONNECTOR_NAME/status" | jq -r '.connector.state')
TASK_COUNT=$(curl -s "$CONNECT_URL/connectors/$CONNECTOR_NAME/status" | jq '.tasks | length')

echo "Connector: $CONNECTOR_NAME"
echo "Status: $STATUS"
echo "Tasks: $TASK_COUNT"

if [ "$STATUS" != "RUNNING" ]; then
    echo "ERROR: Connector is not running!"
    exit 1
fi

for i in $(seq 0 $((TASK_COUNT - 1))); do
    TASK_STATE=$(curl -s "$CONNECT_URL/connectors/$CONNECTOR_NAME/status" | jq -r ".tasks[$i].state")
    echo "Task $i: $TASK_STATE"
    
    if [ "$TASK_STATE" != "RUNNING" ]; then
        echo "ERROR: Task $i is not running!"
        curl -s "$CONNECT_URL/connectors/$CONNECTOR_NAME/status" | jq ".tasks[$i].trace"
        exit 1
    fi
done

echo "All tasks are running successfully"
```

## 7. 추가 리소스

- [Confluent JDBC Sink Connector 문서](https://docs.confluent.io/kafka-connect-jdbc/current/sink-connector/index.html)
- [Debezium PostgreSQL Sink 가이드](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html)
- [Kafka Connect REST API](https://docs.confluent.io/platform/current/connect/references/restapi.html)












