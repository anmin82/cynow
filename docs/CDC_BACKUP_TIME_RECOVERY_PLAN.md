# Debezium CDC 백업 시간 장애 복구 계획서

## 📋 문제 정의

### 현상
- **발생 시간**: 매일 새벽 2시경
- **원인**: Oracle 서버 전체 백업 수행
- **영향**:
  - 순간적인 리소스 부족 (CPU, Memory, I/O)
  - Oracle Listener 일시 중단 또는 응답 지연
  - Debezium Oracle Connector CDC 시도 중 연결 실패
  - Kafka Connect Worker 오류 발생
  - CDC 동기화 중단 → 과거 데이터에 멈춤
  - PostgreSQL 동기화 테이블 업데이트 중단
  - CYNOW VIEW 데이터 갱신 중단

### 영향 범위
```
Oracle (FCMS) [백업중 🔥]
    ↓ (Debezium 죽음 ❌)
Kafka Topics (동기화 중단 ⚠️)
    ↓ (Kafka Sink 동작 안함 ❌)
PostgreSQL (과거 데이터 고정 ⏸️)
    ↓
CYNOW Views (오래된 데이터 📊)
    ↓
대시보드/보고서 (부정확 ⚠️)
```

---

## 🎯 해결 전략 (4단계 접근)

### 전략 1: 예방 (Prevention)
백업 시간대에 CDC를 우회하거나 일시 중지

### 전략 2: 복원력 (Resilience)
Debezium과 Kafka의 자동 복구 능력 강화

### 전략 3: 감지 (Detection)
문제 발생 즉시 탐지 및 알림

### 전략 4: 복구 (Recovery)
자동 재시작 및 데이터 정합성 검증

---

## 📝 상세 해결 방안

## 방안 1: 백업 시간대 CDC 일시 중지 ⭐ 권장

### 개념
백업이 진행되는 시간대(새벽 1:50 ~ 2:30)에는 Debezium Connector를 일시 중지하고, 백업 완료 후 재개

### 장점
- ✅ 근본적인 충돌 방지
- ✅ Oracle 부하 감소
- ✅ 안정적인 백업 보장

### 구현 방법

#### 1-1. Kafka Connect REST API를 통한 자동화

**스크립트**: `deploy/pause_debezium_for_backup.ps1`

```powershell
# Debezium Connector 백업 시간 자동 중지/재개 스크립트

# 설정
$KAFKA_CONNECT_URL = "http://localhost:8083"  # Kafka Connect REST API
$CONNECTOR_NAME = "fcms-oracle-connector"     # Debezium Connector 이름
$LOG_FILE = "C:\cynow\logs\debezium_pause_resume.log"

function Write-Log {
    param($Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] $Message"
    Write-Output $LogMessage
    Add-Content -Path $LOG_FILE -Value $LogMessage
}

function Pause-DebeziumConnector {
    Write-Log "Debezium Connector 일시 중지 시작: $CONNECTOR_NAME"
    
    try {
        $Response = Invoke-RestMethod `
            -Uri "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/pause" `
            -Method Put `
            -ContentType "application/json"
        
        Write-Log "Connector 일시 중지 성공"
        
        # 상태 확인
        Start-Sleep -Seconds 5
        $Status = Invoke-RestMethod `
            -Uri "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/status" `
            -Method Get
        
        Write-Log "현재 상태: $($Status.connector.state)"
        return $true
    }
    catch {
        Write-Log "오류 발생: $($_.Exception.Message)"
        return $false
    }
}

