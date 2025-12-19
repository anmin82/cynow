# VIEW → 스냅샷 테이블 마이그레이션 가이드

## 마이그레이션 절차

### 1단계: 정책 테이블 생성

```bash
# PostgreSQL에 연결하여 DDL 실행
psql -h 10.78.30.98 -p 5434 -U postgres -d cycy_db -f sql/create_cynow_policy_tables.sql
```

### 2단계: 초기 정책 데이터 입력

```bash
# EndUser 기본값 설정
python manage.py load_enduser_defaults

# 밸브 그룹 설정
python manage.py load_valve_groups
```

### 3단계: cy_cylinder_current 테이블 생성

```bash
# 테이블 및 인덱스 생성
psql -h 10.78.30.98 -p 5434 -U postgres -d cycy_db -f sql/create_cy_cylinder_current.sql
```

### 4단계: 초기 스냅샷 생성

```bash
# 전체 용기 스냅샷 생성 (처음 1회)
python manage.py sync_cylinder_current

# 검증
python manage.py verify_cylinder_current
```

### 5단계: Trigger 설정 (자동 동기화)

```bash
# Trigger 및 함수 생성
psql -h 10.78.30.98 -p 5434 -U postgres -d cycy_db -f sql/create_sync_triggers.sql
```

### 6단계: Repository 레이어 전환

```python
# dashboard/views.py 수정
# 기존: ViewRepository.get_inventory_view()
# 변경: CylinderRepository.get_inventory_summary()

# cylinders/views.py 수정
# 기존: ViewRepository.get_cylinder_list_view()
# 변경: CylinderRepository.get_cylinder_list()
```

### 7단계: 검증 및 모니터링

```sql
-- 스냅샷 상태 확인
SELECT 
    COUNT(*) as total,
    COUNT(CASE WHEN snapshot_updated_at > NOW() - INTERVAL '1 hour' THEN 1 END) as updated_last_hour,
    MAX(snapshot_updated_at) as last_update
FROM cy_cylinder_current;

-- 정책 적용 현황
SELECT 
    dashboard_enduser,
    COUNT(*) as qty
FROM cy_cylinder_current
GROUP BY dashboard_enduser
ORDER BY qty DESC;
```

### 8단계: 기존 VIEW 제거 (선택사항)

```sql
-- 검증 완료 후
DROP VIEW IF EXISTS vw_cynow_inventory CASCADE;
DROP VIEW IF EXISTS vw_cynow_cylinder_list CASCADE;
```

## 롤백 절차

문제 발생 시:

```sql
-- Trigger 제거
DROP TRIGGER IF EXISTS trigger_sync_cylinder_current_cylinders ON "fcms_cdc"."ma_cylinders";
DROP TRIGGER IF EXISTS trigger_sync_cylinder_current_status ON "fcms_cdc"."tr_latest_cylinder_statuses";

-- 함수 제거
DROP FUNCTION IF EXISTS sync_cylinder_current_single(VARCHAR);
DROP FUNCTION IF EXISTS trigger_sync_cylinder_current_cylinders();
DROP FUNCTION IF EXISTS trigger_sync_cylinder_current_status();

-- 기존 VIEW로 복구
-- (create_postgresql_views 명령어 재실행)
```
