# Debezium Smart Monitoring and Recovery Script
# On error: Pause -> Check Oracle every 1 min -> Resume when healthy

# Continue execution even on errors
$ErrorActionPreference = "Continue"

# ========================================
# Configuration (Update for your environment)
# ========================================
$KAFKA_CONNECT_URL = "http://localhost:8083"
$CONNECTOR_NAME = "oracle-fcms-cylcy-main"
$CHECK_INTERVAL = 60  # Normal status check interval (seconds)
$RECOVERY_CHECK_INTERVAL = 60  # Recovery check interval (seconds)
$MAX_API_RETRIES = 3  # Max retries when API fails

# Oracle connection test settings
$ORACLE_HOST = "10.78.30.18"  # Oracle server IP
$ORACLE_PORT = "1521"          # Oracle Listener port
$ORACLE_TEST_TIMEOUT = 5       # Connection test timeout (seconds)

# Log settings
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$LogDir = Join-Path $ProjectRoot "logs"
if (-Not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$LogDate = Get-Date -Format "yyyyMM"
$LogFile = Join-Path $LogDir "debezium_smart_monitor_$LogDate.log"

# ========================================
# Functions
# ========================================

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Write-Output $LogMessage
    
    try {
        Add-Content -Path $LogFile -Value $LogMessage
    }
    catch {
        Write-Output "Log file write failed: $($_.Exception.Message)"
    }
}

function Test-OracleConnection {
    <#
    .SYNOPSIS
    Test Oracle listener connection availability
    #>
    Write-Log "Testing Oracle connection... ($ORACLE_HOST`:$ORACLE_PORT)"
    
    try {
        # TCP connection test (quick check)
        $TcpClient = New-Object System.Net.Sockets.TcpClient
        $Connection = $TcpClient.BeginConnect($ORACLE_HOST, $ORACLE_PORT, $null, $null)
        $Success = $Connection.AsyncWaitHandle.WaitOne($ORACLE_TEST_TIMEOUT * 1000, $false)
        
        if ($Success) {
            $TcpClient.EndConnect($Connection)
            $TcpClient.Close()
            Write-Log "[OK] Oracle listener responding normally" "INFO"
            return $true
        }
        else {
            $TcpClient.Close()
            Write-Log "[FAIL] Oracle listener not responding (timeout)" "WARN"
            return $false
        }
    }
    catch {
        Write-Log "[FAIL] Oracle connection failed: $($_.Exception.Message)" "WARN"
        return $false
    }
}

function Get-ConnectorStatus {
    try {
        $Response = Invoke-RestMethod `
            -Uri "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/status" `
            -Method Get `
            -TimeoutSec 10 `
            -ContentType "application/json"
        
        return $Response
    }
    catch {
        Write-Log "Kafka Connect API call failed: $($_.Exception.Message)" "ERROR"
        return $null
    }
}

