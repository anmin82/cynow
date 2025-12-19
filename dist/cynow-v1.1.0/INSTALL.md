# CYNOW v1.1.0 설치 가이드

## 시스템 요구사항

- Python 3.10 이상
- PostgreSQL 14 이상 (CDC 데이터 연동)
- 4GB RAM 이상

## 빠른 설치

### 1. 가상환경 생성 및 활성화

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 설정

`env.example.txt`를 `.env`로 복사하고 수정:

```bash
copy env.example.txt .env
```

`.env` 파일 수정:
```
DB_ENGINE=postgresql
DB_NAME=cynow
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=10.78.30.98
DB_PORT=5434
```

### 4. 데이터베이스 초기화

```bash
# Django 마이그레이션
python manage.py migrate

# 스냅샷 테이블 생성
psql -h DB_HOST -U DB_USER -d DB_NAME -f sql/create_cy_cylinder_current.sql

# 동기화 트리거 생성
psql -h DB_HOST -U DB_USER -d DB_NAME -f sql/create_sync_triggers.sql

# 정책 테이블 생성
psql -h DB_HOST -U DB_USER -d DB_NAME -f sql/create_cynow_policy_tables.sql
```

### 5. 초기 데이터 동기화

```bash
# 전체 스냅샷 생성
python manage.py resync_all_cylinders
```

### 6. 슈퍼유저 생성

```bash
python manage.py createsuperuser
```

### 7. 서버 실행

```bash
# 개발 서버
python manage.py runserver 0.0.0.0:8000

# 프로덕션 (Gunicorn)
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

## 접속

- 대시보드: http://localhost:8000/
- 관리자: http://localhost:8000/admin/

## 기본 EndUser 정책

| 가스명 | 기본 EndUser |
|--------|-------------|
| COS | SEC |
| CLF3 | SEC |
| CF4 | SDC |

## 문제 해결

### 번역이 적용되지 않는 경우

```bash
python manage.py resync_all_cylinders
```

### EndUser가 NULL인 용기가 있는 경우

1. Admin에서 해당 가스명의 기본 EndUser 정책 추가
2. 스냅샷 재동기화

## 업그레이드

v1.0.0에서 업그레이드 시:

```bash
# 마이그레이션 실행
python manage.py migrate

# 동기화 함수 재생성
python manage.py recreate_sync_function

# 스냅샷 재동기화
python manage.py resync_all_cylinders
```

## 지원

문의: CYNOW 개발팀










