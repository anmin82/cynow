# CYNOW 배포 가이드

## Phase 1: 개발 환경 (현재)

현재 SQLite 기반으로 개발이 완료되었습니다.

### 실행 방법
```bash
# 가상환경 활성화
.\venv\Scripts\Activate.ps1  # Windows PowerShell
source venv/bin/activate      # Linux/Mac

# 서버 실행
python manage.py runserver
```

### 정기 스냅샷 설정 (테스트)
```bash
# 수동 실행
python manage.py take_daily_snapshot
```

---

## Phase 2: PostgreSQL 전환 (운영 환경)

### 1. PostgreSQL 연결 설정

`.env` 파일 수정:
```env
DB_ENGINE=postgresql
DB_NAME=cynow
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=10.78.30.98
DB_PORT=5434
```

### 2. VIEW 생성

PostgreSQL에서 실제 동기화 테이블을 기반으로 VIEW를 생성해야 합니다.

**vw_cynow_inventory VIEW 예시:**
```sql
CREATE VIEW vw_cynow_inventory AS
SELECT 
    -- cylinder_type_key는 Python에서 생성 (MD5 해시)
    c.GAS_NAME as gas_name,
    NULL as capacity,  -- TODO: 실제 컬럼명으로 변경
    c.VALVE_SPEC_NAME as valve_spec,
    c.CYLINDER_SPEC_NAME as cylinder_spec,
    NULL as usage_place,  -- TODO: 실제 컬럼명으로 변경
    CASE 
        WHEN c.CONDITION_CODE IN ('100', '102') THEN '보관'
        WHEN c.CONDITION_CODE IN ('210', '220') THEN '충전'
        WHEN c.CONDITION_CODE = '420' THEN '분석'
        WHEN c.CONDITION_CODE = '500' THEN '창입'
        WHEN c.CONDITION_CODE = '600' THEN '출하'
        WHEN c.CONDITION_CODE = '190' THEN '이상'
        WHEN c.CONDITION_CODE IN ('950', '952') THEN '폐기'
        ELSE '기타'
    END as status,
    c.POSITION_USER_NAME as location,
    COUNT(DISTINCT c.CYLINDER_NO) as qty,
    NOW() as updated_at
FROM 실제_동기화_테이블명 c
GROUP BY 
    c.GAS_NAME,
    c.VALVE_SPEC_NAME,
    c.CYLINDER_SPEC_NAME,
    status,
    c.POSITION_USER_NAME;
```

**참고**: 실제 테이블명은 Debezium/JDBC Sink 설정에 따라 다를 수 있습니다.

### 3. Repository 수정

`core/repositories/view_repository.py`에서 PostgreSQL용 쿼리로 수정:
- SQLite: `?` 파라미터 바인딩
- PostgreSQL: `%s` 파라미터 바인딩 (또는 Django ORM 사용)

### 4. 정기 스냅샷 Cron 설정

```bash
# crontab 편집
crontab -e

# 매일 00:05 (KST) 실행
5 0 * * * /path/to/venv/bin/python /path/to/manage.py take_daily_snapshot
```

### 5. 보안 설정

운영 환경에서는 `.env`에서 다음 설정을 변경:
```env
DEBUG=False
SECRET_KEY=강력한_랜덤_문자열
ALLOWED_HOSTS=your-domain.com,10.78.30.98
```

---

## 데이터 마이그레이션

CYNOW 앱 테이블만 마이그레이션:
- `plan_forecast_monthly`
- `plan_scheduled_monthly`
- `hist_inventory_snapshot`
- `hist_snapshot_request`
- `report_export_log`

VIEW는 PostgreSQL에서 직접 생성하므로 마이그레이션 불필요.

---

## 문제 해결

### VIEW 조회 오류
- `core/repositories/view_repository.py`에서 DB 엔진에 따라 파라미터 바인딩 방식 변경 필요

### Timezone 경고
- `USE_TZ = True` 설정 확인
- 모든 datetime은 `timezone.now()` 사용

### 권한 오류
- `python manage.py create_permissions` 실행 확인
- 사용자에게 `cynow.can_edit_plan` 권한 부여

