# CYNOW 버전업 배포 가이드

> 이 문서는 CYNOW 운영 중 새 버전을 배포할 때 사용합니다.

---

## 📋 버전업 배포 전 체크리스트

- [ ] 새 버전 소스 코드 준비 완료
- [ ] CHANGELOG.md 확인 (변경 사항 파악)
- [ ] DB 스키마 변경 여부 확인 (migrations 폴더)
- [ ] requirements.txt 변경 여부 확인
- [ ] 운영 서버 백업 (필요시)

---

## 🚀 버전업 배포 순서

### 1단계: 로컬에서 서버로 파일 전송

**Windows PowerShell에서 실행:**

```powershell
cd C:\cynow

# 방법 1: 전체 프로젝트 전송 (권장)
scp -r config core dashboard cylinders alerts history plans reports templates static requirements.txt manage.py deploy VERSION CHANGELOG.md root@10.78.30.98:/opt/cynow/cynow/

# 방법 2: 변경된 파일만 전송 (rsync 사용 - Git Bash 또는 WSL)
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '*.pyc' --exclude '.env' --exclude 'staticfiles' --exclude 'media' ./ root@10.78.30.98:/opt/cynow/cynow/
```

---

### 2단계: 서버에서 배포 작업

**서버 SSH 접속:**

```bash
ssh root@10.78.30.98
```

**cynow 사용자로 전환:**

```bash
sudo su - cynow
cd /opt/cynow/cynow
source venv/bin/activate
```

---

### 3단계: 의존성 업데이트 (requirements.txt 변경 시)

```bash
pip install -r requirements.txt
```

---

### 4단계: DB 마이그레이션 (스키마 변경 시)

```bash
# 마이그레이션 파일 확인
python manage.py showmigrations

# 마이그레이션 실행
python manage.py migrate
```

---

### 5단계: 정적 파일 수집 (CSS/JS 변경 시)

```bash
python manage.py collectstatic --noinput
```

---

### 6단계: 서비스 재시작

```bash
# cynow 사용자에서 나가기
exit

# Gunicorn 재시작
sudo systemctl restart cynow

# 상태 확인
sudo systemctl status cynow
```

---

### 7단계: 배포 확인

```bash
# 버전 확인
cat /opt/cynow/cynow/VERSION

# 웹 접속 테스트
curl -I http://10.78.30.98/cynow/

# 브라우저에서 확인
# http://10.78.30.98/cynow/
```

---

## ⚡ 빠른 버전업 (한 번에 실행)

변경 사항이 간단할 때 사용하는 빠른 명령어:

```bash
# 서버 접속 후 한 번에 실행
ssh root@10.78.30.98

# 한 줄로 배포
sudo su - cynow -c "cd /opt/cynow/cynow && source venv/bin/activate && pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput" && sudo systemctl restart cynow && sudo systemctl status cynow
```

---

## 🔄 롤백 방법 (문제 발생 시)

### 방법 1: 이전 버전 소스로 복원

```bash
# 로컬에서 이전 버전 전송
cd C:\cynow\dist\cynow-v1.0.0
scp -r * root@10.78.30.98:/opt/cynow/cynow/

# 서버에서 재시작
ssh root@10.78.30.98
sudo systemctl restart cynow
```

### 방법 2: DB 마이그레이션 롤백

```bash
# 특정 마이그레이션으로 되돌리기
python manage.py migrate <app_name> <migration_number>

# 예: core 앱을 0001로 롤백
python manage.py migrate core 0001
```

---

## 📝 버전별 특이사항 기록

### v1.1.0 → v1.2.0 (예시)
- [ ] 새 의존성: `pip install 새패키지`
- [ ] DB 마이그레이션 필요
- [ ] NGINX 설정 변경 필요

### v1.0.0 → v1.1.0
- [x] 서브패스 배포 설정 추가 (settings.py)
- [x] 최초 NGINX + Gunicorn 구성

---

## 🛠️ 유지보수 명령어 모음

### 로그 확인

```bash
# Gunicorn 로그 (실시간)
tail -f /var/log/cynow/access.log
tail -f /var/log/cynow/error.log

# NGINX 로그
tail -f /var/log/nginx/cynow_access.log
tail -f /var/log/nginx/cynow_error.log

# Systemd 로그
sudo journalctl -u cynow -f
```

### 서비스 관리

```bash
# 시작/중지/재시작
sudo systemctl start cynow
sudo systemctl stop cynow
sudo systemctl restart cynow

# 상태 확인
sudo systemctl status cynow

# 부팅 시 자동 시작 설정
sudo systemctl enable cynow
sudo systemctl disable cynow
```

### Django 관리 명령

```bash
# cynow 사용자로 전환
sudo su - cynow
cd /opt/cynow/cynow
source venv/bin/activate

# 자주 사용하는 명령
python manage.py shell                    # Django 쉘
python manage.py dbshell                  # DB 쉘
python manage.py showmigrations           # 마이그레이션 상태
python manage.py check                    # 설정 검증
python manage.py createsuperuser          # 관리자 생성
```

---

## 📅 정기 점검 항목

### 주간
- [ ] 로그 파일 크기 확인
- [ ] 디스크 사용량 확인

### 월간
- [ ] Django/Python 보안 업데이트 확인
- [ ] 백업 테스트

---

## 🆘 긴급 대응

### 서비스 완전 중단 시

```bash
# 1. 상태 확인
sudo systemctl status cynow
sudo systemctl status nginx

# 2. 로그 확인
sudo journalctl -u cynow -n 100

# 3. 수동 실행 테스트
sudo su - cynow
cd /opt/cynow/cynow
source venv/bin/activate
gunicorn --bind 127.0.0.1:8001 config.wsgi:application

# 4. 문제 해결 후 서비스 재시작
exit
sudo systemctl restart cynow
```

### DEBUG 모드로 오류 확인

```bash
# .env 수정
nano /opt/cynow/cynow/.env
# DEBUG=True로 변경

# 재시작
sudo systemctl restart cynow

# 브라우저에서 오류 확인 후
# 반드시 DEBUG=False로 복원!
```

---

*마지막 업데이트: 2024-12-16*
*CYNOW v1.1.0*

