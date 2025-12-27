# Debezium Connector 백업 시간 자동 중지/재개 스크립트
# 사용법: .\pause_debezium_for_backup.ps1 pause|resume

# 오류 발생 시 중단
$ErrorActionPreference = "Stop"

# ========================================
# 설정 (환경에 맞게 수정)
# ========================================
$KAFKA_CONNECT_URL = "http://localhost:8083"  # Kafka Connect REST API URL
$CONNECTOR_NAME = "fcms-oracle-connector"     # Debezium Connector 이름

# 로그 디렉토리 및 파일
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$LogDir = Join-Path $ProjectRoot "logs"
if (-Not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$LogDate = Get-Date -Format "yyyyMM"
$LogFile = Join-Path $LogDir "debezium_pause_resume_$LogDate.log"

# ========================================
# 함수 정의
# ========================================

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Write-Output $LogMessage
    Add-Content -Path $LogFile -Value $LogMessage
}

function Get-ConnectorStatus {
    Write-Log "Connector 상태 조회 중..."
    
    try {
        $Response = Invoke-RestMethod `
            -Uri "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/status" `
            -Method Get `
            -TimeoutSec 10 `
            -ContentType "application/json"
        
        Write-Log "Connector 상태: $($Response.connector.state)"
        
        if ($Response.tasks) {
            Write-Log "Tasks: $($Response.tasks.Count)개"
            foreach ($task in $Response.tasks) {
                Write-Log "  Task $($task.id): $($task.state)"
            }
        }
        
        return $Response
    }
    catch {
        Write-Log "상태 조회 실패: $($_.Exception.Message)" "ERROR"
        return $null
    }
}

function Pause-DebeziumConnector {
    Write-Log "========================================" "INFO"
    Write-Log "Debezium Connector 일시 중지 시작" "INFO"
    Write-Log "Connector: $CONNECTOR_NAME" "INFO"
    Write-Log "========================================" "INFO"
    
    try {
        # 현재 상태 확인
        $CurrentStatus = Get-ConnectorStatus
        
        if ($CurrentStatus -eq $null) {
            Write-Log "Kafka Connect에 연결할 수 없습니다. 서비스 상태를 확인하세요." "ERROR"
            return $false
        }
        
        if ($CurrentStatus.connector.state -eq "PAUSED") {
            Write-Log "Connector가 이미 일시 중지 상태입니다." "WARN"
            return $true
        }
        
        # Connector 일시 중지
        Write-Log "일시 중지 요청 전송 중..."
        
        $Response = Invoke-RestMethod `
            -Uri "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/pause" `
            -Method Put `
            -TimeoutSec 30 `
            -ContentType "application/json"
        
        Write-Log "일시 중지 요청 전송 완료" "INFO"
        
        # 5초 대기 후 상태 확인
        Start-Sleep -Seconds 5
        
        $NewStatus = Get-ConnectorStatus
        
        if ($NewStatus -and $NewStatus.connector.state -eq "PAUSED") {
            Write-Log "✓ Connector 일시 중지 성공!" "INFO"
            return $true
        }
        else {
            Write-Log "일시 중지 후 상태가 예상과 다릅니다: $($NewStatus.connector.state)" "WARN"
            return $false
        }
    }
    catch {
        Write-Log "일시 중지 실패: $($_.Exception.Message)" "ERROR"
        Write-Log "Stack Trace: $($_.ScriptStackTrace)" "ERROR"
        return $false
    }
}

