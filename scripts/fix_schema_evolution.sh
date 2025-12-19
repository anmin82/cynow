#!/bin/bash
# Debezium JDBC Sink Connector 스키마 진화 실패 문제 일괄 수정 스크립트

CONNECT_URL="${KAFKA_CONNECT_URL:-http://localhost:8083}"

echo "=== Debezium JDBC Sink Connector 스키마 진화 문제 수정 ==="
echo "Connect URL: $CONNECT_URL"
echo ""

# 모든 커넥터 목록 가져오기
CONNECTORS=$(curl -s "$CONNECT_URL/connectors" | jq -r '.[]')

FIXED_COUNT=0
FAILED_COUNT=0

for connector in $CONNECTORS; do
    echo "Checking connector: $connector"
    
    # 커넥터 상태 확인
    STATUS=$(curl -s "$CONNECT_URL/connectors/$connector/status")
    CONNECTOR_TYPE=$(echo "$STATUS" | jq -r '.type')
    
    # Sink 커넥터만 처리
    if [ "$CONNECTOR_TYPE" != "sink" ]; then
        echo "  Skipping (not a sink connector)"
        continue
    fi
    
    # Task 상태 확인
    TASK_STATE=$(echo "$STATUS" | jq -r '.tasks[0].state // "UNKNOWN"')
    TRACE=$(echo "$STATUS" | jq -r '.tasks[0].trace // ""')
    
    if [ "$TASK_STATE" = "FAILED" ]; then
        # 스키마 진화 실패 오류 확인
        if echo "$TRACE" | grep -qi "cannot alter table.*not optional but has no default value"; then
            echo "  ⚠️  Schema evolution failure detected"
            
            # 현재 설정 가져오기
            CURRENT_CONFIG=$(curl -s "$CONNECT_URL/connectors/$connector/config")
            
            # auto.evolve를 false로 변경
            NEW_CONFIG=$(echo "$CURRENT_CONFIG" | jq '. + {"auto.evolve": "false"}')
            
            echo "  Setting auto.evolve=false..."
            RESPONSE=$(echo "$NEW_CONFIG" | curl -s -w "\n%{http_code}" -X PUT "$CONNECT_URL/connectors/$connector/config" \
                -H "Content-Type: application/json" \
                -d @-)
            
            HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
            
            if [ "$HTTP_CODE" = "200" ]; then
                echo "  ✓ Configuration updated"
                
                # Task 재시작
                echo "  Restarting task..."
                RESTART_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$CONNECT_URL/connectors/$connector/tasks/0/restart")
                RESTART_CODE=$(echo "$RESTART_RESPONSE" | tail -n1)
                
                if [ "$RESTART_CODE" = "204" ] || [ "$RESTART_CODE" = "200" ]; then
                    echo "  ✓ Task restarted"
                    FIXED_COUNT=$((FIXED_COUNT + 1))
                else
                    echo "  ✗ Failed to restart task (HTTP $RESTART_CODE)"
                    FAILED_COUNT=$((FAILED_COUNT + 1))
                fi
            else
                echo "  ✗ Failed to update configuration (HTTP $HTTP_CODE)"
                FAILED_COUNT=$((FAILED_COUNT + 1))
            fi
        else
            echo "  ⚠️  Failed but not a schema evolution issue"
            echo "  Error: $(echo "$TRACE" | head -n 3 | tr '\n' ' ')"
        fi
    elif [ "$TASK_STATE" = "RUNNING" ]; then
        echo "  ✓ Running normally"
    else
        echo "  ? State: $TASK_STATE"
    fi
    
    echo ""
done

echo "=== 완료 ==="
echo "Fixed: $FIXED_COUNT"
echo "Failed: $FAILED_COUNT"

if [ $FIXED_COUNT -gt 0 ]; then
    echo ""
    echo "수정된 커넥터의 상태를 확인하세요:"
    echo "  curl -s $CONNECT_URL/connectors/<connector-name>/status | jq"
fi












