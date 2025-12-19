# CYNOW 배포 체크리스트

> 버전: v1.3.0  
> 배포 경로: http://10.78.30.98/cynow/  
> 서버: Ubuntu (10.78.30.98)  
> 신규: Scale Gateway API (저울 TCP 연동)

---

## 📋 사전 준비 체크리스트

- [ ] 서버 SSH 접속 확인
- [ ] PostgreSQL 연결 가능 확인
- [ ] NGINX 설치 확인 (`nginx -v`)
- [ ] Python 3.10+ 설치 확인 (`python3 --version`)
- [ ] 소스 코드 서버 전송 완료

---

## 🚀 최초 배포 순서

### 1단계: 디렉토리 및 사용자 설정

```bash
# 1. cynow 전용 사용자 생성 (권장)
sudo useradd -m -s /bin/bash cynow
sudo usermod -aG www-data cynow

# 2. 프로젝트 디렉토리 생성
sudo mkdir -p /opt/cynow/cynow
sudo chown -R cynow:www-data /opt/cynow/cynow

# 3. 로그 디렉토리 생성
sudo mkdir -p /var/log/cynow
sudo chown cynow:www-data /var/log/cynow
```

### 2단계: 소스 코드 배포

```bash
# cynow 사용자로 전환
sudo su - cynow

# 프로젝트 디렉토리로 이동
cd /opt/cynow/cynow

# 소스 코드 복사 (SCP, rsync, git 등)
# 예시: scp -r /path/to/cynow/* cynow@10.78.30.98:/opt/cynow/cynow/
```

### 3단계: Python 가상환경 및 의존성

```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt

# Gunicorn 설치 (requirements.txt에 없다면)
pip install gunicorn
```

### 4단계: 환경 변수 설정

```bash
# .env 파일 생성
cp env.example.txt .env

# .env 파일 편집
nano .env
```

**.env 필수 설정:**
```env
# 운영 환경 설정
DEBUG=False
SECRET_KEY=여기에_강력한_랜덤_문자열_입력
ALLOWED_HOSTS=10.78.30.98,localhost,127.0.0.1

# 서브패스 설정 (이미 settings.py에 기본값 있음)
FORCE_SCRIPT_NAME=/cynow
CSRF_TRUSTED_ORIGINS=http://10.78.30.98

# PostgreSQL 연결
DB_ENGINE=postgresql
DB_NAME=cycy_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432
```

### 5단계: Django 설정

```bash
# 마이그레이션 실행
python manage.py migrate

# devices 앱 마이그레이션 (Scale Gateway API)
python manage.py migrate devices

# 정적 파일 수집 (중요!)
python manage.py collectstatic --noinput

# 슈퍼유저 생성 (최초 1회)
python manage.py createsuperuser

# 권한 생성
python manage.py create_permissions
```

### 6단계: Gunicorn 서비스 설정

```bash
# 서비스 파일 복사 (root 권한 필요)
exit  # cynow 사용자에서 나가기
sudo cp /opt/cynow/cynow/deploy/gunicorn.service /etc/systemd/system/cynow.service

# 서비스 파일 경로 수정 (필요시)
sudo nano /etc/systemd/system/cynow.service

# systemd 리로드 및 서비스 시작
sudo systemctl daemon-reload
sudo systemctl enable cynow
sudo systemctl start cynow

# 상태 확인
sudo systemctl status cynow
```

### 7단계: NGINX 설정

```bash
# NGINX 설정 파일 복사
sudo cp /opt/cynow/cynow/deploy/nginx_cynow.conf /etc/nginx/sites-available/cynow

# 심볼릭 링크 생성
sudo ln -s /etc/nginx/sites-available/cynow /etc/nginx/sites-enabled/

# 문법 검사 (중요!)
sudo nginx -t

# NGINX 재시작
sudo systemctl reload nginx
```

### 8단계: Scale Gateway API 서비스 설정 (신규)

```bash
# Scale Gateway 리스너 서비스 파일 복사
exit  # cynow 사용자에서 나가기
sudo cp /opt/cynow/cynow/deploy/cynow-scale-gateway.service /etc/systemd/system/

# systemd 리로드 및 서비스 시작
sudo systemctl daemon-reload
sudo systemctl enable cynow-scale-gateway
sudo systemctl start cynow-scale-gateway

# 상태 확인
sudo systemctl status cynow-scale-gateway

# 로그 확인 (저울 연결 대기 중 메시지 확인)
sudo journalctl -u cynow-scale-gateway -n 50
```