function Resume-DebeziumConnector {
    Write-Log "========================================" "INFO"
    Write-Log "Debezium Connector 재개 시작" "INFO"
    Write-Log "Connector: $CONNECTOR_NAME" "INFO"
    Write-Log "========================================" "INFO"
    
    try {
        # 현재 상태 확인
        $CurrentStatus = Get-ConnectorStatus
        
        if ($CurrentStatus -eq $null) {
            Write-Log "Kafka Connect에 연결할 수 없습니다. 서비스 상태를 확인하세요." "ERROR"
            return $false
        }
        
        if ($CurrentStatus.connector.state -eq "RUNNING") {
            Write-Log "Connector가 이미 실행 중입니다." "INFO"
            return $true
        }
        
        # Connector 재개
        Write-Log "재개 요청 전송 중..."
        
        $Response = Invoke-RestMethod `
            -Uri "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/resume" `
            -Method Put `
            -TimeoutSec 30 `
            -ContentType "application/json"
        
        Write-Log "재개 요청 전송 완료" "INFO"
        
        # 10초 대기 (Connector가 RUNNING 상태로 전환되는 시간)
        Write-Log "10초 대기 중..."
        Start-Sleep -Seconds 10
        
        $NewStatus = Get-ConnectorStatus
        
        if ($NewStatus -and $NewStatus.connector.state -eq "RUNNING") {
            Write-Log "✓ Connector 재개 성공!" "INFO"
            
            # Tasks 상태도 확인
            $RunningTasks = ($NewStatus.tasks | Where-Object { $_.state -eq "RUNNING" }).Count
            $TotalTasks = $NewStatus.tasks.Count
            Write-Log "실행 중인 Tasks: $RunningTasks/$TotalTasks" "INFO"
            
            if ($RunningTasks -eq $TotalTasks) {
                Write-Log "✓ 모든 Tasks가 정상 실행 중입니다." "INFO"
            }
            else {
                Write-Log "일부 Tasks가 실행되지 않았습니다. 확인 필요." "WARN"
            }
            
            return $true
        }
        else {
            Write-Log "재개 후 상태가 예상과 다릅니다: $($NewStatus.connector.state)" "WARN"
            
            # FAILED 상태인 경우 재시작 시도
            if ($NewStatus.connector.state -eq "FAILED") {
                Write-Log "FAILED 상태 감지. 재시작을 시도합니다..." "WARN"
                
                Invoke-RestMethod `
                    -Uri "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/restart?includeTasks=true" `
                    -Method Post `
                    -TimeoutSec 30
                
                Start-Sleep -Seconds 10
                
                $RestartStatus = Get-ConnectorStatus
                if ($RestartStatus -and $RestartStatus.connector.state -eq "RUNNING") {
                    Write-Log "✓ 재시작 후 정상 실행 중입니다." "INFO"
                    return $true
                }
                else {
                    Write-Log "재시작 후에도 문제가 있습니다. 수동 확인 필요." "ERROR"
                    return $false
                }
            }
            
            return $false
        }
    }
    catch {
        Write-Log "재개 실패: $($_.Exception.Message)" "ERROR"
        Write-Log "Stack Trace: $($_.ScriptStackTrace)" "ERROR"
        return $false
    }
}

# ========================================
# 메인 로직
# ========================================

# 인자 확인
if ($args.Count -eq 0) {
    Write-Log "사용법: .\pause_debezium_for_backup.ps1 pause|resume" "ERROR"
    Write-Output "사용법: .\pause_debezium_for_backup.ps1 pause|resume"
    exit 1
}

$Action = $args[0].ToLower()

Write-Log "========================================" "INFO"
Write-Log "스크립트 시작: pause_debezium_for_backup.ps1" "INFO"
Write-Log "작업: $Action" "INFO"
Write-Log "Kafka Connect: $KAFKA_CONNECT_URL" "INFO"
Write-Log "Connector: $CONNECTOR_NAME" "INFO"
Write-Log "========================================" "INFO"

$Success = $false

try {
    if ($Action -eq "pause") {
        $Success = Pause-DebeziumConnector
    }
    elseif ($Action -eq "resume") {
        $Success = Resume-DebeziumConnector
    }
    else {
        Write-Log "잘못된 인자: $Action (pause 또는 resume만 허용)" "ERROR"
        Write-Output "오류: 잘못된 인자 '$Action'"
        Write-Output "사용법: .\pause_debezium_for_backup.ps1 pause|resume"
        exit 1
    }
    
    if ($Success) {
        Write-Log "========================================" "INFO"
        Write-Log "작업 완료: 성공" "INFO"
        Write-Log "========================================" "INFO"
        exit 0
    }
    else {
        Write-Log "========================================" "WARN"
        Write-Log "작업 완료: 실패 (종료 코드 1)" "WARN"
        Write-Log "========================================" "WARN"
        exit 1
    }
}
catch {
    Write-Log "예상치 못한 오류 발생: $($_.Exception.Message)" "ERROR"
    Write-Log "Stack Trace: $($_.ScriptStackTrace)" "ERROR"
    Write-Log "========================================" "ERROR"
    Write-Log "작업 완료: 오류 (종료 코드 1)" "ERROR"
    Write-Log "========================================" "ERROR"
    exit 1
}



















