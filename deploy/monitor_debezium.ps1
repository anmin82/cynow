# Debezium Connector 상태 모니터링 및 자동 복구 스크립트
# Windows 서비스로 등록하여 백그라운드에서 지속 실행

# 오류 발생 시에도 계속 실행
$ErrorActionPreference = "Continue"

# ========================================
# 설정 (환경에 맞게 수정)
# ========================================
$KAFKA_CONNECT_URL = "http://localhost:8083"  # Kafka Connect REST API URL
$CONNECTOR_NAME = "fcms-oracle-connector"     # Debezium Connector 이름
$CHECK_INTERVAL = 60                          # 확인 간격 (초)
$MAX_RETRIES = 3                              # API 실패 시 최대 재시도 횟수
$RESTART_COOLDOWN = 300                       # 재시작 후 대기 시간 (초, 5분)

# 로그 설정
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$LogDir = Join-Path $ProjectRoot "logs"
if (-Not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$LogDate = Get-Date -Format "yyyyMM"
$LogFile = Join-Path $LogDir "debezium_monitor_$LogDate.log"

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
    
    try {
        Add-Content -Path $LogFile -Value $LogMessage
    }
    catch {
        # 로그 파일 쓰기 실패 시에도 계속 진행
        Write-Output "로그 파일 쓰기 실패: $($_.Exception.Message)"
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
        Write-Log "상태 조회 실패: $($_.Exception.Message)" "ERROR"
        return $null
    }
}

