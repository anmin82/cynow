# CYNOW v1.0.0 설치 가이드

## 시스템 요구사항

- Python 3.10+
- PostgreSQL 13+
- Debezium (FCMS CDC 연동용)

## 설치 절차

### 1. 파일 배포

```bash
# 배포 파일 압축 해제
unzip cynow-v1.0.0.zip -d /opt/cynow
cd /opt/cynow
```

### 2. 가상환경 생성 및 의존성 설치

```bash
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 환경 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집 (실제 값 입력)
nano .env
```

### 4. 데이터베이스 설정

```bash
# PostgreSQL에서 데이터베이스 생성
psql -U postgres
CREATE DATABASE cynow;
CREATE USER cynow_user WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE cynow TO cynow_user;
\q

# Django 마이그레이션
python manage.py migrate

# 슈퍼유저 생성
python manage.py createsuperuser
```

### 5. CYNOW 테이블 및 함수 생성

```bash
# cy_cylinder_current 테이블 생성
psql -U cynow_user -d cynow -f sql/create_cy_cylinder_current.sql

# 동기화 트리거 생성
psql -U cynow_user -d cynow -f sql/create_sync_triggers.sql

# EndUser 정책 테이블 생성
psql -U cynow_user -d cynow -f sql/create_cynow_policy_tables.sql
```

### 6. 초기 데이터 동기화

```bash
# 전체 스냅샷 생성
python manage.py resync_all_cylinders
```

### 7. 서버 시작

```bash
# 개발 서버
python manage.py runserver 0.0.0.0:8000

# 프로덕션 (Gunicorn)
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

## 접속

- 대시보드: http://localhost:8000/
- 관리자: http://localhost:8000/admin/

## 문제 해결

### CDC 데이터가 보이지 않는 경우
1. `fcms_cdc` 스키마의 테이블 확인
2. Debezium 커넥터 상태 확인
3. `python manage.py resync_all_cylinders` 재실행

### 번역이 적용되지 않는 경우
1. Admin에서 번역 추가 (Core > 번역)
2. `python manage.py resync_all_cylinders` 재실행

