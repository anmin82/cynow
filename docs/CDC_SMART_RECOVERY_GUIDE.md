# 🧠 Debezium 지능형 복구 가이드

## 개요

새벽 백업 시간에 Oracle 연결이 끊어질 때, **무분별한 재시도 대신 지능적으로 대응**하는 방식입니다.

### 기존 방식의 문제점 ❌
```
Oracle 장애 발생
  ↓
Debezium 연결 실패 → 재시도 → 실패 → 재시도 → 실패 → ...
  ↓
Connector FAILED
  ↓
무한 재시도로 리소스 낭비
```

### 지능형 복구 방식 ✅
```
Oracle 장애 발생
  ↓
Debezium 연결 실패 감지
  ↓
즉시 Connector 일시 중지 (PAUSED)
  ↓
1분마다 Oracle 연결 테스트
  ↓
Oracle 정상 복구 확인
  ↓
Connector 재개 (RUNNING)
  ↓
정상 동작 재개
```

---

## 핵심 기능

### 1. 즉시 일시 중지
- Connector FAILED 감지 시 **즉시 PAUSED 상태로 전환**
- Task 실패 감지 시도 동일하게 처리
- 무분별한 재시도 방지

### 2. Oracle 연결 테스트
- TCP 소켓 연결로 빠른 확인 (5초 타임아웃)
- 1분마다 주기적 확인
- Oracle Listener 포트(1521) 응답 체크

### 3. 자동 복구
- Oracle 정상 복구 감지 시
- Connector 자동 재개
- 정상 동작 재개

### 4. 타임아웃 보호
- 최대 대기 시간: 30분
- 30분 후에도 복구 안되면 알림
- 수동 개입 필요 메시지

---

## 설치 방법

### 1단계: 스크립트 설정 확인

`deploy/monitor_debezium_smart.ps1` 파일을 열어 다음 항목 확인:

```powershell
# Kafka Connect 설정
$KAFKA_CONNECT_URL = "http://localhost:8083"
$CONNECTOR_NAME = "fcms-oracle-connector"

# Oracle 연결 테스트 설정 (실제 환경에 맞게 수정!)
$ORACLE_HOST = "10.78.30.98"  # Oracle 서버 IP
$ORACLE_PORT = "1521"          # Oracle Listener 포트

# 확인 간격
$CHECK_INTERVAL = 60           # 정상 상태: 60초마다 확인
$RECOVERY_CHECK_INTERVAL = 60  # 복구 대기: 60초마다 Oracle 테스트
```

---

### 2단계: 테스트 실행

```powershell
# 스크립트 위치로 이동
cd C:\cynow\deploy

# 테스트 실행 (Ctrl+C로 중단 가능)
.\monitor_debezium_smart.ps1
```

**예상 출력 (정상 상태):**
```
[2025-12-19 10:00:00] [INFO] Debezium 지능형 모니터링 시작
[2025-12-19 10:00:00] [INFO] Connector: fcms-oracle-connector
[2025-12-19 10:00:05] [INFO] 상태: RUNNING | Tasks: 1/1 (실패: 0)
[2025-12-19 10:00:05] [INFO] ✓ 정상 동작 중
[2025-12-19 10:01:05] [INFO] 상태: RUNNING | Tasks: 1/1 (실패: 0)
[2025-12-19 10:01:05] [INFO] ✓ 정상 동작 중
```

**장애 시나리오 테스트:**
```powershell
# 1. 다른 PowerShell 창에서 Connector를 수동으로 실패 상태로 만들기
# (테스트 목적)

# 2. 모니터링 스크립트가 감지하고 PAUSED로 전환하는지 확인

# 3. Oracle 연결 테스트가 1분마다 실행되는지 확인

# 4. Connector를 수동으로 재개하여 정상 복구 확인
```

---

### 3단계: Windows 서비스로 등록

#### 옵션 A: NSSM 사용 (권장)

```cmd
# NSSM 설치 (Chocolatey 사용)
choco install nssm

# 서비스 등록
nssm install CYNOWDebeziumSmartMonitor "powershell.exe" "-ExecutionPolicy Bypass -NoProfile -File C:\cynow\deploy\monitor_debezium_smart.ps1"
nssm set CYNOWDebeziumSmartMonitor AppDirectory "C:\cynow"
nssm set CYNOWDebeziumSmartMonitor AppStdout "C:\cynow\logs\smart_monitor_stdout.log"
nssm set CYNOWDebeziumSmartMonitor AppStderr "C:\cynow\logs\smart_monitor_stderr.log"
nssm set CYNOWDebeziumSmartMonitor Start SERVICE_AUTO_START
nssm set CYNOWDebeziumSmartMonitor Description "CYNOW Debezium 지능형 모니터링 및 복구"

# 서비스 시작
nssm start CYNOWDebeziumSmartMonitor

# 서비스 상태 확인
nssm status CYNOWDebeziumSmartMonitor
```

#### 옵션 B: Windows 작업 스케줄러 (부팅 시 실행)

