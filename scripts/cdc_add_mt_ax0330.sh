#!/bin/bash
# =============================================================================
# MT_AX0330 (충전량 마스터) CDC 추가 스크립트
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
PG_PASSWORD="cynow2024!"

echo "=========================================="
echo "MT_AX0330 CDC 추가"
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
COMMENT ON COLUMN fcms_cdc.mt_ax0330."NSGT_MEI" IS '납입형태 명칭';

EOF

echo "✓ 테이블 생성 완료"

# -----------------------------------------------------------------------------
# Step 2: 현재 Source Connector 설정 확인
# -----------------------------------------------------------------------------
echo ""
echo "[Step 2] 현재 Source Connector 설정 확인..."

CURRENT_TABLES=$(curl -s $KAFKA_CONNECT_URL/connectors/oracle-fcms-cylcy-main-v4/config | jq -r '.["table.include.list"]')
echo "현재 테이블 목록: $CURRENT_TABLES"

# -----------------------------------------------------------------------------
# Step 3: Source Connector에 MT_AX0330 추가
# -----------------------------------------------------------------------------
echo ""
echo "[Step 3] Source Connector에 MT_AX0330 추가..."
echo "⚠️  주의: table.include.list에 FCMS.MT_AX0330을 수동으로 추가해야 합니다."
echo ""
echo "다음 명령어로 업데이트하세요:"
echo ""
cat << 'HEREDOC'
# 현재 설정 백업
curl -s http://10.78.30.98:8083/connectors/oracle-fcms-cylcy-main-v4/config > /tmp/connector_backup.json

# 설정 수정 (table.include.list에 FCMS.MT_AX0330 추가)
# 예: "table.include.list": "...,FCMS.MT_AX0330"

# 커넥터 업데이트
curl -X PUT http://10.78.30.98:8083/connectors/oracle-fcms-cylcy-main-v4/config \
  -H "Content-Type: application/json" \
  -d @/tmp/connector_config_updated.json
HEREDOC

# -----------------------------------------------------------------------------
# Step 4: Sink Connector 생성
# -----------------------------------------------------------------------------
echo ""
echo "[Step 4] Sink Connector 생성..."

curl -X POST $KAFKA_CONNECT_URL/connectors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "jdbc-sink-mt-ax0330",
    "config": {
      "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
      "connection.url": "jdbc:postgresql://10.78.30.98:5434/cycy_db",
      "connection.user": "postgres",
      "connection.password": "cynow2024!",
      "topics": "fcms.FCMS.MT_AX0330",
      "table.name.format": "fcms_cdc.mt_ax0330",
      "auto.create": "false",
      "auto.evolve": "true",
      "insert.mode": "upsert",
      "pk.mode": "record_key",
      "pk.fields": "KAISYA_CD,NSGT_CD",
      "transforms": "unwrap",
      "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
      "transforms.unwrap.drop.tombstones": "true"
    }
  }'

echo ""
echo "✓ Sink Connector 생성 완료"

# -----------------------------------------------------------------------------
# Step 5: 확인
# -----------------------------------------------------------------------------
echo ""
echo "[Step 5] 커넥터 상태 확인..."
sleep 3
curl -s $KAFKA_CONNECT_URL/connectors/jdbc-sink-mt-ax0330/status | jq .

echo ""
echo "=========================================="
echo "완료!"
echo ""
echo "다음 단계:"
echo "1. Source Connector에 FCMS.MT_AX0330 추가 필요"
echo "2. 데이터 동기화 확인: SELECT COUNT(*) FROM fcms_cdc.mt_ax0330;"
echo "3. CYNOW 제품코드 서비스에서 충전량 조인 추가"
echo "=========================================="

