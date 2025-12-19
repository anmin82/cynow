# PostgreSQL 전환 가이드

## 1. 환경 설정

### 1.1 .env 파일 생성

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 입력하세요:

```env
# Django Settings
SECRET_KEY=django-insecure--%&9(@trtd#1y@4q-_4!45vrk@4d65y^e-9n!&0&ppm$*+6em7
DEBUG=True
ALLOWED_HOSTS=

# PostgreSQL Database Settings
DB_ENGINE=postgresql
DB_NAME=cynow
DB_USER=실제_사용자명
DB_PASSWORD=실제_비밀번호
DB_HOST=10.78.30.98
DB_PORT=5434
```

또는 `.env.example` 파일을 `.env`로 복사한 후 수정하세요:

```bash
copy .env.example .env
# 또는 PowerShell에서: Copy-Item .env.example .env
```

### 1.2 패키지 설치

```bash
pip install -r requirements.txt
```

`psycopg2-binary` 패키지가 자동으로 설치됩니다.

## 2. PostgreSQL 연결 확인

```bash
python manage.py test_db_connection
```

이 명령은 다음을 수행합니다:
- PostgreSQL 연결 정보 표시
- 연결 테스트
- 기존 테이블 및 VIEW 목록 확인

## 3. Django 마이그레이션 실행

CYNOW 앱 테이블을 생성합니다:

```bash
python manage.py migrate
```

생성되는 테이블:
- `plan_forecast_monthly` (출하 계획)
- `plan_scheduled_monthly` (투입 계획)
- `hist_inventory_snapshot` (변화 이력 스냅샷)
- `hist_snapshot_request` (스냅샷 요청 기록)
- `report_export_log` (보고서 출력 이력)

## 4. VIEW 생성

실제 동기화 테이블을 기반으로 VIEW를 생성합니다:

```bash
python manage.py create_postgresql_views
```

이 명령은:
1. PostgreSQL에서 동기화 테이블(`fcms_cylinders` 등)을 자동으로 찾습니다
2. 테이블 스키마를 분석합니다
3. 필수 컬럼을 매핑합니다
4. 다음 VIEW를 생성합니다:
   - `vw_cynow_inventory` (용기종류 × 상태 × 위치별 수량 집계)
   - `vw_cynow_cylinder_list` (개별 용기 리스트)

### 수동 VIEW 생성

자동 생성이 실패하는 경우, PostgreSQL에 직접 접속하여 수동으로 생성할 수 있습니다.

```sql
-- vw_cynow_inventory 예시 (실제 테이블명/컬럼명으로 수정 필요)
CREATE VIEW vw_cynow_inventory AS
SELECT 
    '' as cylinder_type_key,
    GAS_NAME as gas_name,
    CAPACITY as capacity,
    VALVE_SPEC_NAME as valve_spec,
    CYLINDER_SPEC_NAME as cylinder_spec,
    USAGE_PLACE as usage_place,
    CASE 
        WHEN CONDITION_CODE IN ('100', '102') THEN '보관'
        WHEN CONDITION_CODE IN ('210', '220') THEN '충전'
        WHEN CONDITION_CODE = '420' THEN '분석'
        WHEN CONDITION_CODE = '500' THEN '창입'
        WHEN CONDITION_CODE = '600' THEN '출하'
        WHEN CONDITION_CODE = '190' THEN '이상'
        WHEN CONDITION_CODE IN ('950', '952') THEN '폐기'
        ELSE '기타'
    END as status,
    POSITION_USER_NAME as location,
    COUNT(DISTINCT CYLINDER_NO) as qty,
    NOW() as updated_at
FROM 실제_동기화_테이블명
GROUP BY 
    GAS_NAME,
    CAPACITY,
    VALVE_SPEC_NAME,
    CYLINDER_SPEC_NAME,
    USAGE_PLACE,
    status,
    POSITION_USER_NAME;
```

## 5. 검증

VIEW가 정상적으로 작동하는지 확인:

```bash
python manage.py shell
```

```python
from core.repositories.view_repository import ViewRepository

# 인벤토리 VIEW 조회
inventory = ViewRepository.get_inventory_view()
print(f"인벤토리 행 수: {len(inventory)}")

# 용기 리스트 VIEW 조회
cylinders = ViewRepository.get_cylinder_list_view(limit=10)
print(f"용기 리스트 (최대 10개): {len(cylinders)}")
```

## 문제 해결

### 연결 오류
- `.env` 파일의 연결 정보 확인
- PostgreSQL 서버(10.78.30.98:5434) 접근 가능 여부 확인
- 방화벽 설정 확인

### VIEW 생성 오류
- 실제 동기화 테이블명 확인
- 컬럼명 대소문자 확인 (PostgreSQL은 대소문자를 구분할 수 있음)
- `create_postgresql_views` 명령의 출력 로그 확인

### 마이그레이션 오류
- 기존 테이블 충돌 확인
- `python manage.py showmigrations`로 마이그레이션 상태 확인

## 참고

- VIEW는 SSOT(단일 진실 공급원)이므로 절대 수정하지 않습니다
- 동기화 테이블은 읽기 전용으로 취급합니다
- CYNOW 앱 테이블만 Django 마이그레이션으로 관리합니다













