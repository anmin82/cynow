# 🐧 Ubuntu 서버용 Debezium 지능형 복구 가이드

## 개요

Ubuntu 서버에서 Debezium CDC가 Oracle 백업 시간에 죽는 문제를 해결합니다.

### 핵심 전략
```
Oracle 장애 발생
  ↓
즉시 Connector 일시 중지 (PAUSED)
  ↓
1분마다 Oracle 연결 테스트
  ↓
Oracle 정상 복구 확인
  ↓
Connector 재개 (RUNNING)
```

---

## 🚀 빠른 시작 (10분)

### 1단계: 파일 업로드

```bash
# 로컬에서 서버로 파일 복사
scp C:\cynow\deploy\monitor_debezium_smart.sh user@server:/opt/cynow/deploy/
scp C:\cynow\deploy\pause_debezium_for_backup.sh user@server:/opt/cynow/deploy/

# 또는 서버에서 직접 생성 (vi 또는 nano 사용)
```

### 2단계: 실행 권한 부여

```bash
cd /opt/cynow/deploy
chmod +x monitor_debezium_smart.sh
chmod +x pause_debezium_for_backup.sh
```

### 3단계: 설정 확인

```bash
# 스크립트 편집
nano monitor_debezium_smart.sh
```

**수정할 부분:**
```bash
KAFKA_CONNECT_URL="http://localhost:8083"
CONNECTOR_NAME="oracle-fcms-cylcy-main"
ORACLE_HOST="10.78.30.18"
ORACLE_PORT="1521"
```

### 4단계: 필수 패키지 설치

```bash
# jq 설치 (JSON 파싱용)
sudo apt-get update
sudo apt-get install -y jq curl

# 설치 확인
jq --version
curl --version
```

### 5단계: 테스트 실행

```bash
# 모니터링 스크립트 테스트 (Ctrl+C로 종료)
./monitor_debezium_smart.sh
```

**예상 출력:**
```
[2025-12-19 15:00:00] [INFO] ========================================
[2025-12-19 15:00:00] [INFO] Debezium Smart Monitoring Started
[2025-12-19 15:00:00] [INFO] Connector: oracle-fcms-cylcy-main
[2025-12-19 15:00:00] [INFO] Kafka Connect: http://localhost:8083
[2025-12-19 15:00:00] [INFO] Oracle: 10.78.30.18:1521
[2025-12-19 15:00:05] [INFO] Status: RUNNING | Tasks: 1/1 (failed: 0)
[2025-12-19 15:00:05] [INFO] [OK] Operating normally
```

---

## 🔧 systemd 서비스 등록

### 서비스 파일 생성

```bash
sudo nano /etc/systemd/system/cynow-debezium-monitor.service
```

**파일 내용:**
```ini
[Unit]
Description=CYNOW Debezium Smart Monitoring Service
After=network.target kafka-connect.service
Wants=kafka-connect.service

[Service]
Type=simple
User=cynow
Group=cynow
WorkingDirectory=/opt/cynow
ExecStart=/opt/cynow/deploy/monitor_debezium_smart.sh
Restart=always
RestartSec=30
StartLimitInterval=300
StartLimitBurst=5

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cynow-debezium

[Install]
WantedBy=multi-user.target
```

### 서비스 시작

```bash
# 서비스 등록
sudo systemctl daemon-reload
sudo systemctl enable cynow-debezium-monitor.service

# 서비스 시작
sudo systemctl start cynow-debezium-monitor.service

# 서비스 상태 확인
sudo systemctl status cynow-debezium-monitor.service

# 로그 확인 (실시간)
sudo journalctl -u cynow-debezium-monitor.service -f
```

---

## ⏰ cron 작업 설정 (백업 시간 자동 중지/재개)

### crontab 편집

```bash
crontab -e
```

### 작업 추가

```cron
# Oracle 백업 전 Debezium 일시 중지 (새벽 1:50)
50 1 * * * /opt/cynow/deploy/pause_debezium_for_backup.sh pause >> /opt/cynow/logs/cron.log 2>&1

# Oracle 백업 후 Debezium 재개 (새벽 2:30)
30 2 * * * /opt/cynow/deploy/pause_debezium_for_backup.sh resume >> /opt/cynow/logs/cron.log 2>&1
```