function Pause-Connector {
    <#
    .SYNOPSIS
    Pause the connector (set to PAUSED state)
    #>
    Write-Log "Sending connector pause request..." "WARN"
    
    try {
        Invoke-RestMethod `
            -Uri "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/pause" `
            -Method Put `
            -TimeoutSec 30 `
            -ContentType "application/json" | Out-Null
        
        Start-Sleep -Seconds 5
        
        $Status = Get-ConnectorStatus
        if ($Status -and $Status.connector.state -eq "PAUSED") {
            Write-Log "[OK] Connector paused successfully" "INFO"
            return $true
        }
        else {
            Write-Log "Pause failed: state = $($Status.connector.state)" "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "Pause API call failed: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Resume-Connector {
    <#
    .SYNOPSIS
    Resume the connector (set to RUNNING state)
    #>
    Write-Log "Sending connector resume request..." "INFO"
    
    try {
        Invoke-RestMethod `
            -Uri "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/resume" `
            -Method Put `
            -TimeoutSec 30 `
            -ContentType "application/json" | Out-Null
        
        Start-Sleep -Seconds 10
        
        $Status = Get-ConnectorStatus
        if ($Status -and $Status.connector.state -eq "RUNNING") {
            $RunningTasks = ($Status.tasks | Where-Object { $_.state -eq "RUNNING" }).Count
            $TotalTasks = $Status.tasks.Count
            
            Write-Log "[OK] Connector resumed (Tasks: $RunningTasks/$TotalTasks)" "INFO"
            return $true
        }
        else {
            Write-Log "Resume failed: state = $($Status.connector.state)" "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "Resume API call failed: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Send-Alert {
    param(
        [string]$Message,
        [string]$Level = "ERROR"
    )
    
    Write-Log "ALERT: $Message" $Level
    
    # Write to Windows Event Log
    try {
        $EventType = switch ($Level) {
            "ERROR" { "Error" }
            "WARN" { "Warning" }
            default { "Information" }
        }
        Write-EventLog -LogName Application -Source "CYNOW" -EventId 1001 -EntryType $EventType -Message $Message -ErrorAction SilentlyContinue
    }
    catch {
        # Ignore event log write failures
    }
    
    # TODO: Send email, Slack, Teams notifications
}

function Wait-ForRecovery {
    <#
    .SYNOPSIS
    Wait until Oracle recovers
    .DESCRIPTION
    Test Oracle connection every minute and return true when recovered
    #>
    param(
        [int]$MaxWaitMinutes = 30  # Max wait time (minutes)
    )
    
    Write-Log "========================================" "INFO"
    Write-Log "Entering recovery wait mode" "INFO"
    Write-Log "Will check Oracle recovery every $RECOVERY_CHECK_INTERVAL seconds" "INFO"
    Write-Log "Max wait time: $MaxWaitMinutes minutes" "INFO"
    Write-Log "========================================" "INFO"
    
    $StartTime = Get-Date
    $CheckCount = 0
    
    while ($true) {
        $CheckCount++
        $ElapsedMinutes = ((Get-Date) - $StartTime).TotalMinutes
        
        Write-Log "[$CheckCount] Checking Oracle connection... (elapsed: $([int]$ElapsedMinutes) min)"
        
        # Test Oracle connection
        if (Test-OracleConnection) {
            Write-Log "[OK] Oracle has recovered!" "INFO"
            return $true
        }
        else {
            Write-Log "Oracle not recovered yet. Will recheck in $RECOVERY_CHECK_INTERVAL sec..." "WARN"
        }
        
        # Check max wait time exceeded
        if ($ElapsedMinutes -ge $MaxWaitMinutes) {
            Write-Log "Max wait time ($MaxWaitMinutes min) exceeded. Ending recovery wait." "ERROR"
            Send-Alert "Oracle did not recover after $MaxWaitMinutes minutes. Manual intervention required." "ERROR"
            return $false
        }
        
        Start-Sleep -Seconds $RECOVERY_CHECK_INTERVAL
    }
}

# ========================================
# Main Monitoring Loop
# ========================================

Write-Log "========================================" "INFO"
Write-Log "Debezium Smart Monitoring Started" "INFO"
Write-Log "Connector: $CONNECTOR_NAME" "INFO"
Write-Log "Kafka Connect: $KAFKA_CONNECT_URL" "INFO"
Write-Log "Oracle: $ORACLE_HOST`:$ORACLE_PORT" "INFO"
Write-Log "Normal check interval: $CHECK_INTERVAL sec" "INFO"
Write-Log "Recovery check interval: $RECOVERY_CHECK_INTERVAL sec" "INFO"
Write-Log "========================================" "INFO"

$ApiFailCount = 0
$IsInRecoveryMode = $false

while ($true) {
    try {
        $Status = Get-ConnectorStatus
        
        if ($Status -eq $null) {
            # Kafka Connect API not responding
            $ApiFailCount++
            Write-Log "Kafka Connect API not responding (attempt $ApiFailCount/$MAX_API_RETRIES)" "ERROR"
            
            if ($ApiFailCount -ge $MAX_API_RETRIES) {
                Send-Alert "Kafka Connect not responding after $MAX_API_RETRIES attempts. Check service status." "ERROR"
                $ApiFailCount = 0
            }
            
            Start-Sleep -Seconds $CHECK_INTERVAL
            continue
        }
        
        # API responded successfully
        $ApiFailCount = 0
        $ConnectorState = $Status.connector.state
        $TasksCount = $Status.tasks.Count
        $RunningTasks = ($Status.tasks | Where-Object { $_.state -eq "RUNNING" }).Count
        $FailedTasks = ($Status.tasks | Where-Object { $_.state -eq "FAILED" }).Count
        
        Write-Log "Status: $ConnectorState | Tasks: $RunningTasks/$TasksCount (failed: $FailedTasks)"
        
        # ===== State Handling =====
        
        if ($IsInRecoveryMode) {
            # Recovery wait mode
            if ($ConnectorState -eq "PAUSED") {
                Write-Log "Recovery mode: Maintaining PAUSED state"
                
                # Test Oracle connection
                if (Test-OracleConnection) {
                    Write-Log "[OK] Oracle recovery detected! Attempting to resume connector..." "INFO"
                    
                    if (Resume-Connector) {
                        Write-Log "[OK] Connector resumed successfully!" "INFO"
                        Send-Alert "Debezium Connector has recovered and resumed." "INFO"
                        $IsInRecoveryMode = $false
                    }
                    else {
                        Write-Log "Connector resume failed. Will retry in next cycle..." "WARN"
                    }
                }
                else {
                    Write-Log "Oracle not recovered yet. Continuing to wait..." "INFO"
                }
            }
            else {
                Write-Log "In recovery mode but state is not PAUSED: $ConnectorState" "WARN"
                $IsInRecoveryMode = $false
            }
        }
        else {
            # Normal monitoring mode
            
            if ($ConnectorState -eq "FAILED" -or $FailedTasks -gt 0) {
                # Failure detected
                Write-Log "========================================" "ERROR"
                Write-Log "FAILURE DETECTED!" "ERROR"
                Write-Log "Connector: $ConnectorState | Failed Tasks: $FailedTasks" "ERROR"
                Write-Log "========================================" "ERROR"
                
                Send-Alert "Debezium Connector failure detected (state: $ConnectorState, failed tasks: $FailedTasks)" "ERROR"
                
                # Pause immediately
                if (Pause-Connector) {
                    Write-Log "[OK] Connector paused. Entering recovery wait mode." "INFO"
                    $IsInRecoveryMode = $true
                    
                    # Start Oracle recovery wait
                    Wait-ForRecovery -MaxWaitMinutes 30
                    
                    # Resume attempt will happen in next loop iteration
                }
                else {
                    Write-Log "Connector pause failed. Will retry in next cycle..." "ERROR"
                }
            }
            elseif ($ConnectorState -eq "RUNNING" -and $RunningTasks -eq 0 -and $TasksCount -gt 0) {
                # Connector is RUNNING but no tasks are running
                Write-Log "ABNORMAL state: Connector is RUNNING but no tasks are running" "WARN"
                
                Send-Alert "Debezium Connector abnormal state: No tasks are running." "WARN"
                
                if (Pause-Connector) {
                    $IsInRecoveryMode = $true
                    Wait-ForRecovery -MaxWaitMinutes 30
                }
            }
            elseif ($ConnectorState -eq "RUNNING" -and $RunningTasks -eq $TasksCount) {
                # Fully healthy state
                Write-Log "[OK] Operating normally" "INFO"
            }
            else {
                # Other states
                Write-Log "State: $ConnectorState (attention needed)" "WARN"
            }
        }
        
    }
    catch {
        Write-Log "Monitoring loop error: $($_.Exception.Message)" "ERROR"
        Write-Log "Stack Trace: $($_.ScriptStackTrace)" "ERROR"
    }
    
    # Wait until next check
    Start-Sleep -Seconds $CHECK_INTERVAL
}
