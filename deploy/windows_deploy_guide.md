# Windows에서 배포 서버로 파일 전송 가이드

## WinSCP 사용

### 1. WinSCP 다운로드 및 설치
https://winscp.net/

### 2. 서버 접속 설정
- 호스트: 10.78.30.98
- 포트: 22
- 사용자명: (서버 계정)
- 비밀번호: (서버 비밀번호)

### 3. 전송할 파일
```
orders/urls.py
orders/models.py
orders/views.py
orders/forms.py
orders/admin.py
orders/services/move_no_guide_service.py
orders/services/po_progress_service.py
orders/templates/orders/po_list.html
orders/templates/orders/po_detail.html
orders/templates/orders/po_form.html
orders/migrations/0001_initial.py
```

### 4. 서버에서 실행
PuTTY로 서버 접속 후:
```bash
cd /home/cynow/cynow
source venv/bin/activate
python manage.py migrate orders
sudo systemctl restart gunicorn
```

## PowerShell SCP 사용

```powershell
# 단일 파일 전송
scp C:\cynow\orders\urls.py user@10.78.30.98:/home/cynow/cynow/orders/

# 디렉토리 전체 전송
scp -r C:\cynow\orders\* user@10.78.30.98:/home/cynow/cynow/orders/
```

## Git 사용 (권장)

### 1. 로컬에서 커밋 및 푸시
```powershell
cd C:\cynow
git add orders/
git commit -m "Orders 앱 재구성 완료"
git push origin main
```

### 2. 서버에서 풀
```bash
ssh user@10.78.30.98
cd /home/cynow/cynow
git pull origin main
source venv/bin/activate
python manage.py migrate orders
sudo systemctl restart gunicorn
```


