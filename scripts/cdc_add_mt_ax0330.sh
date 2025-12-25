#!/bin/bash
# =============================================================================
# MT_AX0330 (충전량 마스터) CDC 추가 스크립트 - 한방 실행
# 
# 연결: ma_selection_patterns.PACKING_CODE → MT_AX0330.NSGT_CD
# 충전량: MT_AX0330.NSGT_YORY
# =============================================================================

set -e

KAFKA_CONNECT_URL="http://10.78.30.98:8083"
PG_HOST="10.78.30.98"
PG_PORT="5434"
PG_DB="cycy_db"
PG_USER="postgres"
PG_PASSWORD="postgres"

echo "=========================================="
echo "MT_AX0330 CDC 추가 - 한방 스크립트"
echo "=========================================="

# -----------------------------------------------------------------------------
# Step 1: PostgreSQL 테이블 생성
# -----------------------------------------------------------------------------
echo ""
echo "[Step 1] PostgreSQL 테이블 생성..."

PGPASSWORD=$PG_PASSWORD psql -h $PG_HOST -p $PG_PORT -U $PG_USER -d $PG_DB << 'EOF'
CREATE TABLE IF NOT EXISTS fcms_cdc.mt_ax0330 (
    "KAISYA_CD" CHAR(3) NOT NULL,
    "NSGT_CD" CHAR(5) NOT NULL,
    "NSGT_MEI" VARCHAR(40),
    "NSGT_HYUJ_MEI" VARCHAR(10),
    "NSGT_YORY" NUMERIC,
    "NSGT_STN_CLS_K" CHAR(3),
    "NSGT_STN_CD" CHAR(3),
    "ZAIK_NSGT_CD" CHAR(5),
    "REG_DT" TIMESTAMP,
    "REG_BMN_CD" CHAR(6),
    "REG_P_CD" CHAR(7),
    "REG_P_UID" VARCHAR(20),
    "UPD_DT" TIMESTAMP,
    "UPD_BMN_CD" CHAR(6),
    "UPD_P_CD" CHAR(7),
    "UPD_P_UID" VARCHAR(20),
    PRIMARY KEY ("KAISYA_CD", "NSGT_CD")
);

COMMENT ON TABLE fcms_cdc.mt_ax0330 IS '충전량 마스터 (PACKING_CODE 연결)';
COMMENT ON COLUMN fcms_cdc.mt_ax0330."NSGT_CD" IS '납입형태 코드 (PACKING_CODE)';
COMMENT ON COLUMN fcms_cdc.mt_ax0330."NSGT_YORY" IS '충전량 (kg)';
EOF

echo "✓ 테이블 생성 완료"

# -----------------------------------------------------------------------------
# Step 2: Source Connector 설정 가져오기 및 업데이트
# -----------------------------------------------------------------------------
echo ""
echo "[Step 2] Source Connector 업데이트 (MT_AX0330 추가)..."

# 현재 설정 가져오기
curl -s $KAFKA_CONNECT_URL/connectors/oracle-fcms-cylcy-main-v4/config > /tmp/source_config.json

# table.include.list에 MT_AX0330 추가
# jq로 업데이트
cat /tmp/source_config.json | jq '.["table.include.list"] = .["table.include.list"] + ",FCMS.MT_AX0330"' > /tmp/source_config_updated.json

# 커넥터 업데이트
curl -X PUT $KAFKA_CONNECT_URL/connectors/oracle-fcms-cylcy-main-v4/config \
  -H "Content-Type: application/json" \
  -d @/tmp/source_config_updated.json

echo ""
echo "✓ Source Connector 업데이트 완료"

# -----------------------------------------------------------------------------
# Step 3: 기존 Sink Connector 삭제 (있으면)
# -----------------------------------------------------------------------------
echo ""
echo "[Step 3] 기존 Sink Connector 정리..."
curl -X DELETE $KAFKA_CONNECT_URL/connectors/jdbc-sink-mt-ax0330 2>/dev/null || true
sleep 2

# -----------------------------------------------------------------------------
# Step 4: Sink Connector 생성 (Debezium JDBC Sink)
# -----------------------------------------------------------------------------
echo ""
echo "[Step 4] Sink Connector 생성..."

curl -X POST $KAFKA_CONNECT_URL/connectors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "jdbc-sink-mt-ax0330",
    "config": {
      "connector.class": "io.debezium.connector.jdbc.JdbcSinkConnector",
      "tasks.max": "1",
      "connection.url": "jdbc:postgresql://10.78.30.98:5434/cycy_db",
      "connection.username": "postgres",
      "connection.password": "postgres",
      "topics": "fcms.FCMS.MT_AX0330",
      "table.name.format": "fcms_cdc.mt_ax0330",
      "insert.mode": "upsert",
      "primary.key.mode": "record_key",
      "primary.key.fields": "KAISYA_CD,NSGT_CD",
      "schema.evolution": "basic",
      "database.time_zone": "Asia/Seoul"
    }
  }'

echo ""
echo "✓ Sink Connector 생성 완료"

# -----------------------------------------------------------------------------
# Step 5: 상태 확인
# -----------------------------------------------------------------------------
echo ""
echo "[Step 5] 커넥터 상태 확인..."
sleep 5

echo ""
echo "=== Source Connector 상태 ==="
curl -s $KAFKA_CONNECT_URL/connectors/oracle-fcms-cylcy-main-v4/status | jq '.connector.state'

echo ""
echo "=== Sink Connector 상태 ==="
curl -s $KAFKA_CONNECT_URL/connectors/jdbc-sink-mt-ax0330/status | jq .

# -----------------------------------------------------------------------------
# Step 6: 데이터 확인
# -----------------------------------------------------------------------------
echo ""
echo "[Step 6] 데이터 동기화 확인 (30초 대기 후)..."
sleep 30

PGPASSWORD=$PG_PASSWORD psql -h $PG_HOST -p $PG_PORT -U $PG_USER -d $PG_DB -c \
  "SELECT COUNT(*) as count FROM fcms_cdc.mt_ax0330;"

echo ""
echo "=========================================="
echo "✅ 완료!"
echo ""
echo "확인 쿼리:"
echo "SELECT \"NSGT_CD\", \"NSGT_YORY\", \"NSGT_MEI\" FROM fcms_cdc.mt_ax0330 LIMIT 10;"
echo "=========================================="

