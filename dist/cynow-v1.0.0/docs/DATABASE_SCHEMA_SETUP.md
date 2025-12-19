# 데이터베이스 및 스키마 설정 가이드

## 현재 상황

- **CDC 데이터**: `cycy_db` 데이터베이스의 `fcms_cdc` 스키마에 저장됨
- **CYNOW 프로젝트**: `cynow` 데이터베이스 사용 (기본값)

## 문제점

PostgreSQL에서는 다른 데이터베이스에 있는 테이블을 직접 조회할 수 없습니다. 따라서 **같은 데이터베이스를 사용**해야 합니다.

## 해결 방법

### 방법 1: 같은 데이터베이스 사용 (권장)

`cycy_db` 데이터베이스를 사용하도록 설정 변경:

1. `.env` 파일 수정:
```env
DB_NAME=cycy_db
```

2. Django 마이그레이션 실행 (같은 데이터베이스에 CYNOW 테이블 생성):
```bash
python manage.py migrate
```

3. 스키마 지정하여 VIEW 생성:
```bash
python manage.py create_postgresql_views --schema fcms_cdc
```

### 방법 2: Foreign Data Wrapper 사용 (고급)

다른 데이터베이스의 테이블을 조회하려면 `postgres_fdw` 확장을 사용할 수 있지만, 복잡하고 성능 이슈가 있을 수 있습니다.

## 스키마 구조

```
cycy_db (데이터베이스)
├── fcms_cdc (스키마) - CDC 동기화 테이블
│   ├── MA_CYLINDERS
│   ├── MA_CYLINDER_SPECS
│   ├── MA_VALVE_SPECS
│   └── ...
└── public (스키마) - CYNOW 앱 테이블
    ├── plan_forecast_monthly
    ├── plan_scheduled_monthly
    ├── hist_inventory_snapshot
    ├── core_translation
    └── vw_cynow_inventory (VIEW)
    └── vw_cynow_cylinder_list (VIEW)
```

## 장점

1. **단순함**: 같은 데이터베이스 내에서 스키마만 분리
2. **성능**: 다른 데이터베이스 간 조회보다 빠름
3. **관리 용이**: 하나의 데이터베이스만 관리
4. **트랜잭션**: 필요시 같은 트랜잭션 내에서 작업 가능

## 주의사항

- Django는 기본적으로 `public` 스키마를 사용합니다
- CYNOW 앱 테이블은 `public` 스키마에 생성됩니다
- VIEW는 `public` 스키마에 생성하되, `fcms_cdc` 스키마의 테이블을 참조합니다