### cron 로그 확인

```bash
# cron 로그
tail -f /opt/cynow/logs/cron.log

# pause/resume 로그
tail -f /opt/cynow/logs/debezium_pause_resume_*.log
```

---

## 📋 전체 설정 요약

### 구성 요소

1. **지능형 모니터링 서비스** (항상 실행)
   - systemd 서비스로 등록
   - 장애 감지 → 즉시 일시 중지
   - 1분마다 Oracle 연결 테스트
   - 복구 감지 → 자동 재개

2. **백업 시간 자동 중지/재개** (cron)
   - 01:50 - 자동 일시 중지
   - 02:30 - 자동 재개

### 디렉토리 구조

```
/opt/cynow/
├── deploy/
│   ├── monitor_debezium_smart.sh       # 모니터링 스크립트
│   └── pause_debezium_for_backup.sh    # 수동 중지/재개 스크립트
└── logs/
    ├── debezium_smart_monitor_YYYYMM.log
    ├── debezium_pause_resume_YYYYMM.log
    └── cron.log
```

---

## 📊 모니터링 및 로그

### 실시간 로그 확인

```bash
# systemd 서비스 로그
sudo journalctl -u cynow-debezium-monitor.service -f

# 파일 로그
tail -f /opt/cynow/logs/debezium_smart_monitor_*.log

# 시스템 로그 (알림)
tail -f /var/log/syslog | grep CYNOW-Debezium
```

### 로그 검색

```bash
# 에러만 필터링
grep ERROR /opt/cynow/logs/debezium_smart_monitor_*.log

# 알림만 필터링
grep ALERT /opt/cynow/logs/debezium_smart_monitor_*.log

# 특정 날짜
grep "2025-12-19" /opt/cynow/logs/debezium_smart_monitor_*.log
```

### Connector 상태 확인

```bash
# REST API로 직접 확인
curl -s http://localhost:8083/connectors/oracle-fcms-cylcy-main/status | jq

# 간단한 상태만
curl -s http://localhost:8083/connectors/oracle-fcms-cylcy-main/status | jq '.connector.state'
```

---

## 🔧 트러블슈팅

### 문제 1: jq 명령어 없음

**증상:**
```
./monitor_debezium_smart.sh: line 45: jq: command not found
```

**해결:**
```bash
sudo apt-get install -y jq
```

---

### 문제 2: 스크립트 실행 권한 없음

**증상:**
```
bash: ./monitor_debezium_smart.sh: Permission denied
```

**해결:**
```bash
chmod +x /opt/cynow/deploy/monitor_debezium_smart.sh
```

---

### 문제 3: Oracle 연결 테스트 실패

**증상:**
```
[FAIL] Oracle listener not responding (timeout)
```

**확인:**
```bash
# 네트워크 연결 테스트
nc -zv 10.78.30.18 1521

# 또는
telnet 10.78.30.18 1521

# 방화벽 확인
sudo iptables -L -n | grep 1521
```

**해결:**
```bash
# 방화벽 규칙 추가 (필요시)
sudo ufw allow from 10.78.30.18 to any port 1521
```

---

### 문제 4: systemd 서비스 시작 실패

**확인:**
```bash
# 서비스 상태 상세 확인
sudo systemctl status cynow-debezium-monitor.service

# 로그 확인
sudo journalctl -u cynow-debezium-monitor.service -n 50 --no-pager
```

**일반적인 원인:**
1. 스크립트 경로 잘못됨
2. 실행 권한 없음
3. 사용자 계정 문제 (User= 설정)

---

### 문제 5: cron 작업이 실행 안됨

**확인:**
```bash
# cron 서비스 상태
sudo systemctl status cron

# cron 로그
grep CRON /var/log/syslog

# 스크립트 수동 실행으로 테스트
/opt/cynow/deploy/pause_debezium_for_backup.sh pause
```

---

## 🎯 수동 작업

### Connector 수동 제어

