#!/bin/bash
# =============================================================================
# CYNOW 서버 초기 설정 스크립트
# =============================================================================
# 사용법: sudo bash setup.sh
# 주의: root 권한으로 실행 필요
# =============================================================================

set -e  # 오류 발생 시 중단

echo "=========================================="
echo "CYNOW 서버 초기 설정 시작"
echo "=========================================="

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 변수 설정
PROJECT_DIR="/opt/cynow/cynow"
VENV_DIR="${PROJECT_DIR}/venv"
LOG_DIR="/var/log/cynow"

# -----------------------------------------------------------------------------
# 1. 시스템 패키지 설치
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[1/7] 시스템 패키지 확인...${NC}"

if ! command -v nginx &> /dev/null; then
    echo "NGINX 설치 중..."
    apt-get update
    apt-get install -y nginx
fi

if ! command -v python3.10 &> /dev/null && ! command -v python3.11 &> /dev/null; then
    echo -e "${RED}Python 3.10+ 필요합니다. 수동 설치 후 다시 실행하세요.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 시스템 패키지 확인 완료${NC}"

# -----------------------------------------------------------------------------
# 2. 사용자 및 그룹 설정
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[2/7] 사용자 설정...${NC}"

if ! id "cynow" &>/dev/null; then
    useradd -m -s /bin/bash cynow
    usermod -aG www-data cynow
    echo -e "${GREEN}✓ cynow 사용자 생성 완료${NC}"
else
    echo "cynow 사용자 이미 존재"
fi

# -----------------------------------------------------------------------------
# 3. 디렉토리 생성
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[3/7] 디렉토리 생성...${NC}"

mkdir -p ${PROJECT_DIR}
mkdir -p ${LOG_DIR}
mkdir -p ${PROJECT_DIR}/staticfiles
mkdir -p ${PROJECT_DIR}/media

chown -R cynow:www-data ${PROJECT_DIR}
chown -R cynow:www-data ${LOG_DIR}

echo -e "${GREEN}✓ 디렉토리 생성 완료${NC}"

# -----------------------------------------------------------------------------
# 4. Gunicorn 서비스 설정
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[4/7] Gunicorn 서비스 설정...${NC}"

if [ -f "${PROJECT_DIR}/deploy/gunicorn.service" ]; then
    cp ${PROJECT_DIR}/deploy/gunicorn.service /etc/systemd/system/cynow.service
    systemctl daemon-reload
    systemctl enable cynow
    echo -e "${GREEN}✓ Gunicorn 서비스 등록 완료${NC}"
else
    echo -e "${RED}✗ deploy/gunicorn.service 파일이 없습니다${NC}"
fi

# -----------------------------------------------------------------------------
# 5. NGINX 설정
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[5/7] NGINX 설정...${NC}"

if [ -f "${PROJECT_DIR}/deploy/nginx_cynow.conf" ]; then
    cp ${PROJECT_DIR}/deploy/nginx_cynow.conf /etc/nginx/sites-available/cynow
    
    # 기존 심볼릭 링크 제거 후 재생성
    rm -f /etc/nginx/sites-enabled/cynow
    ln -s /etc/nginx/sites-available/cynow /etc/nginx/sites-enabled/
    
    # 문법 검사
    if nginx -t; then
        echo -e "${GREEN}✓ NGINX 설정 검사 통과${NC}"
    else
        echo -e "${RED}✗ NGINX 설정 오류! 수동 확인 필요${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ deploy/nginx_cynow.conf 파일이 없습니다${NC}"
fi

# -----------------------------------------------------------------------------
# 6. 환경 파일 생성 안내
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[6/7] 환경 설정 안내...${NC}"

if [ ! -f "${PROJECT_DIR}/.env" ]; then
    if [ -f "${PROJECT_DIR}/deploy/.env.production" ]; then
        cp ${PROJECT_DIR}/deploy/.env.production ${PROJECT_DIR}/.env
        chown cynow:www-data ${PROJECT_DIR}/.env
        chmod 600 ${PROJECT_DIR}/.env
        echo -e "${YELLOW}⚠ .env 파일이 생성되었습니다. 반드시 실제 값으로 수정하세요!${NC}"
        echo "   nano ${PROJECT_DIR}/.env"
    fi
else
    echo ".env 파일 이미 존재"
fi

# -----------------------------------------------------------------------------
# 7. Python 가상환경 안내
# -----------------------------------------------------------------------------
echo -e "${YELLOW}[7/7] Python 설정 안내...${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}초기 설정 완료!${NC}"
echo "=========================================="
echo ""
echo "다음 단계를 수동으로 실행하세요:"
echo ""
echo "1. 소스 코드 배포:"
echo "   rsync -avz /path/to/cynow/ ${PROJECT_DIR}/"
echo ""
echo "2. cynow 사용자로 전환:"
echo "   sudo su - cynow"
echo ""
echo "3. 가상환경 생성 및 의존성 설치:"
echo "   cd ${PROJECT_DIR}"
echo "   python3 -m venv venv"
echo "   source venv/bin/activate"
echo "   pip install -r requirements.txt"
echo "   pip install gunicorn"
echo ""
echo "4. .env 파일 수정:"
echo "   nano ${PROJECT_DIR}/.env"
echo ""
echo "5. Django 설정:"
echo "   python manage.py migrate"
echo "   python manage.py collectstatic --noinput"
echo "   python manage.py createsuperuser"
echo ""
echo "6. 서비스 시작:"
echo "   exit  # cynow 사용자에서 나가기"
echo "   sudo systemctl start cynow"
echo "   sudo systemctl reload nginx"
echo ""
echo "7. 접속 테스트:"
echo "   curl http://10.78.30.98/cynow/"
echo ""

