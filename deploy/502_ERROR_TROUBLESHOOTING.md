# 502 Bad Gateway 에러 해결 가이드

## 문제 원인

502 Bad Gateway 에러는 Nginx가 백엔드 애플리케이션(Gunicorn/uWSGI)과 통신할 수 없을 때 발생합니다.

## 일반적인 원인

1. ✅ **백엔드 애플리케이션이 실행되지 않음**
2. ✅ **코드 오류로 인한 크래시**
3. ✅ **포트/소켓 연결 문제**
4. ✅ **권한 문제**
5. ✅ **타임아웃**

## 단계별 해결 방법

### 1단계: 서비스 상태 확인

```bash
# Gunicorn 상태 확인
sudo systemctl status gunicorn

# Nginx 상태 확인
sudo systemctl status nginx

# 포트 확인
sudo netstat -tulpn | grep :8000  # Gunicorn
sudo lsof -i :8000
```

**예상 결과:**
```
● gunicorn.service - gunicorn daemon
   Loaded: loaded (/etc/systemd/system/gunicorn.service; enabled)
   Active: active (running)
```

만약 `inactive (dead)` 또는 `failed` 상태라면:
```bash
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
```

### 2단계: 로그 확인

```bash
# Gunicorn 로그 (최근 50줄)
sudo journalctl -u gunicorn -n 50 --no-pager

# Gunicorn 실시간 로그
sudo journalctl -u gunicorn -f

# Nginx 에러 로그
sudo tail -f /var/log/nginx/error.log

# Django 로그 (설정된 경우)
tail -f /var/log/cynow/django.log
```

**주요 에러 패턴:**

#### 에러 1: ModuleNotFoundError
```
ModuleNotFoundError: No module named 'orders.urls'
```
**해결:** 코드 업데이트 및 재시작
```bash
cd /home/cynow/cynow
git pull origin main
sudo systemctl restart gunicorn
```

#### 에러 2: Import Error
```
ImportError: cannot import name 'xxx' from 'orders'
```
**해결:** Python 경로 및 가상환경 확인
```bash
source venv/bin/activate
which python
python -c "import orders; print(orders.__file__)"
```

#### 에러 3: Database Error
```
django.db.utils.OperationalError: no such table
```
**해결:** 마이그레이션 실행
```bash
source venv/bin/activate
python manage.py migrate
```

### 3단계: Gunicorn 설정 확인

```bash
# Gunicorn 서비스 파일 확인
cat /etc/systemd/system/gunicorn.service

# 또는 socket 방식인 경우
cat /etc/systemd/system/gunicorn.socket
```

**올바른 설정 예시:**
```ini
[Unit]
Description=gunicorn daemon
After=network.target

[Service]
User=cynow
Group=www-data
WorkingDirectory=/home/cynow/cynow
ExecStart=/home/cynow/cynow/venv/bin/gunicorn \
          --workers 3 \
          --bind unix:/home/cynow/cynow/gunicorn.sock \
          config.wsgi:application

[Install]
WantedBy=multi-user.target
```

**설정 변경 후:**
```bash
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

### 4단계: Nginx 설정 확인

```bash
# Nginx 설정 파일 확인
sudo nano /etc/nginx/sites-available/cynow

# 설정 테스트
sudo nginx -t

# Nginx 재시작
sudo systemctl restart nginx
```

**올바른 프록시 설정:**
```nginx
location /cynow/ {
    proxy_pass http://unix:/home/cynow/cynow/gunicorn.sock;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### 5단계: 소켓 파일 확인 (Unix Socket 사용 시)

```bash
# 소켓 파일 확인
ls -l /home/cynow/cynow/gunicorn.sock

# 권한 확인
sudo chown www-data:www-data /home/cynow/cynow/gunicorn.sock
sudo chmod 660 /home/cynow/cynow/gunicorn.sock
```

### 6단계: 권한 문제 해결

```bash
# 프로젝트 디렉토리 권한
sudo chown -R cynow:www-data /home/cynow/cynow
sudo chmod -R 755 /home/cynow/cynow

# Static 파일 권한
sudo chown -R www-data:www-data /home/cynow/cynow/static
sudo chmod -R 755 /home/cynow/cynow/static
```

### 7단계: 수동 Gunicorn 실행 테스트

```bash
cd /home/cynow/cynow
source venv/bin/activate

# 수동 실행 (포트 8000)
gunicorn --bind 0.0.0.0:8000 config.wsgi:application

# 브라우저에서 직접 접속 테스트
# http://10.78.30.98:8000/
```

성공하면 Gunicorn 자체는 문제없음 → Nginx 설정 확인
실패하면 Django 코드 문제 → 로그 확인

### 8단계: Django 설정 확인

```bash
source venv/bin/activate
python manage.py check
python manage.py migrate --check
```

## 현재 문제 (orders 앱 재구성)

### 증상
```
ModuleNotFoundError: No module named 'orders.urls'
```

### 원인
배포 서버에 최신 코드(재구성된 orders 앱)가 반영되지 않음

### 해결
```bash
# 1. 서버 접속
ssh user@10.78.30.98

# 2. 프로젝트 디렉토리
cd /home/cynow/cynow

# 3. 코드 업데이트
git pull origin main

# 4. orders/urls.py 확인
cat orders/urls.py

# 5. 마이그레이션
source venv/bin/activate
python manage.py migrate orders

# 6. Static 파일 수집
python manage.py collectstatic --noinput

# 7. Gunicorn 재시작
sudo systemctl restart gunicorn

# 8. 로그 확인
sudo journalctl -u gunicorn -n 20

# 9. 브라우저에서 확인
# http://10.78.30.98/cynow/orders/
```

## 빠른 진단 스크립트

```bash
#!/bin/bash
echo "=== CYNOW 502 에러 진단 ==="

echo -e "\n1. Gunicorn 상태:"
sudo systemctl status gunicorn --no-pager | head -5

echo -e "\n2. Nginx 상태:"
sudo systemctl status nginx --no-pager | head -5

echo -e "\n3. 포트 리스닝:"
sudo netstat -tulpn | grep :8000

echo -e "\n4. Gunicorn 최근 로그:"
sudo journalctl -u gunicorn -n 10 --no-pager

echo -e "\n5. Nginx 에러 로그:"
sudo tail -5 /var/log/nginx/error.log

echo -e "\n6. orders/urls.py 존재 여부:"
ls -l /home/cynow/cynow/orders/urls.py

echo -e "\n7. Python 경로:"
source /home/cynow/cynow/venv/bin/activate
which python
python --version
```

## 체크리스트

- [ ] Gunicorn 서비스 실행 중
- [ ] Nginx 서비스 실행 중
- [ ] 최신 코드 pull 완료
- [ ] orders/urls.py 파일 존재
- [ ] 마이그레이션 완료
- [ ] Static 파일 수집 완료
- [ ] Gunicorn 재시작 완료
- [ ] 로그에 에러 없음

## 추가 도움

여전히 문제가 해결되지 않으면:

1. **전체 로그 확인**
   ```bash
   sudo journalctl -u gunicorn --since "10 minutes ago"
   ```

2. **Gunicorn 프로세스 확인**
   ```bash
   ps aux | grep gunicorn
   ```

3. **Gunicorn 강제 재시작**
   ```bash
   sudo systemctl stop gunicorn
   sudo pkill -9 gunicorn
   sudo systemctl start gunicorn
   ```

4. **서버 재부팅** (최후의 수단)
   ```bash
   sudo reboot
   ```