```powershell
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File C:\cynow\deploy\monitor_debezium_smart.ps1"

$Trigger = New-ScheduledTaskTrigger -AtStartup

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)  # 무제한

$Principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName "CYNOW - Debezium Smart Monitor" `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Debezium 지능형 모니터링 (부팅 시 자동 시작)"
```

---

## 동작 시나리오

### 시나리오 1: 새벽 백업 시간

**01:50 - 백업 시작 전**
```
[01:50:00] [INFO] 상태: RUNNING | Tasks: 1/1 (실패: 0)
[01:50:00] [INFO] ✓ 정상 동작 중
```

**02:00 - Oracle 백업 시작, 리소스 부족**
```
[02:00:05] [ERROR] ⚠️ 장애 감지!
[02:00:05] [ERROR] Connector: FAILED | 실패 Tasks: 1
[02:00:06] [WARN] Connector 일시 중지 요청 전송...
[02:00:11] [INFO] ✓ Connector 일시 중지 완료. 복구 대기 모드로 전환합니다.
[02:00:11] [INFO] ========================================
[02:00:11] [INFO] 복구 대기 모드 진입
[02:00:11] [INFO] Oracle 정상 복구를 60초마다 확인합니다.
[02:00:11] [INFO] ========================================
```

**02:01 ~ 02:25 - 복구 대기 중**
```
[02:01:11] [INFO] [1] Oracle 연결 상태 확인 중... (경과: 1분)
[02:01:11] [INFO] Oracle 연결 테스트 중... (10.78.30.98:1521)
[02:01:16] [WARN] ✗ Oracle 리스너 응답 없음 (타임아웃)
[02:01:16] [WARN] Oracle 아직 복구 안됨. 60초 후 재확인...

[02:02:16] [INFO] [2] Oracle 연결 상태 확인 중... (경과: 2분)
[02:02:16] [WARN] ✗ Oracle 리스너 응답 없음 (타임아웃)
...
```

**02:25 - Oracle 백업 완료, 정상 복구**
```
[02:25:11] [INFO] [25] Oracle 연결 상태 확인 중... (경과: 25분)
[02:25:11] [INFO] Oracle 연결 테스트 중... (10.78.30.98:1521)
[02:25:12] [INFO] ✓ Oracle 리스너 응답 정상
[02:25:12] [INFO] ✓ Oracle이 정상 복구되었습니다!
[02:25:12] [INFO] 복구 대기 모드: PAUSED 상태 유지 중
[02:25:12] [INFO] ✓ Oracle 정상 복구 감지! Connector 재개 시도...
[02:25:12] [INFO] Connector 재개 요청 전송...
[02:25:23] [INFO] ✓ Connector 재개 완료 (Tasks: 1/1)
[02:25:23] [INFO] ✓ Connector 정상 재개 완료!
[02:25:23] [INFO] 🚨 알림: Debezium Connector가 정상 복구되어 재개되었습니다.
```

**02:26 - 정상 동작 재개**
```
[02:26:23] [INFO] 상태: RUNNING | Tasks: 1/1 (실패: 0)
[02:26:23] [INFO] ✓ 정상 동작 중
```

---

### 시나리오 2: 장기 장애 (30분 초과)

**복구 실패 시:**
```
[02:30:11] [ERROR] 최대 대기 시간 (30분) 초과. 복구 대기 종료.
[02:30:11] [ERROR] 🚨 알림: Oracle이 30분 동안 복구되지 않았습니다. 수동 확인 필요.
[02:30:11] [INFO] Connector는 PAUSED 상태로 유지됩니다.
```

**수동 조치:**
```powershell
# 1. Oracle 상태 확인
# DBA팀 연락 또는 직접 확인

# 2. Oracle 정상 확인 후 수동 재개
Invoke-RestMethod -Method Put http://localhost:8083/connectors/fcms-oracle-connector/resume

# 또는 스크립트 사용
C:\cynow\deploy\pause_debezium_for_backup.ps1 resume
```

---

## 모니터링 및 로그

### 로그 파일
```
C:\cynow\logs\
  ├─ debezium_smart_monitor_YYYYMM.log  # 주 로그 파일
  ├─ smart_monitor_stdout.log           # 서비스 표준 출력
  └─ smart_monitor_stderr.log           # 서비스 오류 출력
```

### 로그 확인
```powershell
# 실시간 모니터링
Get-Content C:\cynow\logs\debezium_smart_monitor_*.log -Wait -Tail 20

# 오늘 로그 전체 보기
Get-Content C:\cynow\logs\debezium_smart_monitor_*.log

# 에러만 필터링
Get-Content C:\cynow\logs\debezium_smart_monitor_*.log | Select-String "ERROR"

