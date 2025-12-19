# 데이터베이스 마이그레이션 가이드

## 현재 상황

- CDC 데이터: `cycy_db` 데이터베이스의 `fcms_cdc` 스키마
- CYNOW 프로젝트: `cynow` 데이터베이스 (기본값)

## 해결 방법: 같은 데이터베이스 사용

**같은 데이터베이스(`cycy_db`)를 사용**하도록 변경하는 것이 가장 간단하고 효율적입니다.

### 1단계: 환경 변수 설정

`.env` 파일 수정:

```env
# 기존
# DB_NAME=cynow

# 변경
DB_NAME=cycy_db
```

### 2단계: Django 마이그레이션 실행

같은 데이터베이스에 CYNOW 앱 테이블 생성:

```bash
python manage.py migrate
```

이 명령어는 `cycy_db` 데이터베이스의 `public` 스키마에 다음 테이블을 생성합니다:
- `plan_forecast_monthly`
- `plan_scheduled_monthly`
- `hist_inventory_snapshot`
- `hist_snapshot_request`
- `report_export_log`
- `core_translation` (번역 테이블)

### 3단계: VIEW 생성

`fcms_cdc` 스키마의 테이블을 참조하는 VIEW 생성:

```bash
# 자동으로 fcms_cdc 스키마에서 테이블 찾기
python manage.py create_postgresql_views

# 또는 스키마 지정
python manage.py create_postgresql_views --schema fcms_cdc

# 또는 특정 테이블 지정
python manage.py create_postgresql_views --table fcms_cdc.MA_CYLINDERS
```

### 4단계: 확인

```bash
# 동기화 테이블 확인 (fcms_cdc 스키마 포함)
python manage.py check_sync_tables

# 데이터베이스 연결 테스트
python manage.py test_db_connection
```

## 최종 구조

```
cycy_db (데이터베이스)
│
├── fcms_cdc (스키마) - CDC 동기화 테이블 (읽기 전용)
│   ├── MA_CYLINDERS
│   ├── MA_CYLINDER_SPECS
│   ├── MA_VALVE_SPECS
│   ├── MA_ITEMS
│   ├── MA_PARAMETERS
│   ├── TR_LATEST_CYLINDER_STATUSES
│   └── TR_CYLINDER_STATUS_HISTORIES
│
└── public (스키마) - CYNOW 앱 테이블 및 VIEW
    ├── plan_forecast_monthly
    ├── plan_scheduled_monthly
    ├── hist_inventory_snapshot
    ├── hist_snapshot_request
    ├── report_export_log
    ├── core_translation
    ├── vw_cynow_inventory (VIEW - fcms_cdc 테이블 참조)
    └── vw_cynow_cylinder_list (VIEW - fcms_cdc 테이블 참조)
```

## 장점

1. ✅ **단순함**: 하나의 데이터베이스만 관리
2. ✅ **성능**: 스키마 간 조회는 빠름
3. ✅ **관리 용이**: 백업/복원이 간단
4. ✅ **트랜잭션**: 필요시 같은 트랜잭션 사용 가능

## 주의사항

- Django는 기본적으로 `public` 스키마를 사용합니다
- CYNOW 앱 테이블은 `public` 스키마에 생성됩니다
- VIEW는 `public` 스키마에 생성되지만, `fcms_cdc` 스키마의 테이블을 참조합니다
- `settings.py`에 `search_path`가 설정되어 있어 스키마를 명시하지 않아도 접근 가능합니다

## 문제 해결

### VIEW 생성 실패 시

1. `fcms_cdc` 스키마에 테이블이 있는지 확인:
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'fcms_cdc';
```

2. 스키마 접근 권한 확인:
```sql
GRANT USAGE ON SCHEMA fcms_cdc TO your_user;
GRANT SELECT ON ALL TABLES IN SCHEMA fcms_cdc TO your_user;
```

### 테이블을 찾을 수 없는 경우

명시적으로 테이블명 지정:
```bash
python manage.py create_postgresql_views --table fcms_cdc.실제테이블명
```
