# ONLYOFFICE Document Server 설치 및 연동 가이드

## 개요

ONLYOFFICE Document Server를 사용하면 DOCX 템플릿을 웹 브라우저에서 직접 편집할 수 있습니다.
이 가이드는 Docker 기반으로 ONLYOFFICE를 설치하고 Django와 연동하는 방법을 설명합니다.

---

## 1. 시스템 요구사항

- **Docker**: 20.10 이상
- **Docker Compose**: 2.0 이상
- **RAM**: 최소 4GB (권장 8GB)
- **디스크**: 10GB 이상
- **네트워크**: Django 서버와 ONLYOFFICE 서버 간 통신 가능

---

## 2. ONLYOFFICE 설치

### 2.1. Docker Compose 파일 복사

```bash
cd /opt/cynow
mkdir -p deploy
cp cynow/deploy/docker-compose.onlyoffice.yml deploy/
```

### 2.2. 환경변수 설정

```bash
# JWT 시크릿 설정 (보안을 위해 변경 권장)
export ONLYOFFICE_JWT_SECRET="your-secure-secret-key"

# 또는 .env 파일 생성
echo "ONLYOFFICE_JWT_SECRET=your-secure-secret-key" > deploy/.env
```

### 2.3. 컨테이너 시작

```bash
cd /opt/cynow/deploy
docker-compose -f docker-compose.onlyoffice.yml up -d

# 로그 확인 (초기화에 1-2분 소요)
docker logs -f onlyoffice-docs
```

### 2.4. 설치 확인

```bash
# 헬스체크
curl http://localhost:8080/healthcheck

# 브라우저에서 접속
# http://서버IP:8080
```

---

## 3. Django 환경 설정

### 3.1. 환경변수 설정

```bash
# /opt/cynow/.env 또는 시스템 환경변수에 추가

# ONLYOFFICE Document Server URL
ONLYOFFICE_URL=http://10.78.30.98:8080

# JWT 시크릿 (docker-compose.yml과 동일해야 함)
ONLYOFFICE_JWT_SECRET=your-secure-secret-key

# Django 서버 URL (ONLYOFFICE가 접근할 수 있는 URL)
DJANGO_BASE_URL=http://10.78.30.98
```

### 3.2. Gunicorn/Systemd 재시작

```bash
sudo systemctl restart cynow.service
```

---

## 4. 방화벽 설정

ONLYOFFICE와 Django 간 통신을 위해 포트를 열어야 합니다.

```bash
# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload

# Ubuntu (ufw)
sudo ufw allow 8080/tcp

# iptables
sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
```

---

## 5. 사용 방법

### 5.1. 템플릿 편집

1. Django 사이트 접속 → **관리** → **템플릿 관리**
2. 원하는 템플릿의 **"편집"** 버튼 클릭
3. ONLYOFFICE 에디터가 로드됨
4. 문서 편집 후 저장 (자동 저장 활성화)
5. **"돌아가기"** 클릭하여 목록으로 복귀

### 5.2. 권한

- **관리자 (is_staff=True)**: 편집 가능
- **일반 사용자**: 편집 버튼 숨김

---

## 6. 템플릿 변수 사용법

ONLYOFFICE 에디터에서 템플릿 변수를 입력하려면:

### 6.1. 단일 변수

```
{{supplier_company}}
{{quote_date}}
```

### 6.2. 반복 테이블 (품목 리스트)

테이블의 첫 번째 데이터 행에:

| 첫 번째 셀 | 중간 셀들 | 마지막 셀 |
|----------|----------|----------|
| `{%tr for item in items %}{{item.no}}` | `{{item.product_code}}` | `{{item.amount}}{%tr endfor %}` |

---

## 7. 문제 해결

### 7.1. 에디터가 로드되지 않음

```bash
# ONLYOFFICE 상태 확인
docker ps | grep onlyoffice
docker logs onlyoffice-docs --tail 50

# Django에서 ONLYOFFICE 접근 확인
curl http://localhost:8080/healthcheck
```

### 7.2. 저장이 안 됨

- 콜백 URL 확인: `DJANGO_BASE_URL`이 ONLYOFFICE에서 접근 가능한지
- 방화벽 확인: Django 포트(80)가 열려 있는지
- JWT 시크릿 일치 여부 확인

### 7.3. JWT 오류

```bash
# docker-compose와 Django 환경변수의 시크릿이 같은지 확인
echo $ONLYOFFICE_JWT_SECRET
docker exec onlyoffice-docs cat /etc/onlyoffice/documentserver/local.json | grep secret
```

---

## 8. 보안 고려사항

### 8.1. HTTPS 사용 (프로덕션 권장)

프로덕션 환경에서는 HTTPS를 사용하세요:

1. Nginx를 리버스 프록시로 설정
2. SSL 인증서 적용
3. ONLYOFFICE_URL과 DJANGO_BASE_URL을 https://로 변경

### 8.2. JWT 시크릿

- 복잡한 문자열 사용 (최소 32자)
- 환경변수로 관리 (코드에 하드코딩 금지)

### 8.3. 접근 제한

- 템플릿 편집은 관리자만 가능
- 필요시 IP 기반 접근 제한 추가

---

## 9. 참고 자료

- [ONLYOFFICE Docs 공식 문서](https://api.onlyoffice.com/editors/basic)
- [Docker 설치 가이드](https://helpcenter.onlyoffice.com/installation/docs-community-install-docker.aspx)
- [API 설정 옵션](https://api.onlyoffice.com/editors/config/)

---

## 변경 이력

| 날짜 | 버전 | 설명 |
|------|------|------|
| 2025-12-25 | 1.0 | 초기 버전 |