# 알림 메시지만 필터링
Get-Content C:\cynow\logs\debezium_smart_monitor_*.log | Select-String "🚨"
```

### Windows 이벤트 로그
```
1. eventvwr.msc 실행
2. Windows 로그 → 응용 프로그램
3. 원본: CYNOW 필터
```

---

## 장점 및 효과

### 기존 방식 대비 개선점

| 항목 | 기존 방식 | 지능형 복구 |
|------|----------|------------|
| 재시도 횟수 | 무제한 (리소스 낭비) | 0회 (즉시 중지) |
| 복구 확인 | 계속 실패 | 1분마다 체크 |
| 리소스 사용 | 높음 | 낮음 |
| 로그 양 | 엄청 많음 | 적절함 |
| 복구 시간 | 불확실 | Oracle 복구 즉시 |
| 안정성 | 낮음 | 높음 |

### 예상 효과

1. **리소스 효율성**
   - Kafka Connect Worker CPU/메모리 사용량 감소
   - Oracle 부하 감소 (무의미한 연결 시도 없음)

2. **안정성 향상**
   - 백업 시간에도 파이프라인 안정성 유지
   - Connector 상태 예측 가능

3. **운영 편의성**
   - 자동 복구로 야간 대응 불필요
   - 명확한 로그로 문제 파악 용이

4. **데이터 정합성**
   - CDC 오프셋 보존
   - 복구 후 누락 데이터 없음

---

## 트러블슈팅

### 문제 1: Oracle 연결 테스트 실패

**증상:**
```
[ERROR] ✗ Oracle 연결 실패: Unable to connect
```

**해결:**
1. Oracle IP/포트 확인
   ```powershell
   Test-NetConnection -ComputerName 10.78.30.98 -Port 1521
   ```

2. 방화벽 확인
   ```cmd
   netsh advfirewall firewall show rule name=all | findstr 1521
   ```

3. 스크립트 설정 수정
   ```powershell
   $ORACLE_HOST = "실제_IP"
   $ORACLE_PORT = "실제_포트"
   ```

---

### 문제 2: Connector가 PAUSED에서 재개 안됨

**증상:**
```
[INFO] Oracle 정상 복구 감지
[ERROR] Connector 재개 실패
```

**해결:**
```powershell
# 1. Connector 상태 확인
curl http://localhost:8083/connectors/fcms-oracle-connector/status

# 2. 수동 재시작
curl -X POST http://localhost:8083/connectors/fcms-oracle-connector/restart

# 3. Kafka Connect 로그 확인
# (Kafka Connect 설치 디렉토리의 로그 파일)
```

---

### 문제 3: 서비스가 자동 시작 안됨

**NSSM 서비스 확인:**
```cmd
# 서비스 상태
nssm status CYNOWDebeziumSmartMonitor

# 서비스 재시작
nssm restart CYNOWDebeziumSmartMonitor

# 로그 확인
type C:\cynow\logs\smart_monitor_stderr.log
```

**작업 스케줄러 확인:**
```powershell
Get-ScheduledTask -TaskName "CYNOW - Debezium Smart Monitor"
```

---

## FAQ

### Q1: 기존 모니터링 스크립트와 함께 사용 가능한가요?
**A:** 동시에 사용하지 마세요. 지능형 모니터링 스크립트 하나만 실행하세요.

```powershell
# 기존 서비스 중지
nssm stop CYNOWDebeziumMonitor

# 새 서비스 시작
nssm start CYNOWDebeziumSmartMonitor
```

---

### Q2: Oracle 테스트 대신 다른 방법은?
**A:** 네, `Test-OracleConnection` 함수를 수정하여:
- Kafka Connect API를 통한 커넥터 헬스체크
- PostgreSQL CDC 테이블 업데이트 시간 확인
- 커스텀 헬스체크 엔드포인트 호출

---

### Q3: 복구 대기 시간을 변경하려면?
**A:** 스크립트에서 두 가지 값 수정:

```powershell
$RECOVERY_CHECK_INTERVAL = 30  # 30초마다 체크 (더 자주)
# 또는
$RECOVERY_CHECK_INTERVAL = 120 # 2분마다 체크 (덜 자주)

# Wait-ForRecovery 호출 부분도 수정
Wait-ForRecovery -MaxWaitMinutes 60  # 최대 60분 대기
```

---

### Q4: 백업 시간대 자동 일시 중지와 함께 사용?
**A:** 네! 함께 사용하면 더 안전합니다.

**구성:**
1. **01:50** - 자동 일시 중지 (백업 시작 전)
2. **02:30** - 자동 재개 (백업 종료 후)
3. **항상** - 지능형 모니터링 실행 (예상치 못한 장애 대응)

이렇게 하면 **계획된 백업**과 **예상치 못한 장애** 모두 대응 가능합니다.

---

## 요약

### 핵심 동작
1. ⚠️ 장애 감지 → 즉시 일시 중지
2. 🔍 1분마다 Oracle 연결 테스트
3. ✅ 정상 복구 → 자동 재개
4. ⏰ 30분 초과 → 알림 + 수동 개입

### 설치 요약
```powershell
# 1. 설정 확인 (IP, 포트)
notepad C:\cynow\deploy\monitor_debezium_smart.ps1

# 2. 테스트 실행
.\monitor_debezium_smart.ps1

# 3. 서비스 등록
nssm install CYNOWDebeziumSmartMonitor ...
nssm start CYNOWDebeziumSmartMonitor

# 4. 로그 확인
Get-Content C:\cynow\logs\debezium_smart_monitor_*.log -Wait
```

---

**작성일**: 2025-12-19  
**버전**: 1.0  
**업데이트**: 지능형 복구 방식 적용













