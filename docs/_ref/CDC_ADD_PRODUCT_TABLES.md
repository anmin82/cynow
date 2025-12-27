# 🔧 CDC 제품코드 테이블 추가 가이드

## 📋 현재 환경

| 구성요소 | 정보 |
|---------|------|
| Kafka Connect | `http://localhost:8083` (container: `debezium-oracle-connect`) |
| Source Connector | `oracle-fcms-cylcy-main-v4` |
| Topic Prefix | `fcms` → `fcms.FCMS.테이블명` |
| Oracle | `10.78.30.18:1521`, DB: `FCMSDB`, Schema: `FCMS` |
| PostgreSQL Sink | `jdbc:postgresql://10.78.30.98:5434/cycy_db` |

---

## 📊 추가할 테이블

| Oracle 테이블 | Kafka Topic | PostgreSQL 테이블 |
|--------------|-------------|-------------------|
| `FCMS.MA_SELECTION_PATTERNS` | `fcms.FCMS.MA_SELECTION_PATTERNS` | `fcms_cdc.ma_selection_patterns` |
| `FCMS.MA_SELECTION_PATTERN_DETAILS` | `fcms.FCMS.MA_SELECTION_PATTERN_DETAILS` | `fcms_cdc.ma_selection_pattern_details` |

### 주요 컬럼

**MA_SELECTION_PATTERNS** (제품코드 마스터)
```
SELECTION_PATTERN_CODE  -- PK
TRADE_CONDITION_NO      -- 제품코드 (KF001, KF013 등)
PRIMARY_STORE_USER_CODE -- 고객코드 (KDKK)
CUSTOMER_USER_CODE      -- 엔드유저코드
```

**MA_SELECTION_PATTERN_DETAILS** (용기/밸브 스펙)
```
SELECTION_PATTERN_CODE  -- FK
SEQ_NO                  -- 순번
CYLINDER_SPEC_CODE      -- 용기스펙 코드
VALVE_SPEC_CODE         -- 밸브스펙 코드
```

---

## 🚀 작업 순서

### Step 1: Source Connector 업데이트

현재 `table.include.list`에 제품코드 테이블 추가:

```bash
# 현재 설정 확인
curl -s http://localhost:8083/connectors/oracle-fcms-cylcy-main-v4/config | jq '.["table.include.list"]'
```

**새 table.include.list 값:**
```
FCMS.MA_CYLINDERS,FCMS.MA_CYLINDER_SPECS,FCMS.MA_ITEMS,FCMS.MA_PARAMETERS,FCMS.MA_VALVE_SPECS,FCMS.TR_CYLINDER_STATUS_HISTORIES,FCMS.TR_LATEST_CYLINDER_STATUSES,FCMS.TR_MOVE_REPORTS,FCMS.TR_MOVE_REPORT_DETAILS,FCMS.TR_ORDERS,FCMS.TR_ORDER_INFORMATIONS,FCMS.MA_SELECTION_PATTERNS,FCMS.MA_SELECTION_PATTERN_DETAILS
```

**커넥터 업데이트 명령:**
```bash
curl -X PUT http://localhost:8083/connectors/oracle-fcms-cylcy-main-v4/config \
  -H "Content-Type: application/json" \
  -d '{
    "connector.class": "io.debezium.connector.oracle.OracleConnector",
    "name": "oracle-fcms-cylcy-main-v4",
    "database.hostname": "10.78.30.18",
    "database.port": "1521",
    "database.dbname": "FCMSDB",
    "database.user": "FCMS",
    "database.password": "FCMS",
    "database.connection.adapter": "logminer",
    "log.mining.dictionary": "online_catalog",
    "log.mining.start.scn": "260664866",
    "log.mining.continuous.mine": "false",
    "schema.include.list": "FCMS",
    "table.include.list": "FCMS.MA_CYLINDERS,FCMS.MA_CYLINDER_SPECS,FCMS.MA_ITEMS,FCMS.MA_PARAMETERS,FCMS.MA_VALVE_SPECS,FCMS.TR_CYLINDER_STATUS_HISTORIES,FCMS.TR_LATEST_CYLINDER_STATUSES,FCMS.TR_MOVE_REPORTS,FCMS.TR_MOVE_REPORT_DETAILS,FCMS.TR_ORDERS,FCMS.TR_ORDER_INFORMATIONS,FCMS.MA_SELECTION_PATTERNS,FCMS.MA_SELECTION_PATTERN_DETAILS",
    "include.schema.changes": "false",
    "snapshot.mode": "when_needed",
    "topic.prefix": "fcms",
    "schema.history.internal.kafka.bootstrap.servers": "kafka:29092",
    "schema.history.internal.kafka.topic": "dbhistory.oracle.cylcy.main"
  }'
```

### Step 2: Source Connector 상태 확인

```bash
curl -s http://localhost:8083/connectors/oracle-fcms-cylcy-main-v4/status | jq
```

**정상 응답:**
```json
{
  "name": "oracle-fcms-cylcy-main-v4",
  "connector": { "state": "RUNNING", "worker_id": "..." },
  "tasks": [{ "id": 0, "state": "RUNNING", "worker_id": "..." }]
}
```

### Step 3: Kafka Topic 생성 확인

새 테이블의 토픽이 생성되었는지 확인:
```bash
docker exec -it debezium-oracle-kafka bash -lc "kafka-topics --bootstrap-server localhost:9092 --list | grep -i selection"
```

**예상 출력:**
```
fcms.FCMS.MA_SELECTION_PATTERNS
fcms.FCMS.MA_SELECTION_PATTERN_DETAILS
```

---

### Step 4: PostgreSQL 테이블 생성

