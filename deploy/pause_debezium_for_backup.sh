#!/bin/bash
# Debezium Connector pause/resume script for backup time
# Usage: ./pause_debezium_for_backup.sh pause|resume

set -e

# ========================================
# Configuration (Update for your environment)
# ========================================
KAFKA_CONNECT_URL="http://localhost:8083"
CONNECTOR_NAME="oracle-fcms-cylcy-main"

# Log settings
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

LOG_DATE=$(date +%Y%m)
LOG_FILE="$LOG_DIR/debezium_pause_resume_$LOG_DATE.log"

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

get_connector_status() {
    write_log "Getting connector status..."
    
    local response
    response=$(curl -s -f -m 10 "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/status" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        local state=$(echo "$response" | jq -r '.connector.state')
        local tasks_count=$(echo "$response" | jq '.tasks | length')
        
        write_log "Connector state: $state"
        write_log "Tasks: $tasks_count"
        
        if [ "$tasks_count" -gt 0 ]; then
            echo "$response" | jq -r '.tasks[] | "  Task \(.id): \(.state)"' | while read line; do
                write_log "$line"
            done
        fi
        
        echo "$response"
        return 0
    else
        write_log "Failed to get connector status" "ERROR"
        return 1
    fi
}

pause_connector() {
    write_log "========================================" "INFO"
    write_log "Pausing Debezium Connector" "INFO"
    write_log "Connector: $CONNECTOR_NAME" "INFO"
    write_log "========================================" "INFO"
    
    # Check current status
    local current_status=$(get_connector_status)
    if [ $? -ne 0 ]; then
        write_log "Cannot connect to Kafka Connect. Check service status." "ERROR"
        return 1
    fi
    
    local current_state=$(echo "$current_status" | jq -r '.connector.state')
    if [ "$current_state" = "PAUSED" ]; then
        write_log "Connector is already PAUSED" "WARN"
        return 0
    fi
    
    # Send pause request
    write_log "Sending pause request..."
    
    if curl -s -f -X PUT -m 30 "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/pause" > /dev/null 2>&1; then
        write_log "Pause request sent successfully" "INFO"
        
        # Wait and check status
        sleep 5
        
        local new_status=$(get_connector_status)
        if [ $? -eq 0 ]; then
            local new_state=$(echo "$new_status" | jq -r '.connector.state')
            if [ "$new_state" = "PAUSED" ]; then
                write_log "[OK] Connector paused successfully!" "INFO"
                return 0
            else
                write_log "Pause failed: state = $new_state" "WARN"
                return 1
            fi
        fi
    else
        write_log "Pause request failed" "ERROR"
        return 1
    fi
}

resume_connector() {
    write_log "========================================" "INFO"
    write_log "Resuming Debezium Connector" "INFO"
    write_log "Connector: $CONNECTOR_NAME" "INFO"
    write_log "========================================" "INFO"
    
    # Check current status
    local current_status=$(get_connector_status)
    if [ $? -ne 0 ]; then
        write_log "Cannot connect to Kafka Connect. Check service status." "ERROR"
        return 1
    fi
    
    local current_state=$(echo "$current_status" | jq -r '.connector.state')
    if [ "$current_state" = "RUNNING" ]; then
        write_log "Connector is already RUNNING" "INFO"
        return 0
    fi
    
    # Send resume request
    write_log "Sending resume request..."
    
    if curl -s -f -X PUT -m 30 "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/resume" > /dev/null 2>&1; then
        write_log "Resume request sent successfully" "INFO"
        
        # Wait for connector to start
        write_log "Waiting 10 seconds..."
        sleep 10
        
        local new_status=$(get_connector_status)
        if [ $? -eq 0 ]; then
            local new_state=$(echo "$new_status" | jq -r '.connector.state')
            
            if [ "$new_state" = "RUNNING" ]; then
                local running_tasks=$(echo "$new_status" | jq '[.tasks[] | select(.state == "RUNNING")] | length')
                local total_tasks=$(echo "$new_status" | jq '.tasks | length')
                
                write_log "[OK] Connector resumed successfully!" "INFO"
                write_log "Running tasks: $running_tasks/$total_tasks" "INFO"
                
                if [ "$running_tasks" -eq "$total_tasks" ]; then
                    write_log "[OK] All tasks are running normally" "INFO"
                else
                    write_log "Some tasks are not running. Check needed." "WARN"
                fi
                
                return 0
            elif [ "$new_state" = "FAILED" ]; then
                write_log "Connector is in FAILED state. Attempting restart..." "WARN"
                
                if curl -s -f -X POST -m 30 "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/restart?includeTasks=true" > /dev/null 2>&1; then
                    sleep 10
                    
                    local restart_status=$(get_connector_status)
                    local restart_state=$(echo "$restart_status" | jq -r '.connector.state')
                    
                    if [ "$restart_state" = "RUNNING" ]; then
                        write_log "[OK] Connector restarted and running" "INFO"
                        return 0
                    else
                        write_log "Restart failed. Manual intervention needed." "ERROR"
                        return 1
                    fi
                fi
            else
                write_log "Resume failed: state = $new_state" "ERROR"
                return 1
            fi
        fi
    else
        write_log "Resume request failed" "ERROR"
        return 1
    fi
}

# ========================================
# Main
# ========================================

if [ $# -eq 0 ]; then
    echo "Usage: $0 pause|resume"
    write_log "No action specified. Usage: $0 pause|resume" "ERROR"
    exit 1
fi

ACTION="$1"

write_log "========================================" "INFO"
write_log "Script started: pause_debezium_for_backup.sh" "INFO"
write_log "Action: $ACTION" "INFO"
write_log "Kafka Connect: $KAFKA_CONNECT_URL" "INFO"
write_log "Connector: $CONNECTOR_NAME" "INFO"
write_log "========================================" "INFO"

case "$ACTION" in
    pause)
        if pause_connector; then
            write_log "========================================" "INFO"
            write_log "Action completed: SUCCESS" "INFO"
            write_log "========================================" "INFO"
            exit 0
        else
            write_log "========================================" "WARN"
            write_log "Action completed: FAILED" "WARN"
            write_log "========================================" "WARN"
            exit 1
        fi
        ;;
    resume)
        if resume_connector; then
            write_log "========================================" "INFO"
            write_log "Action completed: SUCCESS" "INFO"
            write_log "========================================" "INFO"
            exit 0
        else
            write_log "========================================" "WARN"
            write_log "Action completed: FAILED" "WARN"
            write_log "========================================" "WARN"
            exit 1
        fi
        ;;
    *)
        echo "Invalid action: $ACTION"
        echo "Usage: $0 pause|resume"
        write_log "Invalid action: $ACTION" "ERROR"
        exit 1
        ;;
esac















