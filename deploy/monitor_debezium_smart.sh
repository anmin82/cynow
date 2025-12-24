#!/bin/bash
# Debezium Smart Monitoring and Recovery Script
# On error: Pause -> Check Oracle every 1 min -> Resume when healthy

# ========================================
# Configuration (Update for your environment)
# ========================================
KAFKA_CONNECT_URL="http://localhost:8083"
CONNECTOR_NAME="oracle-fcms-cylcy-main"
CHECK_INTERVAL=60  # Normal status check interval (seconds)
RECOVERY_CHECK_INTERVAL=60  # Recovery check interval (seconds)
MAX_API_RETRIES=3  # Max retries when API fails

# Oracle connection test settings
ORACLE_HOST="10.78.30.18"  # Oracle server IP
ORACLE_PORT="1521"         # Oracle Listener port
ORACLE_TEST_TIMEOUT=5      # Connection test timeout (seconds)

# Log settings
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

LOG_DATE=$(date +%Y%m)
LOG_FILE="$LOG_DIR/debezium_smart_monitor_$LOG_DATE.log"

# ========================================
# Functions
# ========================================

write_log() {
    local message="$1"
    local level="${2:-INFO}"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    local log_message="[$timestamp] [$level] $message"
    
    echo "$log_message"
    echo "$log_message" >> "$LOG_FILE"
}

test_oracle_connection() {
    write_log "Testing Oracle connection... ($ORACLE_HOST:$ORACLE_PORT)"
    
    # TCP connection test using timeout and nc (netcat)
    if timeout "$ORACLE_TEST_TIMEOUT" bash -c "echo > /dev/tcp/$ORACLE_HOST/$ORACLE_PORT" 2>/dev/null; then
        write_log "[OK] Oracle listener responding normally" "INFO"
        return 0
    else
        write_log "[FAIL] Oracle listener not responding (timeout)" "WARN"
        return 1
    fi
}

get_connector_status() {
    local response
    response=$(curl -s -f -m 10 "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/status" 2>/dev/null)
    local exit_code=$?
    
    if [ $exit_code -eq 0 ] && [ -n "$response" ]; then
        echo "$response"
        return 0
    else
        write_log "Kafka Connect API call failed (exit code: $exit_code)" "ERROR"
        return 1
    fi
}

pause_connector() {
    write_log "Sending connector pause request..." "WARN"
    
    if curl -s -f -X PUT -m 30 "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/pause" > /dev/null 2>&1; then
        sleep 5
        
        local status=$(get_connector_status)
        if [ $? -eq 0 ]; then
            local state=$(echo "$status" | jq -r '.connector.state')
            if [ "$state" = "PAUSED" ]; then
                write_log "[OK] Connector paused successfully" "INFO"
                return 0
            else
                write_log "Pause failed: state = $state" "ERROR"
                return 1
            fi
        fi
    else
        write_log "Pause API call failed" "ERROR"
        return 1
    fi
}

resume_connector() {
    write_log "Sending connector resume request..." "INFO"
    
    if curl -s -f -X PUT -m 30 "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/resume" > /dev/null 2>&1; then
        sleep 10
        
        local status=$(get_connector_status)
        if [ $? -eq 0 ]; then
            local state=$(echo "$status" | jq -r '.connector.state')
            if [ "$state" = "RUNNING" ]; then
                local running_tasks=$(echo "$status" | jq '[.tasks[] | select(.state == "RUNNING")] | length')
                local total_tasks=$(echo "$status" | jq '.tasks | length')
                write_log "[OK] Connector resumed (Tasks: $running_tasks/$total_tasks)" "INFO"
                return 0
            else
                write_log "Resume failed: state = $state" "ERROR"
                return 1
            fi
        fi
    else
        write_log "Resume API call failed" "ERROR"
        return 1
    fi
}

send_alert() {
    local message="$1"
    local level="${2:-ERROR}"
    
    write_log "ALERT: $message" "$level"
    
    # Write to syslog
    logger -t "CYNOW-Debezium" -p "user.$level" "$message" 2>/dev/null || true
    
    # TODO: Send email, Slack, Teams notifications
}

wait_for_recovery() {
    local max_wait_minutes="${1:-30}"
    
    write_log "========================================" "INFO"
    write_log "Entering recovery wait mode" "INFO"
    write_log "Will check Oracle recovery every $RECOVERY_CHECK_INTERVAL seconds" "INFO"
    write_log "Max wait time: $max_wait_minutes minutes" "INFO"
    write_log "========================================" "INFO"
    
    local start_time=$(date +%s)
    local check_count=0
    
    while true; do
        check_count=$((check_count + 1))
        local current_time=$(date +%s)
        local elapsed_seconds=$((current_time - start_time))
        local elapsed_minutes=$((elapsed_seconds / 60))
        
        write_log "[$check_count] Checking Oracle connection... (elapsed: $elapsed_minutes min)"
        
        if test_oracle_connection; then
            write_log "[OK] Oracle has recovered!" "INFO"
            return 0
        else
            write_log "Oracle not recovered yet. Will recheck in $RECOVERY_CHECK_INTERVAL sec..." "WARN"
        fi
        
        if [ $elapsed_minutes -ge $max_wait_minutes ]; then
            write_log "Max wait time ($max_wait_minutes min) exceeded. Ending recovery wait." "ERROR"
            send_alert "Oracle did not recover after $max_wait_minutes minutes. Manual intervention required." "ERROR"
            return 1
        fi
        
        sleep "$RECOVERY_CHECK_INTERVAL"
    done
}

