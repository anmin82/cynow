#!/bin/bash

##############################################
# CYNOW Git 배포 스크립트
# 사용법: ./deploy/git_deploy.sh
##############################################

set -e  # 에러 발생 시 중단

echo "=== CYNOW Git 배포 시작 ==="

# 색상 코드
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 프로젝트 디렉토리
PROJECT_DIR="/opt/cynow/cynow"
VENV_DIR="$PROJECT_DIR/venv"

# 1. 디렉토리 이동
echo -e "${YELLOW}[1/6] 프로젝트 디렉토리로 이동...${NC}"
cd $PROJECT_DIR

# 2. Git Pull
echo -e "${YELLOW}[2/6] 최신 코드 가져오기...${NC}"
git pull origin main

# 3. 가상환경 활성화
echo -e "${YELLOW}[3/6] 가상환경 활성화...${NC}"
source $VENV_DIR/bin/activate

# 4. 패키지 업데이트 (requirements.txt 변경 시)
echo -e "${YELLOW}[4/6] 패키지 확인 및 업데이트...${NC}"
pip install -r requirements.txt --quiet

# 5. Django 관리 작업
echo -e "${YELLOW}[5/6] Django 관리 작업...${NC}"

# 마이그레이션 확인
python manage.py migrate --check > /dev/null 2>&1 || {
    echo -e "${GREEN}  → 마이그레이션 실행...${NC}"
    python manage.py migrate
}

# Static 파일 수집
echo -e "${GREEN}  → Static 파일 수집...${NC}"
python manage.py collectstatic --noinput --clear

# 6. Gunicorn 재시작
echo -e "${YELLOW}[6/6] Gunicorn 재시작...${NC}"

# Graceful reload (추천)
if pkill -HUP -f "gunicorn.*8001"; then
    echo -e "${GREEN}  → Gunicorn graceful reload 완료${NC}"
else
    echo -e "${RED}  → Gunicorn 프로세스를 찾을 수 없습니다. 수동 시작이 필요합니다.${NC}"
    exit 1
fi

# 프로세스 확인
sleep 2
if ps aux | grep -v grep | grep "gunicorn.*8001" > /dev/null; then
    echo -e "${GREEN}✅ Gunicorn이 정상적으로 실행 중입니다.${NC}"
else
    echo -e "${RED}❌ Gunicorn이 실행되지 않았습니다!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 배포 완료!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "접속 URL: http://10.78.30.98/cynow/"
echo ""
echo "로그 확인:"
echo "  - Nginx 에러: tail -f /var/log/nginx/error.log"
echo "  - Gunicorn: ps aux | grep gunicorn"
echo ""

















