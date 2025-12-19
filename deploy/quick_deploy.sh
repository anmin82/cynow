#!/bin/bash

# CYNOW 빠른 배포 스크립트

echo "🚀 CYNOW 배포 시작..."

# 1. 프로젝트 디렉토리로 이동
cd /home/cynow/cynow  # 실제 경로로 수정 필요

# 2. Git pull
echo "📥 최신 코드 가져오기..."
git pull origin main

# 3. 가상환경 활성화
echo "🐍 가상환경 활성화..."
source venv/bin/activate

# 4. 의존성 업데이트 (requirements.txt 변경 시)
# pip install -r requirements.txt

# 5. Static 파일 수집
echo "📦 Static 파일 수집..."
python manage.py collectstatic --noinput

# 6. 마이그레이션
echo "🗄️ 데이터베이스 마이그레이션..."
python manage.py migrate

# 7. Gunicorn 재시작
echo "🔄 Gunicorn 재시작..."
sudo systemctl restart gunicorn
sleep 2

# 8. 상태 확인
echo "✅ 서비스 상태 확인..."
sudo systemctl status gunicorn --no-pager

# 9. Nginx 재시작 (필요시)
# sudo systemctl restart nginx

echo "✅ 배포 완료!"
echo "🌐 접속: http://10.78.30.98/cynow/"