# ========================================
# Main Monitoring Loop
# ========================================

write_log "========================================" "INFO"
write_log "Debezium Smart Monitoring Started" "INFO"
write_log "Connector: $CONNECTOR_NAME" "INFO"
write_log "Kafka Connect: $KAFKA_CONNECT_URL" "INFO"
write_log "Oracle: $ORACLE_HOST:$ORACLE_PORT" "INFO"
write_log "Normal check interval: $CHECK_INTERVAL sec" "INFO"
write_log "Recovery check interval: $RECOVERY_CHECK_INTERVAL sec" "INFO"
write_log "========================================" "INFO"

api_fail_count=0
is_in_recovery_mode=false

while true; do
    status=$(get_connector_status)
    
    if [ $? -ne 0 ] || [ -z "$status" ]; then
        # Kafka Connect API not responding
        api_fail_count=$((api_fail_count + 1))
        write_log "Kafka Connect API not responding (attempt $api_fail_count/$MAX_API_RETRIES)" "ERROR"
        
        if [ $api_fail_count -ge $MAX_API_RETRIES ]; then
            send_alert "Kafka Connect not responding after $MAX_API_RETRIES attempts. Check service status." "ERROR"
            api_fail_count=0
        fi
        
        sleep "$CHECK_INTERVAL"
        continue
    fi
    
    # API responded successfully
    api_fail_count=0
    
    connector_state=$(echo "$status" | jq -r '.connector.state')
    tasks_count=$(echo "$status" | jq '.tasks | length')
    running_tasks=$(echo "$status" | jq '[.tasks[] | select(.state == "RUNNING")] | length')
    failed_tasks=$(echo "$status" | jq '[.tasks[] | select(.state == "FAILED")] | length')
    
    write_log "Status: $connector_state | Tasks: $running_tasks/$tasks_count (failed: $failed_tasks)"
    
    # ===== State Handling =====
    
    if [ "$is_in_recovery_mode" = true ]; then
        # Recovery wait mode
        if [ "$connector_state" = "PAUSED" ]; then
            write_log "Recovery mode: Maintaining PAUSED state"
            
            if test_oracle_connection; then
                write_log "[OK] Oracle recovery detected! Attempting to resume connector..." "INFO"
                
                if resume_connector; then
                    write_log "[OK] Connector resumed successfully!" "INFO"
                    send_alert "Debezium Connector has recovered and resumed." "INFO"
                    is_in_recovery_mode=false
                else
                    write_log "Connector resume failed. Will retry in next cycle..." "WARN"
                fi
            else
                write_log "Oracle not recovered yet. Continuing to wait..." "INFO"
            fi
        else
            write_log "In recovery mode but state is not PAUSED: $connector_state" "WARN"
            is_in_recovery_mode=false
        fi
    else
        # Normal monitoring mode
        
        if [ "$connector_state" = "FAILED" ] || [ "$failed_tasks" -gt 0 ]; then
            # Failure detected
            write_log "========================================" "ERROR"
            write_log "FAILURE DETECTED!" "ERROR"
            write_log "Connector: $connector_state | Failed Tasks: $failed_tasks" "ERROR"
            write_log "========================================" "ERROR"
            
            send_alert "Debezium Connector failure detected (state: $connector_state, failed tasks: $failed_tasks)" "ERROR"
            
            if pause_connector; then
                write_log "[OK] Connector paused. Entering recovery wait mode." "INFO"
                is_in_recovery_mode=true
                wait_for_recovery 30
            else
                write_log "Connector pause failed. Will retry in next cycle..." "ERROR"
            fi
        elif [ "$connector_state" = "RUNNING" ] && [ "$running_tasks" -eq 0 ] && [ "$tasks_count" -gt 0 ]; then
            # Connector is RUNNING but no tasks are running
            write_log "ABNORMAL state: Connector is RUNNING but no tasks are running" "WARN"
            send_alert "Debezium Connector abnormal state: No tasks are running." "WARN"
            
            if pause_connector; then
                is_in_recovery_mode=true
                wait_for_recovery 30
            fi
        elif [ "$connector_state" = "RUNNING" ] && [ "$running_tasks" -eq "$tasks_count" ]; then
            # Fully healthy state
            write_log "[OK] Operating normally" "INFO"
        else
            # Other states
            write_log "State: $connector_state (attention needed)" "WARN"
        fi
    fi
    
    sleep "$CHECK_INTERVAL"
done