function Restart-DebeziumConnector {
    Write-Log "========================================" "WARN"
    Write-Log "Connector 재시작 시도..." "WARN"
    Write-Log "========================================" "WARN"
    
    try {
        # 재시작 요청 (includeTasks=true로 모든 Task도 함께 재시작)
        Invoke-RestMethod `
            -Uri "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/restart?includeTasks=true&onlyFailed=false" `
            -Method Post `
            -TimeoutSec 30 `
            -ContentType "application/json"
        
        Write-Log "재시작 요청 전송 완료" "INFO"
        
        # 30초 대기 (Connector가 초기화되는 시간)
        Write-Log "30초 대기 중..."
        Start-Sleep -Seconds 30
        
        # 상태 확인
        $Status = Get-ConnectorStatus
        
        if ($Status -eq $null) {
            Write-Log "재시작 후 상태 확인 실패" "ERROR"
            return $false
        }
        
        $ConnectorState = $Status.connector.state
        Write-Log "재시작 후 Connector 상태: $ConnectorState"
        
        if ($ConnectorState -eq "RUNNING") {
            $RunningTasks = ($Status.tasks | Where-Object { $_.state -eq "RUNNING" }).Count
            $TotalTasks = $Status.tasks.Count
            
            Write-Log "Tasks: $RunningTasks/$TotalTasks 실행 중" "INFO"
            
            if ($RunningTasks -eq $TotalTasks) {
                Write-Log "✓ Connector 재시작 성공!" "INFO"
                return $true
            }
            else {
                Write-Log "일부 Tasks가 실행되지 않음" "WARN"
                return $false
            }
        }
        else {
            Write-Log "재시작 후에도 RUNNING 상태가 아님: $ConnectorState" "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "재시작 실패: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Send-Alert {
    param(
        [string]$Message,
        [string]$Level = "ERROR"
    )
    
    Write-Log "🚨 알림: $Message" $Level
    
    # Windows 이벤트 로그에 기록 (이벤트 뷰어에서 확인 가능)
    try {
        # Source가 없으면 생성 (관리자 권한 필요)
        if (-not [System.Diagnostics.EventLog]::SourceExists("CYNOW")) {
            # 이 명령은 관리자 권한이 필요하므로 실패할 수 있음
            # [System.Diagnostics.EventLog]::CreateEventSource("CYNOW", "Application")
        }
        
        # 이벤트 로그 작성
        $EventType = if ($Level -eq "ERROR") { "Error" } elseif ($Level -eq "WARN") { "Warning" } else { "Information" }
        Write-EventLog -LogName Application -Source "CYNOW" -EventId 1001 -EntryType $EventType -Message $Message
    }
    catch {
        Write-Log "Windows 이벤트 로그 작성 실패: $($_.Exception.Message)" "WARN"
    }
    
    # TODO: 이메일, Slack, Teams 등으로 알림 전송
    # 예시:
    # Send-MailMessage -To "ops@company.com" -Subject "CYNOW CDC Alert" -Body $Message
    # Invoke-RestMethod -Uri "https://hooks.slack.com/..." -Method Post -Body ...
}

# ========================================
# 메인 모니터링 루프
# ========================================

Write-Log "========================================" "INFO"
Write-Log "Debezium 모니터링 서비스 시작" "INFO"
Write-Log "Connector: $CONNECTOR_NAME" "INFO"
Write-Log "Kafka Connect: $KAFKA_CONNECT_URL" "INFO"
Write-Log "확인 간격: $CHECK_INTERVAL 초" "INFO"
Write-Log "최대 재시도: $MAX_RETRIES 회" "INFO"
Write-Log "========================================" "INFO"

$FailCount = 0
$LastRestartTime = (Get-Date).AddDays(-1)  # 초기값: 어제

while ($true) {
    try {
        $Status = Get-ConnectorStatus
        
        if ($Status -eq $null) {
            # API 응답 없음
            $FailCount++
            Write-Log "Kafka Connect API 응답 없음 (시도 $FailCount/$MAX_RETRIES)" "ERROR"
            
            if ($FailCount -ge $MAX_RETRIES) {
                Send-Alert "Kafka Connect가 $MAX_RETRIES 번 연속 응답하지 않습니다. Kafka Connect 서비스 상태를 확인하세요." "ERROR"
                $FailCount = 0  # 리셋하여 계속 모니터링
            }
        }
        else {
            # 정상 응답
            $ConnectorState = $Status.connector.state
            $TasksCount = $Status.tasks.Count
            $RunningTasks = ($Status.tasks | Where-Object { $_.state -eq "RUNNING" }).Count
            $FailedTasks = ($Status.tasks | Where-Object { $_.state -eq "FAILED" }).Count
            
            Write-Log "Connector: $ConnectorState | Tasks: $RunningTasks/$TasksCount (실패: $FailedTasks)"
            
            $NeedRestart = $false
            $RestartReason = ""
            
            # Connector가 FAILED 상태
            if ($ConnectorState -eq "FAILED") {
                Write-Log "⚠️ Connector FAILED 상태 감지!" "ERROR"
                $NeedRestart = $true
                $RestartReason = "Connector가 FAILED 상태입니다."
            }
            
            # Task가 FAILED 상태
            if ($FailedTasks -gt 0) {
                Write-Log "⚠️ 실패한 Task 발견: $FailedTasks 개" "ERROR"
                $NeedRestart = $true
                $RestartReason = "Task $FailedTasks 개가 FAILED 상태입니다."
            }
            
            # Connector는 RUNNING이지만 Task가 하나도 RUNNING이 아닌 경우
            if ($ConnectorState -eq "RUNNING" -and $RunningTasks -eq 0 -and $TasksCount -gt 0) {
                Write-Log "⚠️ Connector는 RUNNING이지만 실행 중인 Task가 없습니다!" "ERROR"
                $NeedRestart = $true
                $RestartReason = "실행 중인 Task가 없습니다."
            }
            
            # 재시작 필요 여부 판단
            if ($NeedRestart) {
                # 마지막 재시작 후 충분한 시간이 경과했는지 확인 (무한 루프 방지)
                $TimeSinceLastRestart = ((Get-Date) - $LastRestartTime).TotalSeconds
                
                if ($TimeSinceLastRestart -lt $RESTART_COOLDOWN) {
                    Write-Log "최근에 재시작했으므로 대기 중입니다. (남은 시간: $([int]($RESTART_COOLDOWN - $TimeSinceLastRestart))초)" "WARN"
                }
                else {
                    Send-Alert $RestartReason "ERROR"
                    
                    $RestartSuccess = Restart-DebeziumConnector
                    $LastRestartTime = Get-Date
                    
                    if ($RestartSuccess) {
                        Send-Alert "Connector 자동 재시작 성공" "INFO"
                    }
                    else {
                        Send-Alert "Connector 자동 재시작 실패. 수동 개입 필요." "ERROR"
                    }
                }
            }
            
            $FailCount = 0  # 성공적으로 확인했으면 카운터 리셋
        }
    }
    catch {
        Write-Log "모니터링 루프 오류: $($_.Exception.Message)" "ERROR"
        Write-Log "Stack Trace: $($_.ScriptStackTrace)" "ERROR"
    }
    
    # 다음 확인까지 대기
    Start-Sleep -Seconds $CHECK_INTERVAL
}













