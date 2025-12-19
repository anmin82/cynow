# CYNOW v1.3.0 배포 가이드

**Scale Gateway API 포함 - 저울 TCP 연동 신규 추가**

배포일: 2025-12-18

---

## 📦 배포 패키지

```
dist/cynow-v1.3.0.zip
```

**파일 수**: 270개  
**주요 변경사항**: Scale Gateway API 추가

---

## 🎯 이번 배포의 주요 기능

### ✨ Scale Gateway API (신규)

저울(FG-150KAL)과 TCP 연결을 통해 실시간 무게 데이터를 수신하고 출하/회수 시스템에 통합:

- **TCP 리스너**: 포트 4001에서 저울 데이터 수신
- **실시간 캐시**: 최신 안정값(ST)을 메모리에 저장
- **REST API**:
  - `GET /api/scale-gateway/latest/` - 최신 무게 조회
  - `POST /api/scale-gateway/commit/` - 출하/회수 확정
- **DB 로그**: ScaleWeightLog 테이블에 영구 저장
- **systemd 서비스**: 자동 시작/재시작 지원

---

## 📋 배포 전 체크리스트

### 필수 확인사항

- [ ] PostgreSQL 실행 중
- [ ] CYNOW v1.2.0 이상 현재 운영 중
- [ ] 서버 SSH 접속 가능
- [ ] 백업 완료

### 신규 요구사항 (Scale Gateway)

- [ ] 저울 장비 네트워크 정보 확인 (IP 주소)
- [ ] 포트 4001 사용 가능 확인
- [ ] 저울 ↔ 서버 간 네트워크 연결 확인

---

## 🚀 빠른 배포 (기존 시스템 업그레이드)

### 1단계: 패키지 전송

```bash
# 로컬에서 서버로 전송
scp cynow-v1.3.0.zip cynow@10.78.30.98:/tmp/

# 또는 rsync
rsync -avz cynow-v1.3.0.zip cynow@10.78.30.98:/tmp/
```

### 2단계: 백업 및 압축 해제

```bash
# 서버 접속
ssh cynow@10.78.30.98

# 현재 버전 백업
cd /opt/cynow
sudo cp -r cynow cynow-backup-$(date +%Y%m%d-%H%M%S)

# 압축 해제
cd /tmp
unzip cynow-v1.3.0.zip

# 파일 복사 (venv, .env, db.sqlite3 제외)
sudo rsync -av --exclude='venv' --exclude='.env' --exclude='db.sqlite3' \
  cynow-v1.3.0/ /opt/cynow/cynow/

# 소유권 변경
sudo chown -R cynow:www-data /opt/cynow/cynow
```

### 3단계: 환경변수 업데이트

```bash
cd /opt/cynow/cynow

# .env 파일 편집
nano .env
```

**.env에 추가**:

```env
# -----------------------------------------------------------------------------
# Scale Gateway API (v1.3.0 신규)
# -----------------------------------------------------------------------------
SCALE_GATEWAY_LISTEN_HOST=0.0.0.0
SCALE_GATEWAY_LISTEN_PORT=4001
SCALE_GATEWAY_IDLE_TIMEOUT_SEC=10
```

### 4단계: 데이터베이스 마이그레이션

```bash
# 가상환경 활성화
source venv/bin/activate

# devices 앱 마이그레이션
python manage.py migrate devices

# 결과 확인
python manage.py showmigrations devices
```

예상 출력:
```
devices
 [X] 0001_initial
```

### 5단계: Scale Gateway 서비스 설치

```bash
# 서비스 파일 복사
sudo cp deploy/cynow-scale-gateway.service /etc/systemd/system/

# systemd 리로드
sudo systemctl daemon-reload

# 서비스 활성화 및 시작
sudo systemctl enable cynow-scale-gateway
sudo systemctl start cynow-scale-gateway

# 상태 확인
sudo systemctl status cynow-scale-gateway
```