Sink 커넥터가 자동 생성하지 않으므로 수동 생성:

```sql
-- PostgreSQL에서 실행
-- psql -U postgres -d cycy_db

CREATE TABLE IF NOT EXISTS "fcms_cdc"."ma_selection_patterns" (
    "SELECTION_PATTERN_CODE" VARCHAR(50) PRIMARY KEY,
    "TRADE_CONDITION_NO" VARCHAR(50),
    "PRIMARY_STORE_USER_CODE" VARCHAR(50),
    "CUSTOMER_USER_CODE" VARCHAR(100),
    "CUSTOMER_USER_NAME" VARCHAR(200),
    "UPDATE_USER_CODE" VARCHAR(50),
    "UPDATE_DATETIME" TIMESTAMP,
    "ENTRY_USER_CODE" VARCHAR(50),
    "ENTRY_DATETIME" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "fcms_cdc"."ma_selection_pattern_details" (
    "SELECTION_PATTERN_CODE" VARCHAR(50),
    "SEQ_NO" INTEGER,
    "CYLINDER_SPEC_CODE" VARCHAR(50),
    "VALVE_SPEC_CODE" VARCHAR(50),
    "ITEM_CODE" VARCHAR(50),
    "CAPACITY" NUMERIC,
    "UPDATE_USER_CODE" VARCHAR(50),
    "UPDATE_DATETIME" TIMESTAMP,
    PRIMARY KEY ("SELECTION_PATTERN_CODE", "SEQ_NO")
);

-- 인덱스 추가
CREATE INDEX idx_ma_selection_patterns_trade ON "fcms_cdc"."ma_selection_patterns"("TRADE_CONDITION_NO");
CREATE INDEX idx_ma_selection_pattern_details_specs ON "fcms_cdc"."ma_selection_pattern_details"("CYLINDER_SPEC_CODE", "VALVE_SPEC_CODE");
```

---

### Step 5: Sink Connector 생성

**MA_SELECTION_PATTERNS Sink:**
```bash
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sink_dev_ma_selection_patterns",
    "config": {
      "connector.class": "io.debezium.connector.jdbc.JdbcSinkConnector",
      "topics": "fcms.FCMS.MA_SELECTION_PATTERNS",
      "connection.url": "jdbc:postgresql://10.78.30.98:5434/cycy_db?stringtype=unspecified",
      "connection.username": "postgres",
      "connection.password": "postgres",
      "insert.mode": "upsert",
      "primary.key.mode": "record_key",
      "delete.enabled": "true",
      "auto.create": "false",
      "auto.evolve": "false",
      "schema.evolution": "none",
      "quote.identifiers": "true",
      "table.name.format": "\"fcms_cdc\".\"ma_selection_patterns\"",
      "tasks.max": "1"
    }
  }'
```

**MA_SELECTION_PATTERN_DETAILS Sink:**
```bash
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sink_dev_ma_selection_pattern_details",
    "config": {
      "connector.class": "io.debezium.connector.jdbc.JdbcSinkConnector",
      "topics": "fcms.FCMS.MA_SELECTION_PATTERN_DETAILS",
      "connection.url": "jdbc:postgresql://10.78.30.98:5434/cycy_db?stringtype=unspecified",
      "connection.username": "postgres",
      "connection.password": "postgres",
      "insert.mode": "upsert",
      "primary.key.mode": "record_key",
      "delete.enabled": "true",
      "auto.create": "false",
      "auto.evolve": "false",
      "schema.evolution": "none",
      "quote.identifiers": "true",
      "table.name.format": "\"fcms_cdc\".\"ma_selection_pattern_details\"",
      "tasks.max": "1"
    }
  }'
```

### Step 6: Sink Connector 상태 확인

```bash
curl -s http://localhost:8083/connectors/sink_dev_ma_selection_patterns/status | jq
curl -s http://localhost:8083/connectors/sink_dev_ma_selection_pattern_details/status | jq
```

---

### Step 7: PostgreSQL 데이터 확인

```bash
psql -U postgres -d cycy_db -c 'SELECT COUNT(*) FROM "fcms_cdc"."ma_selection_patterns";'
psql -U postgres -d cycy_db -c 'SELECT "SELECTION_PATTERN_CODE", "TRADE_CONDITION_NO", "PRIMARY_STORE_USER_CODE" FROM "fcms_cdc"."ma_selection_patterns" LIMIT 5;'
```

---

## 🔍 문제 해결

### Topic이 생성되지 않는 경우

새 테이블 추가 후 snapshot이 필요할 수 있음:
```bash
# Source 커넥터 재시작
curl -X POST http://localhost:8083/connectors/oracle-fcms-cylcy-main-v4/restart
```

### Sink가 FAILED 상태인 경우

```bash
# 오류 메시지 확인
curl -s http://localhost:8083/connectors/sink_dev_ma_selection_patterns/status | jq '.tasks[0].trace'

# Task 재시작
curl -X POST http://localhost:8083/connectors/sink_dev_ma_selection_patterns/tasks/0/restart
```

### PostgreSQL 테이블 구조 불일치

Oracle 컬럼과 PostgreSQL 컬럼명이 정확히 일치해야 함 (대소문자 포함)

---

## ✅ 완료 체크리스트

- [ ] Source Connector `table.include.list` 업데이트
- [ ] Source Connector RUNNING 확인
- [ ] Kafka Topic 생성 확인 (`fcms.FCMS.MA_SELECTION_*`)
- [ ] PostgreSQL 테이블 생성
- [ ] Sink Connector 2개 생성
- [ ] Sink Connector RUNNING 확인
- [ ] PostgreSQL 데이터 동기화 확인
