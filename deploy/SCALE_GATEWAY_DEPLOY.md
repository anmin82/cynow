# Scale Gateway API 배포 가이드

**CYNOW v1.3.0 - 저울 TCP 연동 시스템**

---

## 📋 개요

Scale Gateway API는 저울(FG-150KAL)로부터 TCP 연결을 통해 실시간 무게 데이터를 수신하고, 출하/회수 시스템에 통합하는 기능입니다.

---

## 🔧 시스템 요구사항

### 하드웨어
- **저울 장비**: FG-150KAL (TCP 통신 지원)
- **네트워크**: 서버 ↔ 저울 간 TCP/IP 통신 가능

### 소프트웨어
- Python 3.10+
- PostgreSQL 12+
- CYNOW v1.3.0 이상

### 네트워크
- **포트 4001**: 저울 TCP 리스너 포트 (방화벽 허용 필요)
- 저울 장비 IP → 서버 IP:4001 접속 가능해야 함

---

## 🚀 배포 절차

### 1단계: 코드 업데이트

```bash
# CYNOW 서버 접속
ssh cynow@10.78.30.98

# 프로젝트 디렉토리로 이동
cd /opt/cynow/cynow

# 백업 (안전을 위해)
cp -r . ../cynow-backup-$(date +%Y%m%d)

# v1.3.0 코드 배포 (rsync, scp, git 등)
# 예시: rsync -avz --exclude 'venv' --exclude '.env' /path/to/cynow-v1.3.0/ /opt/cynow/cynow/
```

### 2단계: 의존성 업데이트

```bash
# 가상환경 활성화
source venv/bin/activate

# requirements.txt 확인 (신규 패키지 없음)
pip install -r requirements.txt
```

### 3단계: 환경변수 설정

```bash
# .env 파일 편집
nano .env
```

**.env 파일에 추가**:

```env
# -----------------------------------------------------------------------------
# Scale Gateway API (저울 TCP 연동)
# -----------------------------------------------------------------------------
# 저울 TCP 리스너 설정
SCALE_GATEWAY_LISTEN_HOST=0.0.0.0
SCALE_GATEWAY_LISTEN_PORT=4001
SCALE_GATEWAY_IDLE_TIMEOUT_SEC=10
```

### 4단계: 데이터베이스 마이그레이션

```bash
# devices 앱 마이그레이션 적용
python manage.py migrate devices

# 마이그레이션 확인
python manage.py showmigrations devices
```

예상 출력:
```
devices
 [X] 0001_initial
```

### 5단계: Scale Gateway 서비스 설치

```bash
# systemd 서비스 파일 복사
exit  # cynow 사용자에서 나가기
sudo cp /opt/cynow/cynow/deploy/cynow-scale-gateway.service /etc/systemd/system/

# 서비스 파일 확인
cat /etc/systemd/system/cynow-scale-gateway.service

# systemd 리로드
sudo systemctl daemon-reload

# 서비스 활성화 (부팅 시 자동 시작)
sudo systemctl enable cynow-scale-gateway

# 서비스 시작
sudo systemctl start cynow-scale-gateway

# 상태 확인
sudo systemctl status cynow-scale-gateway
```

예상 출력:
```
● cynow-scale-gateway.service - CYNOW Scale Gateway API - TCP Listener
   Loaded: loaded (/etc/systemd/system/cynow-scale-gateway.service; enabled)
   Active: active (running) since ...
```

### 6단계: 로그 확인

```bash
# 리스너 로그 확인 (실시간)
sudo journalctl -u cynow-scale-gateway -f
```

예상 로그:
```
[Scale Gateway] 리스너 시작: 0.0.0.0:4001
[Scale Gateway] 포트 4001에서 연결 대기 중...
```

### 7단계: 방화벽 설정

```bash
# Ubuntu UFW 사용 시
sudo ufw allow from <저울_장비_IP> to any port 4001 proto tcp

# 예시: 저울 IP가 10.78.30.200인 경우
sudo ufw allow from 10.78.30.200 to any port 4001 proto tcp

# 방화벽 상태 확인
sudo ufw status
```

### 8단계: Django 웹 서비스 재시작

```bash
# CYNOW 웹 애플리케이션 재시작 (API 엔드포인트 활성화)
sudo systemctl restart cynow

# 정적 파일 재수집 (필요시)
sudo su - cynow
cd /opt/cynow/cynow
source venv/bin/activate
python manage.py collectstatic --noinput
exit

# NGINX 재로드 (설정 변경 없으면 불필요)
sudo systemctl reload nginx
```

---

## 🧪 테스트

### 1. 서비스 상태 확인

