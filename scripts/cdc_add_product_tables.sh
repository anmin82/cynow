#!/bin/bash
# ============================================================
# CDC 제품코드 테이블 추가 스크립트
# 서버에서 한 번에 실행하세요
# ============================================================

echo "===== Step 1: PostgreSQL 테이블 생성 ====="
docker exec -i debezium-oracle-postgres psql -U postgres -d cycy_db << 'EOSQL'
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

CREATE INDEX IF NOT EXISTS idx_ma_selection_patterns_trade ON "fcms_cdc"."ma_selection_patterns"("TRADE_CONDITION_NO");
CREATE INDEX IF NOT EXISTS idx_ma_selection_pattern_details_specs ON "fcms_cdc"."ma_selection_pattern_details"("CYLINDER_SPEC_CODE", "VALVE_SPEC_CODE");
EOSQL

echo ""
echo "===== Step 2: Source Connector 업데이트 ====="
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

echo ""
echo ""
echo "===== Step 3: Source Connector 상태 확인 ====="
sleep 3
curl -s http://localhost:8083/connectors/oracle-fcms-cylcy-main-v4/status | jq '.connector.state, .tasks[0].state'

echo ""
echo ""
echo "===== Step 4: Sink Connector - MA_SELECTION_PATTERNS ====="
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

echo ""
echo ""
echo "===== Step 5: Sink Connector - MA_SELECTION_PATTERN_DETAILS ====="
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

echo ""
echo ""
echo "===== Step 6: 모든 Sink Connector 상태 확인 ====="
sleep 3
echo "--- MA_SELECTION_PATTERNS ---"
curl -s http://localhost:8083/connectors/sink_dev_ma_selection_patterns/status | jq '.connector.state, .tasks[0].state' 2>/dev/null || echo "아직 생성 중..."
echo ""
echo "--- MA_SELECTION_PATTERN_DETAILS ---"
curl -s http://localhost:8083/connectors/sink_dev_ma_selection_pattern_details/status | jq '.connector.state, .tasks[0].state' 2>/dev/null || echo "아직 생성 중..."

echo ""
echo ""
echo "===== Step 7: Kafka Topic 확인 ====="
docker exec -it debezium-oracle-kafka bash -lc "kafka-topics --bootstrap-server localhost:9092 --list 2>/dev/null | grep -i selection"

echo ""
echo ""
echo "===== 완료! ====="
echo "30초 후 PostgreSQL 데이터 확인:"
echo "  docker exec -i debezium-oracle-postgres psql -U postgres -d cycy_db -c 'SELECT COUNT(*) FROM \"fcms_cdc\".\"ma_selection_patterns\";'"
echo "  docker exec -i debezium-oracle-postgres psql -U postgres -d cycy_db -c 'SELECT \"TRADE_CONDITION_NO\", \"PRIMARY_STORE_USER_CODE\" FROM \"fcms_cdc\".\"ma_selection_patterns\" LIMIT 5;'"