**주의사항:**
- Scale Gateway는 포트 4001을 사용
- 방화벽에서 포트 4001 허용 필요 (저울 장비 IP만)
- 저울 장비가 연결되지 않아도 서비스는 정상 실행됨

### 9단계: 배포 확인

```bash
# 1. Gunicorn 직접 접속 테스트
curl http://127.0.0.1:8001/

# 2. NGINX 프록시 테스트
curl -I http://10.78.30.98/cynow/

# 3. 정적 파일 테스트
curl -I http://10.78.30.98/cynow/static/

# 4. Scale Gateway API 테스트
curl http://10.78.30.98/cynow/api/scale-gateway/latest/

# 5. 브라우저에서 접속
# http://10.78.30.98/cynow/
```

---

## 🔄 코드 업데이트 시 (재배포)

```bash
# 1. 소스 코드 업데이트
cd /opt/cynow/cynow
# git pull 또는 rsync 등

# 2. 가상환경 활성화
source venv/bin/activate

# 3. 의존성 업데이트 (필요시)
pip install -r requirements.txt

# 4. 마이그레이션 (DB 스키마 변경 시)
python manage.py migrate

# 5. 정적 파일 재수집 (CSS/JS 변경 시)
python manage.py collectstatic --noinput

# 6. 서비스 재시작
sudo systemctl restart cynow
sudo systemctl restart cynow-scale-gateway  # Scale Gateway도 재시작
```

---

## ⚠️ 문제 발생 시 점검 포인트

### 1. 502 Bad Gateway

**원인:** Gunicorn이 실행되지 않음

```bash
# Gunicorn 상태 확인
sudo systemctl status cynow

# Gunicorn 로그 확인
sudo journalctl -u cynow -n 50

# 수동 실행 테스트
cd /home/cynow/cynow
source venv/bin/activate
gunicorn --bind 127.0.0.1:8001 config.wsgi:application
```

### 2. 404 Not Found

**원인:** URL 경로 설정 문제

```bash
# NGINX 설정 확인
sudo nginx -t

# NGINX 로그 확인
tail -f /var/log/nginx/cynow_error.log
```

### 3. 정적 파일 404

**원인:** collectstatic 미실행 또는 NGINX alias 경로 불일치

```bash
# collectstatic 재실행
python manage.py collectstatic --noinput

# staticfiles 디렉토리 확인
ls -la /opt/cynow/cynow/staticfiles/

# NGINX 설정에서 alias 경로 확인
cat /etc/nginx/sites-available/cynow | grep alias
```

### 4. CSRF 검증 실패

**원인:** CSRF_TRUSTED_ORIGINS 미설정

```bash
# .env 파일 확인
grep CSRF .env

# 필요시 추가 (.env 파일 경로 확인)
# nano /opt/cynow/cynow/.env

# Gunicorn 재시작
sudo systemctl restart cynow
```

### 5. 500 Internal Server Error

**원인:** Django 애플리케이션 오류

```bash
# DEBUG=True로 임시 변경하여 상세 오류 확인
# .env 파일에서 DEBUG=True 설정

# Gunicorn 재시작
sudo systemctl restart cynow

# 오류 확인 후 DEBUG=False로 복원
```

---

## 🐛 자주 발생하는 서브패스 배포 오류

### 오류 1: 로그인 후 루트(/)로 리다이렉트

**증상:** 로그인 성공 후 `/cynow/`가 아닌 `/`로 이동

**해결:**
```python
# settings.py 확인
LOGIN_REDIRECT_URL = '/'  # FORCE_SCRIPT_NAME이 자동으로 붙음
# 문제 지속 시 명시적으로:
LOGIN_REDIRECT_URL = '/cynow/'
```

### 오류 2: Admin 페이지 CSS 깨짐

**증상:** `/cynow/admin/` 접속 시 스타일 없음

**해결:**
```bash
# collectstatic 재실행
python manage.py collectstatic --noinput

# NGINX 정적 파일 경로 확인
ls /home/cynow/cynow/staticfiles/admin/
```

### 오류 3: /cynow 접속 시 404 (슬래시 없이)

**증상:** `/cynow`로 접속하면 404, `/cynow/`는 정상

**해결:** NGINX 설정에 이미 리다이렉트 포함
```nginx
location = /cynow {
    return 301 /cynow/;
}
```

### 오류 4: 폼 제출 시 403 Forbidden

