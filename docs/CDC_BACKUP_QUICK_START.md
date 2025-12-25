# 🚀 CDC 백업 시간 장애 해결 - 빠른 시작 가이드

## ⚡ 30분만에 적용하기

### 전제 조건 확인

- [ ] Kafka Connect REST API 접근 가능 (기본: http://localhost:8083)
- [ ] Debezium Connector 이름 확인 (기본: `fcms-oracle-connector`)
- [ ] PowerShell 실행 가능
- [ ] Oracle 백업 시간 확인 (기본: 새벽 1:50 ~ 2:30)

### 1단계: Connector 이름 확인 (1분)

```powershell
# Connector 목록 조회
Invoke-RestMethod -Uri "http://localhost:8083/connectors"

# 특정 Connector 상태 확인
Invoke-RestMethod -Uri "http://localhost:8083/connectors/fcms-oracle-connector/status"
```

**Connector 이름이 다르면?**
- `deploy/pause_debezium_for_backup.ps1` 파일 수정
- `deploy/monitor_debezium.ps1` 파일 수정
- 3번째 줄 `$CONNECTOR_NAME` 변수를 실제 이름으로 변경

---

### 2단계: 스크립트 테스트 (5분)

#### 2-1. 일시 중지 테스트
```powershell
cd C:\cynow\deploy
.\pause_debezium_for_backup.ps1 pause
```

**예상 출력:**
```
[2025-12-19 10:00:00] [INFO] Connector 상태 조회 중...
[2025-12-19 10:00:01] [INFO] Connector 상태: RUNNING
[2025-12-19 10:00:01] [INFO] 일시 중지 요청 전송 중...
[2025-12-19 10:00:02] [INFO] ✓ Connector 일시 중지 성공!
```

#### 2-2. 재개 테스트
```powershell
.\pause_debezium_for_backup.ps1 resume
```

**예상 출력:**
```
[2025-12-19 10:05:00] [INFO] Connector 상태 조회 중...
[2025-12-19 10:05:01] [INFO] Connector 상태: PAUSED
[2025-12-19 10:05:01] [INFO] 재개 요청 전송 중...
[2025-12-19 10:05:12] [INFO] ✓ Connector 재개 성공!
```

#### 2-3. CDC 지연 확인 테스트
```powershell
cd C:\cynow
.\venv\Scripts\activate
python manage.py check_cdc_lag --threshold 60
```

---

### 3단계: 작업 스케줄러 등록 (10분)

#### 방법 A: PowerShell 명령어 (권장)

**관리자 권한 PowerShell** 실행 후:

```powershell
# ===== 1. 백업 전 일시 중지 작업 (새벽 1:50) =====
$ActionPause = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -NoProfile -File `"C:\cynow\deploy\pause_debezium_for_backup.ps1`" pause" `
    -WorkingDirectory "C:\cynow"

$TriggerPause = New-ScheduledTaskTrigger -Daily -At "01:50AM"

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$Principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName "CYNOW - Debezium Pause for Backup" `
    -Action $ActionPause `
    -Trigger $TriggerPause `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Oracle 백업 전 Debezium 일시 중지"

Write-Output "✓ 일시 중지 작업 등록 완료"

# ===== 2. 백업 후 재개 작업 (새벽 2:30) =====
$ActionResume = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -NoProfile -File `"C:\cynow\deploy\pause_debezium_for_backup.ps1`" resume" `
    -WorkingDirectory "C:\cynow"

$TriggerResume = New-ScheduledTaskTrigger -Daily -At "02:30AM"

Register-ScheduledTask `
    -TaskName "CYNOW - Debezium Resume after Backup" `
    -Action $ActionResume `
    -Trigger $TriggerResume `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Oracle 백업 후 Debezium 재개"

Write-Output "✓ 재개 작업 등록 완료"

# ===== 3. CDC 지연 모니터링 (10분마다) =====
$ActionCDC = New-ScheduledTaskAction `
    -Execute "C:\cynow\venv\Scripts\python.exe" `
    -Argument "C:\cynow\manage.py check_cdc_lag --threshold 30" `
    -WorkingDirectory "C:\cynow"

$TriggerCDC = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 10) `
    -RepetitionDuration ([TimeSpan]::MaxValue)

Register-ScheduledTask `
    -TaskName "CYNOW - CDC Lag Monitor" `
    -Action $ActionCDC `
    -Trigger $TriggerCDC `
    -Settings $Settings `
    -Principal $Principal `
    -Description "CDC 동기화 지연 모니터링 (10분마다)"

Write-Output "✓ CDC 지연 모니터링 작업 등록 완료"

Write-Output ""
Write-Output "========================================="
Write-Output "✓ 모든 작업 스케줄러 등록 완료!"
Write-Output "========================================="
```

#### 방법 B: GUI 사용

1. `Win + R` → `taskschd.msc` 입력
2. "작업 만들기..." 클릭
3. 상세 설정은 `CDC_BACKUP_TIME_RECOVERY_PLAN.md` 참조

---

### 4단계: 모니터링 서비스 시작 (선택사항, 5분)

#### 옵션 A: 백그라운드 프로세스로 실행

```powershell
# 백그라운드에서 실행 (PowerShell 창 닫아도 계속 실행)
Start-Process powershell `
    -ArgumentList "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File C:\cynow\deploy\monitor_debezium.ps1" `
    -WindowStyle Hidden
```

#### 옵션 B: Windows 서비스로 등록 (권장)

**NSSM 다운로드** (한번만):
```powershell
# Chocolatey로 설치
choco install nssm

# 또는 수동 다운로드
# https://nssm.cc/download
```

**서비스 등록**:
```cmd
nssm install CYNOWDebeziumMonitor "powershell.exe" "-ExecutionPolicy Bypass -NoProfile -File C:\cynow\deploy\monitor_debezium.ps1"
nssm set CYNOWDebeziumMonitor AppDirectory "C:\cynow"
nssm set CYNOWDebeziumMonitor AppStdout "C:\cynow\logs\monitor_stdout.log"
nssm set CYNOWDebeziumMonitor AppStderr "C:\cynow\logs\monitor_stderr.log"
nssm set CYNOWDebeziumMonitor Start SERVICE_AUTO_START
nssm set CYNOWDebeziumMonitor Description "CYNOW Debezium 상태 모니터링 및 자동 복구"
nssm start CYNOWDebeziumMonitor
```

---

### 5단계: 확인 (5분)

#### 5-1. 작업 스케줄러 확인
```powershell
# 등록된 작업 목록
schtasks /Query /FO LIST | Select-String "CYNOW"

# 특정 작업 상세 정보
schtasks /Query /TN "CYNOW - Debezium Pause for Backup" /FO LIST /V
```

#### 5-2. 수동 실행 테스트
```cmd
# 일시 중지 작업 실행
schtasks /Run /TN "CYNOW - Debezium Pause for Backup"

# 5초 대기
timeout /t 5

# 상태 확인
curl http://localhost:8083/connectors/fcms-oracle-connector/status

# 재개 작업 실행
schtasks /Run /TN "CYNOW - Debezium Resume after Backup"

# 10초 대기
timeout /t 10

# 상태 확인
curl http://localhost:8083/connectors/fcms-oracle-connector/status
```

#### 5-3. 로그 확인
```powershell
# 작업 스케줄러 로그
Get-Content C:\cynow\logs\debezium_pause_resume_*.log -Tail 20

# 모니터링 로그 (서비스 실행 시)
Get-Content C:\cynow\logs\debezium_monitor_*.log -Tail 20

# CDC 지연 확인 결과
python manage.py check_cdc_lag
```

---

## 🎯 예상 결과

### 정상 동작 시

**새벽 1:50**
```
[2025-12-19 01:50:00] [INFO] Debezium Connector 일시 중지 시작
[2025-12-19 01:50:01] [INFO] Connector 상태: RUNNING
[2025-12-19 01:50:02] [INFO] ✓ Connector 일시 중지 성공!
```

**새벽 2:30**
```
[2025-12-19 02:30:00] [INFO] Debezium Connector 재개 시작
[2025-12-19 02:30:01] [INFO] Connector 상태: PAUSED
[2025-12-19 02:30:12] [INFO] ✓ Connector 재개 성공!
[2025-12-19 02:30:12] [INFO] 실행 중인 Tasks: 1/1
```

**모니터링 서비스** (1분마다)
```
[2025-12-19 02:35:00] [INFO] Connector: RUNNING | Tasks: 1/1 (실패: 0)
[2025-12-19 02:36:00] [INFO] Connector: RUNNING | Tasks: 1/1 (실패: 0)
```

---

## ⚠️ 문제 해결

### 문제 1: "스크립트 실행 금지" 오류

**증상:**
```
.\pause_debezium_for_backup.ps1 : 이 시스템에서 스크립트를 실행할 수 없으므로...
```

**해결:**
```powershell
# 현재 정책 확인
Get-ExecutionPolicy

# 정책 변경 (현재 사용자만)
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

# 또는 한 번만 우회
powershell -ExecutionPolicy Bypass -File .\pause_debezium_for_backup.ps1 pause
```

---

### 문제 2: Kafka Connect 연결 안됨

**증상:**
```
[ERROR] 상태 조회 실패: Unable to connect to the remote server
```

**해결:**
```powershell
# Kafka Connect 서비스 확인
Get-Service | Where-Object { $_.Name -like "*kafka*" }

# 포트 확인
netstat -ano | findstr :8083

# URL 확인
curl http://localhost:8083/

# URL이 다르면 스크립트 수정
# $KAFKA_CONNECT_URL = "http://다른주소:포트"
```

---

### 문제 3: Connector 이름 불일치

**증상:**
```
[ERROR] 상태 조회 실패: Connector fcms-oracle-connector not found
```

**해결:**
```powershell
# 실제 Connector 이름 확인
curl http://localhost:8083/connectors

# 스크립트에서 수정
# pause_debezium_for_backup.ps1 3번째 줄:
# $CONNECTOR_NAME = "실제_커넥터_이름"
```

---

### 문제 4: 작업 스케줄러 실행 안됨

**증상:**
- 작업이 예정된 시간에 실행되지 않음
- "마지막 실행 결과"가 0x0이 아님

**해결:**
```powershell
# 작업 이력 확인
schtasks /Query /TN "CYNOW - Debezium Pause for Backup" /FO LIST /V

# 이벤트 뷰어 확인
eventvwr.msc
# Windows 로그 → 응용 프로그램 → "Task Scheduler" 필터

# 수동 실행으로 오류 확인
schtasks /Run /TN "CYNOW - Debezium Pause for Backup"
```

---

## 📋 체크리스트

### 배포 완료 체크리스트

- [ ] Connector 이름 확인 완료
- [ ] 스크립트 테스트 성공 (pause/resume)
- [ ] 작업 스케줄러 3개 등록 완료
  - [ ] Debezium Pause (01:50)
  - [ ] Debezium Resume (02:30)
  - [ ] CDC Lag Monitor (10분마다)
- [ ] 모니터링 서비스 시작 (선택)
- [ ] 로그 파일 정상 생성 확인
- [ ] 수동 실행 테스트 성공

### 1주 후 점검 체크리스트

- [ ] 새벽 2시 장애 발생 여부 확인
- [ ] 로그 분석 (pause_resume_*.log)
- [ ] 모니터링 로그 분석 (monitor_*.log)
- [ ] CDC 지연 현황 확인
- [ ] 자동 재시작 동작 확인

---

## 📞 추가 도움말

### 전체 문서
- 상세 계획서: `docs/CDC_BACKUP_TIME_RECOVERY_PLAN.md`
- Debezium 설정: `docs/DEBEZIUM_FIX.md`
- 배포 가이드: `deploy/DEPLOY_CHECKLIST.md`

### 로그 위치
```
C:\cynow\logs\
  ├─ debezium_pause_resume_YYYYMM.log  # 일시중지/재개 로그
  ├─ debezium_monitor_YYYYMM.log       # 모니터링 로그
  ├─ monitor_stdout.log                # 모니터링 서비스 출력
  └─ monitor_stderr.log                # 모니터링 서비스 오류
```

### 유용한 명령어
```powershell
# Connector 상태 확인
Invoke-RestMethod http://localhost:8083/connectors/fcms-oracle-connector/status | ConvertTo-Json -Depth 5

# Connector 재시작
Invoke-RestMethod -Method Post http://localhost:8083/connectors/fcms-oracle-connector/restart

# 로그 실시간 모니터링
Get-Content C:\cynow\logs\debezium_monitor_*.log -Wait -Tail 10

# 작업 스케줄러 모든 CYNOW 작업 확인
Get-ScheduledTask | Where-Object { $_.TaskName -like "CYNOW*" } | Format-Table TaskName, State, LastRunTime, NextRunTime
```

---

**작성일**: 2025-12-19  
**소요 시간**: 30분  
**난이도**: ⭐⭐☆☆☆ (중하)  

---

✅ **이제 새벽 2시 Oracle 백업 시간에도 CDC가 안전합니다!** 🎉