function Resume-DebeziumConnector {
    Write-Log "Debezium Connector 재개 시작: $CONNECTOR_NAME"
    
    try {
        $Response = Invoke-RestMethod `
            -Uri "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/resume" `
            -Method Put `
            -ContentType "application/json"
        
        Write-Log "Connector 재개 성공"
        
        # 상태 확인
        Start-Sleep -Seconds 5
        $Status = Invoke-RestMethod `
            -Uri "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/status" `
            -Method Get
        
        Write-Log "현재 상태: $($Status.connector.state)"
        Write-Log "Tasks: $($Status.tasks.Count)개"
        
        return $true
    }
    catch {
        Write-Log "오류 발생: $($_.Exception.Message)"
        return $false
    }
}

# 메인 로직
$Action = $args[0]  # "pause" 또는 "resume"

Write-Log "=========================================="
Write-Log "작업: $Action"

if ($Action -eq "pause") {
    Pause-DebeziumConnector
}
elseif ($Action -eq "resume") {
    Resume-DebeziumConnector
}
else {
    Write-Log "잘못된 인자: $Action (pause 또는 resume 사용)"
    exit 1
}

Write-Log "=========================================="
```

#### 1-2. Windows 작업 스케줄러 등록

**일시 중지 작업** (새벽 1:50)
```powershell
$ActionPause = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -File `"C:\cynow\deploy\pause_debezium_for_backup.ps1`" pause"

$TriggerPause = New-ScheduledTaskTrigger -Daily -At "01:50AM"

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName "Debezium Pause for Backup" `
    -Action $ActionPause `
    -Trigger $TriggerPause `
    -Settings $Settings `
    -Description "Oracle 백업 전 Debezium 일시 중지"
```

**재개 작업** (새벽 2:30)
```powershell
$ActionResume = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -File `"C:\cynow\deploy\pause_debezium_for_backup.ps1`" resume"

$TriggerResume = New-ScheduledTaskTrigger -Daily -At "02:30AM"

Register-ScheduledTask `
    -TaskName "Debezium Resume after Backup" `
    -Action $ActionResume `
    -Trigger $TriggerResume `
    -Settings $Settings `
    -Description "Oracle 백업 후 Debezium 재개"
```

---

## 방안 2: Debezium 자동 재시작 및 복구

### 2-1. Debezium Connector 설정 강화

**connector-config.json** 수정:

```json
{
  "name": "fcms-oracle-connector",
  "config": {
    "connector.class": "io.debezium.connector.oracle.OracleConnector",
    
    // ... 기존 설정 ...
    
    // ===== 에러 핸들링 및 복구 설정 =====
    
    // 재시도 설정
    "errors.retry.timeout": "300000",
    "errors.retry.delay.initial.ms": "1000",
    "errors.retry.delay.max.ms": "60000",
    
    // 에러 허용 (일시적 네트워크 오류 등)
    "errors.tolerance": "all",
    "errors.log.enable": true,
    "errors.log.include.messages": true,
    
    // Dead Letter Queue (DLQ) 설정
    "errors.deadletterqueue.topic.name": "dlq-fcms-oracle",
    "errors.deadletterqueue.topic.replication.factor": 1,
    "errors.deadletterqueue.context.headers.enable": true,
    
    // Oracle 연결 설정 강화
    "database.connection.adapter": "logminer",
    "log.mining.strategy": "online_catalog",
    "log.mining.continuous.mine": true,
    
    // 하트비트 설정 (연결 상태 체크)
    "heartbeat.interval.ms": "10000",
    "heartbeat.action.query": "SELECT 1 FROM DUAL",
    
    // 타임아웃 설정
    "database.query.timeout.ms": "60000",
    "connect.timeout.ms": "30000",
    
    // 백오프 설정 (재연결 시도)
    "connect.backoff.initial.delay.ms": "5000",
    "connect.backoff.max.delay.ms": "120000",
    
    // 스냅샷 복구 설정
    "snapshot.mode": "when_needed",
    "snapshot.locking.mode": "none",
    
    // 로그 레벨
    "log.level": "INFO"
  }
}
```

### 2-2. Kafka Connect Worker 설정

**connect-distributed.properties** 수정:

```properties
# Kafka Connect Worker 설정

# 재시작 정책
task.shutdown.graceful.timeout.ms=30000
offset.flush.interval.ms=60000
offset.flush.timeout.ms=5000

# 에러 핸들링
errors.retry.timeout=300000
errors.retry.delay.max.ms=60000
errors.tolerance=all
errors.log.enable=true

# 헬스체크
rest.advertised.host.name=localhost
rest.port=8083

# 재시작 정책 (실패 시 자동 재시작)
# 이것은 Kafka Connect 2.3.0+ 버전에서 지원
connector.client.config.override.policy=All
```

### 2-3. systemd/Windows Service 자동 재시작

#### Linux (systemd)

**/etc/systemd/system/kafka-connect.service**:

```ini
[Unit]
Description=Kafka Connect Service
After=network.target kafka.service

[Service]
Type=simple
User=kafka
ExecStart=/opt/kafka/bin/connect-distributed.sh /opt/kafka/config/connect-distributed.properties
Restart=always
RestartSec=30
StartLimitInterval=300
StartLimitBurst=5

# 로그
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### Windows (NSSM - Non-Sucking Service Manager)

```cmd
# NSSM 다운로드 및 설치
# https://nssm.cc/download

# Kafka Connect를 Windows 서비스로 등록
nssm install KafkaConnect "C:\kafka\bin\windows\connect-distributed.bat" "C:\kafka\config\connect-distributed.properties"

# 자동 재시작 설정
nssm set KafkaConnect AppRestartDelay 30000
nssm set KafkaConnect AppStopMethodSkip 0
nssm set KafkaConnect AppExit Default Restart

# 서비스 시작
nssm start KafkaConnect
```

---

## 방안 3: 모니터링 및 자동 복구 시스템 구축

### 3-1. Debezium 상태 모니터링 스크립트

**deploy/monitor_debezium.ps1**:

```powershell
# Debezium Connector 상태 모니터링 및 자동 복구

# 설정
$KAFKA_CONNECT_URL = "http://localhost:8083"
$CONNECTOR_NAME = "fcms-oracle-connector"
$LOG_FILE = "C:\cynow\logs\debezium_monitor.log"
$CHECK_INTERVAL = 60  # 60초마다 체크
$MAX_RETRIES = 3

function Write-Log {
    param($Message, $Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Write-Output $LogMessage
    Add-Content -Path $LOG_FILE -Value $LogMessage
}

function Get-ConnectorStatus {
    try {
        $Status = Invoke-RestMethod `
            -Uri "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/status" `
            -Method Get `
            -TimeoutSec 10
        
        return $Status
    }
    catch {
        Write-Log "상태 조회 실패: $($_.Exception.Message)" "ERROR"
        return $null
    }
}

function Restart-DebeziumConnector {
    Write-Log "Connector 재시작 시도..." "WARN"
    
    try {
        # 1. Connector 재시작
        Invoke-RestMethod `
            -Uri "$KAFKA_CONNECT_URL/connectors/$CONNECTOR_NAME/restart?includeTasks=true" `
            -Method Post `
            -TimeoutSec 30
        
        Write-Log "Connector 재시작 명령 전송 성공" "INFO"
        
        # 2. 30초 대기
        Start-Sleep -Seconds 30
        
        # 3. 상태 확인
        $Status = Get-ConnectorStatus
        if ($Status -and $Status.connector.state -eq "RUNNING") {
            Write-Log "Connector 재시작 성공: RUNNING" "INFO"
            return $true
        }
        else {
            Write-Log "Connector 재시작 후 여전히 문제 있음: $($Status.connector.state)" "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "재시작 실패: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

function Send-Alert {
    param($Message)
    
    # TODO: 이메일, Slack, Teams 등으로 알림 전송
    Write-Log "🚨 알림: $Message" "ALERT"
    
    # 예시: Windows 이벤트 로그에 기록
    # Write-EventLog -LogName Application -Source "CYNOW" -EventId 1001 -EntryType Error -Message $Message
}

# 메인 모니터링 루프
Write-Log "=========================================="
Write-Log "Debezium 모니터링 시작"
Write-Log "Connector: $CONNECTOR_NAME"
Write-Log "확인 간격: $CHECK_INTERVAL 초"
Write-Log "=========================================="

$FailCount = 0

while ($true) {
    $Status = Get-ConnectorStatus
    
    if ($Status -eq $null) {
        $FailCount++
        Write-Log "Kafka Connect API 응답 없음 (시도 $FailCount/$MAX_RETRIES)" "ERROR"
        
        if ($FailCount -ge $MAX_RETRIES) {
            Send-Alert "Kafka Connect가 응답하지 않습니다. 수동 확인 필요."
            $FailCount = 0  # 리셋하여 계속 모니터링
        }
    }
    else {
        $ConnectorState = $Status.connector.state
        $TasksCount = $Status.tasks.Count
        $FailedTasks = ($Status.tasks | Where-Object { $_.state -ne "RUNNING" }).Count
        
        Write-Log "Connector: $ConnectorState | Tasks: $TasksCount (실패: $FailedTasks)" "INFO"
        
        # Connector가 FAILED 상태
        if ($ConnectorState -eq "FAILED") {
            Write-Log "⚠️ Connector 실패 상태 감지!" "ERROR"
            Send-Alert "Debezium Connector가 FAILED 상태입니다."
            
            $RestartSuccess = Restart-DebeziumConnector
            if (-not $RestartSuccess) {
                Send-Alert "Connector 자동 재시작 실패. 수동 개입 필요."
            }
        }
        
        # Task가 FAILED 상태
        if ($FailedTasks -gt 0) {
            Write-Log "⚠️ 실패한 Task 발견: $FailedTasks 개" "ERROR"
            Send-Alert "Debezium Task $FailedTasks 개가 실패 상태입니다."
            
            $RestartSuccess = Restart-DebeziumConnector
            if (-not $RestartSuccess) {
                Send-Alert "Task 자동 재시작 실패. 수동 개입 필요."
            }
        }
        
        $FailCount = 0  # 성공적으로 확인했으면 카운터 리셋
    }
    
    Start-Sleep -Seconds $CHECK_INTERVAL
}
```

### 3-2. Windows 서비스로 등록 (NSSM)

```cmd
nssm install DebeziumMonitor "powershell.exe" "-ExecutionPolicy Bypass -File C:\cynow\deploy\monitor_debezium.ps1"
nssm set DebeziumMonitor AppDirectory "C:\cynow"
nssm set DebeziumMonitor AppStdout "C:\cynow\logs\monitor_stdout.log"
nssm set DebeziumMonitor AppStderr "C:\cynow\logs\monitor_stderr.log"
nssm set DebeziumMonitor Start SERVICE_AUTO_START
nssm start DebeziumMonitor
```

---

## 방안 4: 데이터 정합성 검증 및 재동기화

### 4-1. CDC 동기화 상태 확인 Django Management Command

**core/management/commands/check_cdc_lag.py**:

```python
"""CDC 동기화 지연 확인"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger('core')


class Command(BaseCommand):
    help = 'CDC 동기화 지연 시간 확인 및 알림'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold',
            type=int,
            default=60,
            help='알림 임계값 (분 단위, 기본 60분)'
        )

    def handle(self, *args, **options):
        threshold_minutes = options['threshold']
        threshold_time = timezone.now() - timedelta(minutes=threshold_minutes)
        
        self.stdout.write(f'CDC 동기화 상태 확인 중...')
        self.stdout.write(f'임계값: {threshold_minutes}분 이전')
        
        try:
            with connection.cursor() as cursor:
                # PostgreSQL의 CDC 테이블에서 최근 업데이트 시간 확인
                # (테이블명은 실제 환경에 맞게 수정)
                
                # 예시 1: __source_ts_ms 컬럼이 있는 경우 (Debezium 메타데이터)
                cursor.execute("""
                    SELECT 
                        table_name,
                        MAX(__source_ts_ms) as last_update_ms,
                        COUNT(*) as row_count
                    FROM (
                        SELECT '__source_ts_ms' as __source_ts_ms, 'dummy' as table_name
                        -- 실제 CDC 테이블 쿼리로 변경 필요
                    ) t
                    GROUP BY table_name
                """)
                
                results = cursor.fetchall()
                
                all_ok = True
                for table_name, last_update_ms, row_count in results:
                    if last_update_ms:
                        last_update = timezone.datetime.fromtimestamp(
                            last_update_ms / 1000, 
                            tz=timezone.utc
                        )
                        lag = timezone.now() - last_update
                        
                        self.stdout.write(
                            f'테이블: {table_name} | '
                            f'마지막 업데이트: {last_update} | '
                            f'지연: {lag.total_seconds() / 60:.1f}분'
                        )
                        
                        if last_update < threshold_time:
                            self.stdout.write(
                                self.style.ERROR(
                                    f'⚠️ {table_name}: 동기화 지연 감지! '
                                    f'({lag.total_seconds() / 60:.1f}분 지연)'
                                )
                            )
                            logger.error(
                                f'CDC 동기화 지연: {table_name} - '
                                f'{lag.total_seconds() / 60:.1f}분'
                            )
                            all_ok = False
                        else:
                            self.stdout.write(
                                self.style.SUCCESS(f'✓ {table_name}: 정상')
                            )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f'⚠️ {table_name}: 타임스탬프 없음'
                            )
                        )
                
                if all_ok:
                    self.stdout.write(self.style.SUCCESS('✓ 모든 테이블 동기화 정상'))
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            '⚠️ 일부 테이블 동기화 지연 감지. '
                            'Debezium 상태를 확인하세요.'
                        )
                    )
                    # 알림 전송 (TODO: 이메일/Slack 등)
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'오류 발생: {e}'))
            logger.error(f'CDC 지연 확인 실패: {e}')
            raise
```

### 4-2. 정기적인 검증 작업

**Windows 작업 스케줄러**: 10분마다 실행

```powershell
$Action = New-ScheduledTaskAction `
    -Execute "C:\cynow\venv\Scripts\python.exe" `
    -Argument "C:\cynow\manage.py check_cdc_lag --threshold 30" `
    -WorkingDirectory "C:\cynow"

$Trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 10) `
    -RepetitionDuration ([TimeSpan]::MaxValue)

Register-ScheduledTask `
    -TaskName "CDC Lag Check" `
    -Action $Action `
    -Trigger $Trigger `
    -Description "CDC 동기화 지연 모니터링"
```

---

## 방안 5: Oracle 백업 시간 변경 협의 (장기 해결책)

### 5-1. DBA팀과 협의 사항

1. **백업 시간 변경**
   - 현재: 새벽 2:00
   - 제안: 새벽 4:00 또는 3:00
   - 이유: CYNOW 스냅샷(2:00)과 충돌 방지

2. **백업 방식 변경**
   - Hot Backup (온라인 백업) 사용
   - RMAN Incremental Backup 사용
   - Listener 중단 최소화

3. **리소스 할당**
   - 백업 전용 Resource Manager Plan
   - CDC 프로세스 우선순위 유지

---

## 📊 종합 구현 계획

### Phase 1: 긴급 대응 (즉시 ~ 1주)

| 우선순위 | 작업 | 담당 | 기간 | 비고 |
|---------|------|------|------|------|
| 🔴 높음 | Debezium 모니터링 스크립트 배포 | DevOps | 1일 | 자동 재시작 |
| 🔴 높음 | 백업 시간대 CDC 일시 중지 스크립트 | DevOps | 1일 | 임시 조치 |
| 🟡 중간 | Debezium Connector 설정 강화 | DevOps | 2일 | 에러 핸들링 |
| 🟡 중간 | CDC 동기화 지연 모니터링 | Dev | 3일 | Django command |

### Phase 2: 안정화 (1주 ~ 1개월)

| 우선순위 | 작업 | 담당 | 기간 | 비고 |
|---------|------|------|------|------|
| 🟡 중간 | Kafka Connect 자동 재시작 설정 | DevOps | 1주 | systemd/NSSM |
| 🟡 중간 | 알림 시스템 구축 (Email/Slack) | Dev | 1주 | 장애 알림 |
| 🟢 낮음 | 대시보드 모니터링 UI | Dev | 2주 | Grafana 등 |
| 🟢 낮음 | 문서화 및 운영 매뉴얼 | All | 1주 | Runbook |

### Phase 3: 근본 해결 (1개월 ~ 3개월)

| 우선순위 | 작업 | 담당 | 기간 | 비고 |
|---------|------|------|------|------|
| 🟡 중간 | Oracle 백업 시간 변경 협의 | PM + DBA | 2주 | 회의 필요 |
| 🟡 중간 | Debezium 버전 업그레이드 | DevOps | 1주 | 최신 안정화 버전 |
| 🟢 낮음 | CDC 이중화 구성 검토 | DevOps | 3주 | Active-Standby |
| 🟢 낮음 | 데이터 정합성 자동 복구 | Dev | 4주 | 재동기화 자동화 |

---

## 🛠️ 즉시 적용 가능한 Quick Win

### 1단계: 오늘 배포 (30분 소요)

```powershell
# 1. 모니터링 스크립트 실행 (백그라운드)
Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File C:\cynow\deploy\monitor_debezium.ps1" -WindowStyle Hidden

# 2. 백업 시간 CDC 중지 작업 등록
# (위의 Windows 작업 스케줄러 명령어 실행)
```

### 2단계: 내일 확인 (10분 소요)

```powershell
# 로그 확인
Get-Content C:\cynow\logs\debezium_monitor.log -Tail 50
Get-Content C:\cynow\logs\debezium_pause_resume.log -Tail 20

# Debezium 상태 확인
Invoke-RestMethod -Uri "http://localhost:8083/connectors/fcms-oracle-connector/status"
```

### 3단계: 1주 후 평가

- [ ] 새벽 2시 장애 발생 여부 확인
- [ ] 자동 재시작 동작 확인
- [ ] 로그 분석 및 개선점 도출

---

## 📞 비상 연락망

### 장애 발생 시 대응 순서

1. **자동 복구 시도** (모니터링 스크립트)
   - 3회 재시도
   - 로그 기록

2. **자동 복구 실패 시 알림**
   - Email: ops-team@company.com
   - Slack: #cynow-alerts
   - SMS: 담당자 휴대폰

3. **수동 개입**
   - DevOps 엔지니어 확인
   - Kafka Connect 수동 재시작
   - Oracle 연결 상태 확인

### 수동 복구 절차

```bash
# 1. Kafka Connect 재시작
systemctl restart kafka-connect  # Linux
# 또는
Restart-Service KafkaConnect  # Windows

# 2. Debezium Connector 재시작
curl -X POST http://localhost:8083/connectors/fcms-oracle-connector/restart

# 3. 상태 확인
curl http://localhost:8083/connectors/fcms-oracle-connector/status | jq

# 4. Kafka Topic 확인
kafka-console-consumer --bootstrap-server localhost:9092 --topic fcms.FCMS.CF4_YC --max-messages 10

# 5. PostgreSQL 동기화 확인
psql -U postgres -d cycy_db -c "SELECT COUNT(*), MAX(__source_ts_ms) FROM fcms_cdc.cf4_yc;"
```

---

## 📈 성공 지표 (KPI)

### 목표
- **CDC 가용성**: 99.5% 이상
- **동기화 지연**: 평균 5분 이내
- **백업 시간 장애**: 월 0회
- **자동 복구 성공률**: 95% 이상

### 측정 방법
1. **일일 체크**
   - 새벽 2시 전후 로그 확인
   - CDC 지연 시간 측정

2. **주간 리포트**
   - 장애 발생 횟수
   - 평균 복구 시간
   - 데이터 정합성 이슈

3. **월간 리뷰**
   - KPI 달성률
   - 개선 사항 도출
   - 다음 달 계획

---

## 📚 참고 자료

### Debezium 공식 문서
- [Oracle Connector Configuration](https://debezium.io/documentation/reference/stable/connectors/oracle.html)
- [Error Handling](https://debezium.io/documentation/reference/stable/configuration/error-handling.html)

### Kafka Connect
- [REST API Reference](https://docs.confluent.io/platform/current/connect/references/restapi.html)
- [Connector Configuration](https://kafka.apache.org/documentation/#connect_configuring)

### 내부 문서
- `docs/DEBEZIUM_FIX.md`
- `docs/CDC_TABLES_ANALYSIS.md`
- `deploy/DEPLOY_CHECKLIST.md`

---

## ✅ 체크리스트

### 배포 전 확인사항
- [ ] Kafka Connect REST API 접근 가능 확인
- [ ] Connector 이름 확인 (`fcms-oracle-connector`)
- [ ] 백업 시간 정확히 파악 (01:50 ~ 02:30)
- [ ] 로그 디렉토리 생성 (`C:\cynow\logs`)
- [ ] PowerShell 실행 정책 확인

### 배포 후 확인사항
- [ ] 모니터링 스크립트 정상 동작
- [ ] 백업 시간 자동 중지/재개 동작
- [ ] 로그 파일 생성 및 기록
- [ ] Windows 작업 스케줄러 등록 확인

### 1주 후 점검
- [ ] 새벽 2시 장애 0건 달성
- [ ] 자동 재시작 정상 동작 확인
- [ ] 데이터 정합성 이상 없음
- [ ] 로그 분석 완료

---

**작성일**: 2025-12-19
**작성자**: CYNOW DevOps Team
**버전**: 1.0
**검토자**: [담당 PM, DBA]