**증상:** POST 요청 시 CSRF 오류

**해결:**
```python
# settings.py 확인
CSRF_TRUSTED_ORIGINS = ['http://10.78.30.98']
CSRF_COOKIE_PATH = '/cynow/'
```

---

## 📊 운영 모니터링

### 로그 확인 명령

```bash
# Gunicorn 로그 (실시간)
tail -f /var/log/cynow/access.log
tail -f /var/log/cynow/error.log

# NGINX 로그 (실시간)
tail -f /var/log/nginx/cynow_access.log
tail -f /var/log/nginx/cynow_error.log

# Systemd 저널
sudo journalctl -u cynow -f
```

### 서비스 관리 명령

```bash
# Gunicorn
sudo systemctl start cynow
sudo systemctl stop cynow
sudo systemctl restart cynow
sudo systemctl status cynow

# NGINX
sudo systemctl reload nginx
sudo systemctl restart nginx
```

---

## 🔧 DEBUG 모드 전환

### 운영 중 디버깅 필요 시

```bash
# 1. .env 파일 수정
nano /opt/cynow/cynow/.env
# DEBUG=False → DEBUG=True

# 2. Gunicorn 재시작
sudo systemctl restart cynow

# 3. 디버깅 완료 후 반드시 DEBUG=False로 복원!
```

### 주의사항
- DEBUG=True 상태에서는 상세 오류 페이지가 노출됨
- 민감한 정보가 포함될 수 있으므로 디버깅 후 즉시 False로 복원
- 정적 파일은 DEBUG=False일 때 NGINX가 서빙해야 함

---

## 📁 권장 디렉토리 구조

```
/opt/cynow/
└── cynow/                    # 프로젝트 루트
    ├── config/               # Django 설정
    │   ├── settings.py
    │   ├── urls.py
    │   └── wsgi.py
    ├── core/                 # 핵심 앱
    ├── dashboard/            # 대시보드 앱
    ├── ...                   # 기타 앱들
    ├── static/               # 개발용 정적 파일
    ├── staticfiles/          # collectstatic 결과물 (NGINX alias)
    ├── media/                # 업로드 파일
    ├── templates/            # 공통 템플릿
    ├── deploy/               # 배포 설정 파일
    │   ├── gunicorn.service
    │   └── nginx_cynow.conf
    ├── venv/                 # 가상환경
    ├── .env                  # 환경변수 (Git 제외)
    ├── manage.py
    └── requirements.txt
```

---

## ✅ 최종 배포 체크리스트

### 기본 설정
- [ ] `.env` 파일에 `DEBUG=False` 설정
- [ ] `.env` 파일에 강력한 `SECRET_KEY` 설정
- [ ] `.env` 파일에 Scale Gateway 설정 추가
- [ ] `collectstatic` 실행 완료
- [ ] Gunicorn 서비스 자동 시작 활성화
- [ ] Scale Gateway 서비스 자동 시작 활성화
- [ ] NGINX 설정 `nginx -t` 통과

### 웹 애플리케이션
- [ ] 브라우저에서 http://10.78.30.98/cynow/ 접속 확인
- [ ] 로그인/로그아웃 테스트
- [ ] 정적 파일(CSS/JS) 로드 확인
- [ ] CSRF 오류 없이 폼 제출 가능
- [ ] Admin 페이지 접속 가능 (/cynow/admin/)

### Scale Gateway API
- [ ] Scale Gateway 서비스 실행 확인 (`systemctl status cynow-scale-gateway`)
- [ ] 포트 4001 리스닝 확인 (`netstat -tlnp | grep 4001`)
- [ ] API 엔드포인트 접근 확인 (`curl http://localhost:8000/api/scale-gateway/latest/`)
- [ ] 저울 연결 테스트 (저울 장비 접속 후)
- [ ] 방화벽에서 포트 4001 허용 (저울 장비 IP만)

---

## 🔄 이후 버전업 고려사항

### 무중단 배포 (향후)
- Gunicorn graceful restart: `kill -HUP <pid>`
- 블루-그린 배포 고려

### Docker 전환 (향후)
- 현재 구조 그대로 Dockerfile 작성 가능
- docker-compose로 Gunicorn + NGINX 구성

### CI/CD 파이프라인 (향후)
- GitHub Actions 또는 Jenkins 연동
- 자동 테스트 → 빌드 → 배포

---

*문서 작성일: 2024-12-16*  
*CYNOW v1.1.0*