### 6단계: 웹 서비스 재시작

```bash
# 정적 파일 재수집
python manage.py collectstatic --noinput

# Gunicorn 재시작
sudo systemctl restart cynow
```

### 7단계: 방화벽 설정

```bash
# 저울 장비 IP에서만 포트 4001 허용
sudo ufw allow from <저울_IP> to any port 4001 proto tcp

# 예시
sudo ufw allow from 10.78.30.200 to any port 4001 proto tcp

# 확인
sudo ufw status
```

### 8단계: 배포 확인

```bash
# Scale Gateway 서비스
sudo systemctl status cynow-scale-gateway
sudo netstat -tlnp | grep 4001

# 웹 서비스
sudo systemctl status cynow

# API 테스트
curl http://localhost:8000/api/scale-gateway/latest/

# 브라우저 접속
# http://10.78.30.98/cynow/
```

---

## 🧪 테스트 시나리오

### 시나리오 1: 저울 시뮬레이터 테스트

```bash
# 터미널 1: 로그 모니터링
sudo journalctl -u cynow-scale-gateway -f

# 터미널 2: 데이터 전송
echo "ST , +000053.26 _kg" | nc localhost 4001

# 터미널 3: API 조회
curl http://localhost:8000/api/scale-gateway/latest/
```

### 시나리오 2: 출하 확정 테스트

```bash
# 1. 저울 데이터 전송
echo "ST , +000053.26 _kg" | nc localhost 4001

# 2. 최신값 조회
curl http://localhost:8000/api/scale-gateway/latest/

# 3. 출하 확정
curl -X POST http://localhost:8000/api/scale-gateway/commit/ \
  -H "Content-Type: application/json" \
  -d '{
    "cylinder_no": "TEST001",
    "event_type": "SHIP",
    "arrival_shipping_no": "AS20251218-001"
  }'

# 4. DB 확인
python manage.py shell
>>> from devices.models import ScaleWeightLog
>>> ScaleWeightLog.objects.all()
```

---

## 📁 주요 파일 및 디렉토리

### 신규 추가

```
devices/                                    # Scale Gateway API 앱
├── scale_gateway/
│   ├── listener.py                        # TCP 리스너
│   ├── parser.py                          # 데이터 파서
│   └── state.py                           # 메모리 캐시
├── management/commands/
│   └── scale_gateway_listener.py         # Django 커맨드
├── models.py                              # ScaleWeightLog 모델
├── views.py                               # REST API
├── urls.py                                # URL 라우팅
├── README.md                              # 사용자 가이드
└── TESTING_GUIDE.md                      # 테스트 가이드

deploy/
├── cynow-scale-gateway.service           # systemd 유닛 파일
├── SCALE_GATEWAY_DEPLOY.md              # 배포 가이드
└── env.production.example                # 환경변수 예시 (업데이트)

SCALE_GATEWAY_IMPLEMENTATION.md           # 구현 보고서
```

---

## 🔄 롤백 절차 (문제 발생 시)

### 1단계: 서비스 중지

```bash
sudo systemctl stop cynow-scale-gateway
sudo systemctl stop cynow
```

### 2단계: 백업 복원

```bash
# 최신 백업 확인
ls -lt /opt/cynow/ | grep backup

# 백업 복원
sudo rm -rf /opt/cynow/cynow
sudo cp -r /opt/cynow/cynow-backup-20251218-120000 /opt/cynow/cynow
sudo chown -R cynow:www-data /opt/cynow/cynow
```

### 3단계: 서비스 재시작

```bash
sudo systemctl start cynow
```

### 4단계: 마이그레이션 롤백 (필요시)

```bash
cd /opt/cynow/cynow
source venv/bin/activate
python manage.py migrate devices zero
```

---

## 📊 모니터링

### 로그 확인