```bash
# Scale Gateway 서비스
sudo systemctl status cynow-scale-gateway

# 포트 리스닝 확인
sudo netstat -tlnp | grep 4001
# 또는
sudo ss -tlnp | grep 4001
```

예상 출력:
```
tcp  0  0  0.0.0.0:4001  0.0.0.0:*  LISTEN  12345/python
```

### 2. API 엔드포인트 테스트

```bash
# 최신값 조회 (데이터 없으면 404)
curl http://localhost:8000/api/scale-gateway/latest/

# 예상 응답 (데이터 없음):
# {"ok": false, "error": "no_data", "message": "저울 데이터가 없습니다"}
```

### 3. 저울 연결 테스트 (시뮬레이터)

**서버에서 직접 테스트**:

```bash
# 터미널 1: 로그 모니터링
sudo journalctl -u cynow-scale-gateway -f

# 터미널 2: 데이터 전송
echo "ST , +000053.26 _kg" | nc localhost 4001
```

**리스너 로그 확인**:
```
[Scale Gateway] 연결 수락: ('127.0.0.1', 54321)
[Scale Gateway] ST 업데이트: 53.26 kg
[Scale Gateway] 연결 종료: ('127.0.0.1', 54321)
```

**API 조회**:
```bash
curl http://localhost:8000/api/scale-gateway/latest/
```

예상 응답:
```json
{
  "ok": true,
  "scale_id": "default",
  "status": "ST",
  "weight": 53.26,
  "raw": "ST , +000053.26 _kg",
  "received_at": "2025-12-18T12:00:00+09:00",
  "stale": false
}
```

### 4. 커밋 API 테스트

```bash
curl -X POST http://localhost:8000/api/scale-gateway/commit/ \
  -H "Content-Type: application/json" \
  -d '{
    "cylinder_no": "TEST001",
    "event_type": "SHIP",
    "arrival_shipping_no": "AS20251218-TEST"
  }'
```

예상 응답:
```json
{
  "ok": true,
  "id": 1,
  "cylinder_no": "TEST001",
  "event_type": "SHIP",
  "gross_kg": 53.26,
  "committed_at": "2025-12-18T12:01:00+09:00"
}
```

### 5. DB 확인

```bash
sudo su - cynow
cd /opt/cynow/cynow
source venv/bin/activate
python manage.py shell
```

```python
from devices.models import ScaleWeightLog

# 전체 로그 조회
logs = ScaleWeightLog.objects.all()
print(f"총 {logs.count()}개 로그")

for log in logs[:5]:
    print(f"{log.id}: {log.cylinder_no} - {log.event_type} - {log.gross_kg}kg")

# 최근 로그
latest = ScaleWeightLog.objects.first()
if latest:
    print(f"\n최근 로그:")
    print(f"  용기: {latest.cylinder_no}")
    print(f"  무게: {latest.gross_kg}kg")
    print(f"  시각: {latest.committed_at}")
```

---

## 🔌 저울 장비 연결 설정

### FG-150KAL 설정

저울 장비의 네트워크 설정:

1. **IP 설정**: 고정 IP 할당 (예: 10.78.30.200)
2. **서버 IP**: CYNOW 서버 IP (10.78.30.98)
3. **포트**: 4001
4. **프로토콜**: TCP Client
5. **데이터 포맷**: 기본 포맷 (예: `ST , +000053.26 _kg\r\n`)

### 연결 확인

저울 장비 측에서:
- 서버 IP:4001로 TCP 연결 시도
- 연결 성공 시 저울 데이터 전송 시작

CYNOW 서버 측에서:
```bash
# 연결 확인 (로그)
sudo journalctl -u cynow-scale-gateway -n 20
```

예상 로그:
```
[Scale Gateway] 연결 수락: ('10.78.30.200', 54321)
[Scale Gateway] ST 업데이트: 53.26 kg
```

---

## 📊 모니터링

### 로그 확인

```bash
# 실시간 로그
sudo journalctl -u cynow-scale-gateway -f

# 최근 100줄
sudo journalctl -u cynow-scale-gateway -n 100

# 특정 시간대
sudo journalctl -u cynow-scale-gateway --since "2025-12-18 10:00:00"

# 오류만 필터링
sudo journalctl -u cynow-scale-gateway -p err
```

### 서비스 관리

```bash
# 상태 확인
sudo systemctl status cynow-scale-gateway

# 재시작
sudo systemctl restart cynow-scale-gateway

# 중지
sudo systemctl stop cynow-scale-gateway

# 시작
sudo systemctl start cynow-scale-gateway

# 로그 레벨 변경 (DEBUG)
# .env 파일에서 Django 로그 레벨 조정
```

### 성능 모니터링