```bash
# 일시 중지
/opt/cynow/deploy/pause_debezium_for_backup.sh pause

# 재개
/opt/cynow/deploy/pause_debezium_for_backup.sh resume

# 또는 curl 직접 사용
curl -X PUT http://localhost:8083/connectors/oracle-fcms-cylcy-main/pause
curl -X PUT http://localhost:8083/connectors/oracle-fcms-cylcy-main/resume

# 재시작
curl -X POST http://localhost:8083/connectors/oracle-fcms-cylcy-main/restart
```

### 서비스 제어

```bash
# 모니터링 서비스 시작
sudo systemctl start cynow-debezium-monitor.service

# 모니터링 서비스 중지
sudo systemctl stop cynow-debezium-monitor.service

# 모니터링 서비스 재시작
sudo systemctl restart cynow-debezium-monitor.service

# 부팅 시 자동 시작 활성화
sudo systemctl enable cynow-debezium-monitor.service

# 부팅 시 자동 시작 비활성화
sudo systemctl disable cynow-debezium-monitor.service
```

---

## 📧 알림 설정 (선택사항)

### 이메일 알림

스크립트의 `send_alert` 함수에 추가:

```bash
send_alert() {
    local message="$1"
    local level="${2:-ERROR}"
    
    write_log "ALERT: $message" "$level"
    
    # 이메일 전송
    echo "$message" | mail -s "CYNOW Debezium Alert: $level" admin@example.com
}
```

**mail 명령어 설치:**
```bash
sudo apt-get install -y mailutils
```

### Slack 알림

```bash
send_alert() {
    local message="$1"
    local level="${2:-ERROR}"
    
    write_log "ALERT: $message" "$level"
    
    # Slack webhook
    local slack_webhook="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"🚨 CYNOW Alert [$level]: $message\"}" \
        "$slack_webhook"
}
```

---

## 📝 체크리스트

### 설치 완료 체크리스트

- [ ] jq, curl 설치 확인
- [ ] 스크립트 파일 업로드
- [ ] 스크립트 실행 권한 부여
- [ ] 설정 값 수정 (Connector 이름, Oracle IP/포트)
- [ ] 수동 테스트 성공
- [ ] systemd 서비스 등록
- [ ] systemd 서비스 시작 및 확인
- [ ] cron 작업 등록 (백업 시간)
- [ ] 로그 파일 생성 확인

### 1주 후 점검 체크리스트

- [ ] 새벽 2시 장애 0건 달성
- [ ] 자동 일시 중지/재개 정상 동작
- [ ] 모니터링 서비스 정상 실행 중
- [ ] 로그 파일 크기 적절
- [ ] Oracle 연결 테스트 정상

---

## 🔍 유용한 명령어 모음

```bash
# === 서비스 관리 ===
sudo systemctl status cynow-debezium-monitor.service
sudo systemctl restart cynow-debezium-monitor.service
sudo journalctl -u cynow-debezium-monitor.service -f

# === Connector 상태 ===
curl -s http://localhost:8083/connectors/oracle-fcms-cylcy-main/status | jq
curl -s http://localhost:8083/connectors | jq

# === 로그 확인 ===
tail -f /opt/cynow/logs/debezium_smart_monitor_*.log
tail -f /opt/cynow/logs/debezium_pause_resume_*.log
grep ERROR /opt/cynow/logs/debezium_smart_monitor_*.log | tail -20

# === Oracle 연결 테스트 ===
nc -zv 10.78.30.18 1521
timeout 5 bash -c "echo > /dev/tcp/10.78.30.18/1521" && echo "OK" || echo "FAIL"

# === Kafka Connect ===
sudo systemctl status kafka-connect
sudo journalctl -u kafka-connect -f

# === 디스크 사용량 ===
du -sh /opt/cynow/logs/*
df -h
```

---

## 📚 추가 참고 자료

- `docs/CDC_BACKUP_TIME_RECOVERY_PLAN.md` - 전체 복구 계획서
- `docs/CDC_SMART_RECOVERY_GUIDE.md` - Windows 가이드 (참고용)
- `docs/DEBEZIUM_FIX.md` - Debezium 트러블슈팅

---

**작성일**: 2025-12-19  
**서버 환경**: Ubuntu Server  
**버전**: 1.0













