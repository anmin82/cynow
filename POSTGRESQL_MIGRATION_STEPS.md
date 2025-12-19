# PostgreSQL 전환 단계별 가이드

## 1단계: 환경 변수 설정

`.env` 파일을 생성하거나 수정하여 다음 내용을 추가하세요:

```env
# Django Settings
SECRET_KEY=django-insecure--%&9(@trtd#1y@4q-_4!45vrk@4d65y^e-9n!&0&ppm$*+6em7
DEBUG=True
ALLOWED_HOSTS=

# PostgreSQL Database Settings
DB_ENGINE=postgresql
DB_NAME=cycy_db
DB_USER=실제_사용자명
DB_PASSWORD=실제_비밀번호
DB_HOST=10.78.30.98
DB_PORT=5434
```

**중요**: 
- `DB_NAME=cycy_db` (CDC 데이터가 있는 데이터베이스)
- `DB_HOST`와 `DB_PORT`는 실제 PostgreSQL 서버 정보로 변경

## 2단계: 연결 테스트

```bash
python manage.py test_db_connection
```

연결이 성공하면 PostgreSQL 버전과 기존 테이블 목록이 표시됩니다.

## 3단계: Django 마이그레이션 실행

CYNOW 앱 테이블을 PostgreSQL에 생성:

```bash
python manage.py migrate
```

생성되는 테이블:
- `plan_forecast_monthly` (출하 계획)
- `plan_scheduled_monthly` (투입 계획)
- `hist_inventory_snapshot` (변화 이력 스냅샷)
- `hist_snapshot_request` (스냅샷 요청 기록)
- `report_export_log` (보고서 출력 이력)
- `core_translation` (번역 테이블)

## 4단계: CDC 테이블 확인

```bash
python manage.py check_sync_tables
```

이 명령어는 `fcms_cdc` 스키마와 `public` 스키마에서 동기화된 테이블을 찾아 표시합니다.

## 5단계: VIEW 생성

CDC 테이블을 기반으로 VIEW 생성:

```bash
# 자동으로 테이블 찾기
python manage.py create_postgresql_views

# 또는 스키마 지정
python manage.py create_postgresql_views --schema fcms_cdc

# 또는 특정 테이블 지정
python manage.py create_postgresql_views --table fcms_cdc.MA_CYLINDERS
```

## 6단계: 번역 데이터 로드

일본어 데이터를 번역 테이블에 로드:

```bash
python manage.py load_translations
```

## 문제 해결

### 연결 실패 시

1. PostgreSQL 서버가 실행 중인지 확인
2. 방화벽 설정 확인 (포트 5434)
3. 사용자 권한 확인:
```sql
GRANT ALL PRIVILEGES ON DATABASE cycy_db TO your_user;
GRANT USAGE ON SCHEMA public TO your_user;
GRANT USAGE ON SCHEMA fcms_cdc TO your_user;
GRANT SELECT ON ALL TABLES IN SCHEMA fcms_cdc TO your_user;
```

### 테이블을 찾을 수 없는 경우

1. `fcms_cdc` 스키마에 테이블이 있는지 확인:
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'fcms_cdc';
```

2. 스키마 접근 권한 확인