```bash
# 프로세스 확인
ps aux | grep scale_gateway

# 포트 연결 상태
sudo netstat -anp | grep 4001

# 메모리 사용량
sudo systemctl status cynow-scale-gateway | grep Memory
```

---

## 🐛 문제 해결

### 문제 1: 서비스 시작 실패

**증상**: `systemctl start cynow-scale-gateway` 실패

**원인**:
- Python 가상환경 경로 오류
- .env 파일 없음
- 포트 4001이 이미 사용 중

**해결**:
```bash
# 로그 확인
sudo journalctl -u cynow-scale-gateway -n 50

# 포트 사용 확인
sudo lsof -i :4001

# 수동 실행 테스트
sudo su - cynow
cd /opt/cynow/cynow
source venv/bin/activate
python manage.py scale_gateway_listener
```

### 문제 2: 저울 연결 안됨

**증상**: 저울에서 연결 시도하지만 서버에서 연결 수락 로그 없음

**원인**:
- 방화벽 차단
- 네트워크 라우팅 문제
- 저울 IP 설정 오류

**해결**:
```bash
# 방화벽 확인
sudo ufw status | grep 4001

# 포트 리스닝 확인
sudo netstat -tlnp | grep 4001

# 저울 IP에서 접속 테스트 (다른 장비에서)
telnet 10.78.30.98 4001

# 방화벽 규칙 추가
sudo ufw allow from <저울_IP> to any port 4001 proto tcp
```

### 문제 3: API 응답 없음

**증상**: `/api/scale-gateway/latest/` 접속 시 404 또는 500

**원인**:
- CYNOW 웹 서비스(Gunicorn) 재시작 안됨
- URL 라우팅 오류
- devices 앱 미등록

**해결**:
```bash
# Gunicorn 재시작
sudo systemctl restart cynow

# URL 확인
sudo su - cynow
cd /opt/cynow/cynow
source venv/bin/activate
python manage.py show_urls | grep scale

# settings.py 확인 (INSTALLED_APPS)
grep -A 20 "INSTALLED_APPS" config/settings.py | grep devices
```

### 문제 4: 데이터 수신되지만 캐시 없음

**증상**: 리스너 로그에 데이터 수신 보이지만 API에서 no_data

**원인**:
- US 또는 OL 상태 (ST만 캐시)
- 파싱 실패

**해결**:
```bash
# 로그 확인 (DEBUG 레벨)
sudo journalctl -u cynow-scale-gateway -n 100 | grep -E "(ST|US|OL|파싱)"

# 저울 데이터 포맷 확인
# "ST , +000053.26 _kg" 형식이어야 함
```

---

## 🔐 보안 고려사항

### 프로덕션 권장사항

1. **API 인증**:
   - 현재: POC로 인증 없음
   - 권장: Token 기반 인증, IP 화이트리스트

2. **방화벽**:
   - 포트 4001: 저울 장비 IP만 허용
   - API 엔드포인트: 내부망만 접근

3. **HTTPS**:
   - 웹 API는 HTTPS 사용 (NGINX SSL)

4. **로그 관리**:
   - 저울 데이터 로그 보관 정책
   - 개인정보 포함 여부 확인

---

## 📈 확장 계획

### 다중 저울 지원

현재 단일 저울 지원, 향후 확장:

```bash
# 여러 저울 실행 예시 (포트별)
python manage.py scale_gateway_listener --port 4001 --scale-id scale-01
python manage.py scale_gateway_listener --port 4002 --scale-id scale-02
```

### 웹소켓 실시간 푸시

저울 데이터를 웹 대시보드에 실시간 표시

### 데이터 분석

- 용기별 무게 추이
- 이상치 탐지
- 예측 유지보수

---

## ✅ 배포 완료 체크리스트

- [ ] v1.3.0 코드 배포
- [ ] .env에 Scale Gateway 설정 추가
- [ ] devices 앱 마이그레이션 완료
- [ ] cynow-scale-gateway.service 설치
- [ ] 서비스 자동 시작 활성화
- [ ] 방화벽에서 포트 4001 허용
- [ ] 서비스 실행 확인 (`systemctl status`)
- [ ] 포트 리스닝 확인 (`netstat -tlnp`)
- [ ] API 엔드포인트 테스트
- [ ] 저울 연결 테스트 (시뮬레이터)
- [ ] DB에 로그 저장 확인
- [ ] 운영팀에 사용법 교육

---

## 📞 지원

문제 발생 시:
1. 로그 확인: `sudo journalctl -u cynow-scale-gateway -n 100`
2. 서비스 상태: `sudo systemctl status cynow-scale-gateway`
3. 이 문서의 "문제 해결" 섹션 참고

---

**Scale Gateway API v1.0**  
**CYNOW v1.3.0**  
**배포일**: 2025-12-18



