```bash
# Scale Gateway
sudo journalctl -u cynow-scale-gateway -f
sudo journalctl -u cynow-scale-gateway -n 100

# CYNOW 웹
sudo journalctl -u cynow -f
tail -f /var/log/cynow/error.log

# NGINX
tail -f /var/log/nginx/cynow_access.log
tail -f /var/log/nginx/cynow_error.log
```

### 성능 모니터링

```bash
# 서비스 상태
sudo systemctl status cynow-scale-gateway
sudo systemctl status cynow

# 포트 확인
sudo netstat -tlnp | grep -E "(4001|8001)"

# 프로세스 확인
ps aux | grep -E "(scale_gateway|gunicorn)"

# 메모리 사용량
free -h
```

---

## 🐛 문제 해결

### Scale Gateway 관련

| 문제 | 원인 | 해결 |
|------|------|------|
| 서비스 시작 실패 | .env 파일 없음 | .env 파일에 Scale Gateway 설정 추가 |
| 포트 4001 바인딩 실패 | 포트 이미 사용 중 | `sudo lsof -i :4001`로 확인 후 종료 |
| 저울 연결 안됨 | 방화벽 차단 | `sudo ufw allow from <IP> to any port 4001` |
| API 404 오류 | URL 라우팅 오류 | `sudo systemctl restart cynow` |

자세한 내용은 `deploy/SCALE_GATEWAY_DEPLOY.md` 참고

---

## ✅ 배포 완료 체크리스트

### 웹 애플리케이션
- [ ] Gunicorn 정상 실행
- [ ] NGINX 정상 실행
- [ ] 브라우저 접속 확인
- [ ] 로그인/로그아웃 테스트
- [ ] 대시보드 정상 표시

### Scale Gateway API
- [ ] cynow-scale-gateway 서비스 실행 중
- [ ] 포트 4001 리스닝 확인
- [ ] 방화벽 규칙 추가
- [ ] API 엔드포인트 응답 확인
- [ ] 저울 연결 테스트 (시뮬레이터)
- [ ] DB에 로그 저장 확인

### 문서화
- [ ] 운영팀에 사용법 교육
- [ ] 긴급 연락망 확인
- [ ] 백업 정책 확인

---

## 📚 관련 문서

1. **deploy/SCALE_GATEWAY_DEPLOY.md** - Scale Gateway 상세 배포 가이드
2. **devices/README.md** - Scale Gateway API 사용자 가이드
3. **devices/TESTING_GUIDE.md** - 테스트 시나리오 및 명령어
4. **SCALE_GATEWAY_IMPLEMENTATION.md** - 구현 완료 보고서
5. **deploy/DEPLOY_CHECKLIST.md** - 전체 배포 체크리스트
6. **CHANGELOG.md** - 버전별 변경 이력

---

## 🔗 API 엔드포인트 (신규)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/scale-gateway/latest/` | 최신 저울 데이터 조회 |
| POST | `/api/scale-gateway/commit/` | 출하/회수 확정 (DB 저장) |

**베이스 URL**: `http://10.78.30.98/cynow`

---

## 📞 지원

**배포 후 문제 발생 시**:

1. 로그 확인
2. 이 문서의 "문제 해결" 섹션 참고
3. `deploy/SCALE_GATEWAY_DEPLOY.md` 참고
4. 개발팀 연락

---

## 🎉 배포 완료 후

### 다음 단계

1. **저울 장비 연결**:
   - 저울 네트워크 설정 (서버 IP:4001)
   - 연결 테스트
   - 실제 무게 측정 확인

2. **출하/회수 시스템 연동**:
   - POP에서 API 호출 테스트
   - 용기 무게 자동 입력 확인

3. **모니터링**:
   - 저울 데이터 수신 모니터링
   - 로그 정기 확인
   - 이상 패턴 감지

---

**CYNOW v1.3.0**  
**배포일**: 2025-12-18  
**배포자**: [이름]  
**상태**: ✅ 준비 완료

---

**배포를 시작하세요!** 🚀





