# CYNOW 데이터 아키텍처 설계서

## 1. CYNOW 전용 테이블 설계 (DDL)

### 1.1 EndUser 정책 테이블

```sql
-- EndUser 기본값 설정 테이블
CREATE TABLE cy_enduser_default (
    id SERIAL PRIMARY KEY,
    gas_name VARCHAR(100) NOT NULL,
    capacity NUMERIC,
    valve_spec_code VARCHAR(50),
    cylinder_spec_code VARCHAR(50),
    default_enduser VARCHAR(50) NOT NULL DEFAULT 'SDC',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(gas_name, capacity, valve_spec_code, cylinder_spec_code)
);

CREATE INDEX idx_cy_enduser_default_lookup ON cy_enduser_default(gas_name, capacity, valve_spec_code, cylinder_spec_code) WHERE is_active = TRUE;

-- EndUser 예외 지정 테이블 (기본값과 다른 경우만)
CREATE TABLE cy_enduser_exception (
    id SERIAL PRIMARY KEY,
    cylinder_no VARCHAR(20) NOT NULL UNIQUE,
    enduser VARCHAR(50) NOT NULL,
    reason TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cy_enduser_exception_cylinder ON cy_enduser_exception(cylinder_no) WHERE is_active = TRUE;
```

### 1.2 밸브 표준화(통합) 테이블

```sql
-- 밸브 그룹 정의 테이블
CREATE TABLE cy_valve_group (
    id SERIAL PRIMARY KEY,
    group_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 밸브 → 그룹 매핑 테이블
CREATE TABLE cy_valve_group_mapping (
    id SERIAL PRIMARY KEY,
    valve_spec_code VARCHAR(50) NOT NULL,
    valve_spec_name VARCHAR(200) NOT NULL,
    group_id INTEGER NOT NULL REFERENCES cy_valve_group(id),
    is_primary BOOLEAN DEFAULT FALSE,  -- 그룹의 대표 밸브
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(valve_spec_code, valve_spec_name)
);

CREATE INDEX idx_cy_valve_group_mapping_lookup ON cy_valve_group_mapping(valve_spec_code, valve_spec_name) WHERE is_active = TRUE;
CREATE INDEX idx_cy_valve_group_mapping_group ON cy_valve_group_mapping(group_id) WHERE is_active = TRUE;
```

### 1.3 대시보드 조회용 스냅샷 테이블

```sql
-- 용기 현재 상태 스냅샷 테이블 (대시보드 전용)
CREATE TABLE cy_cylinder_current (
    -- 식별자
    cylinder_no VARCHAR(20) PRIMARY KEY,
    
    -- FCMS Raw 값 (원천 데이터, 감사용)
    raw_gas_name VARCHAR(100),
    raw_capacity NUMERIC,
    raw_valve_spec_code VARCHAR(50),
    raw_valve_spec_name VARCHAR(200),
    raw_cylinder_spec_code VARCHAR(50),
    raw_cylinder_spec_name VARCHAR(200),
    raw_usage_place VARCHAR(50),
    raw_location VARCHAR(100),
    raw_condition_code VARCHAR(10),
    raw_position_user_name VARCHAR(100),
    
    -- CYNOW 정책 적용된 Dashboard 값 (운영/집계용)
    dashboard_gas_name VARCHAR(100),
    dashboard_capacity NUMERIC,
    dashboard_valve_spec_code VARCHAR(50),
    dashboard_valve_spec_name VARCHAR(200),  -- 표준화된 밸브명
    dashboard_valve_group_name VARCHAR(100),  -- 밸브 그룹명
    dashboard_cylinder_spec_code VARCHAR(50),
    dashboard_cylinder_spec_name VARCHAR(200),
    dashboard_usage_place VARCHAR(50),
    dashboard_location VARCHAR(100),
    dashboard_status VARCHAR(20),  -- 변환된 상태명 (보관, 충전 등)
    dashboard_enduser VARCHAR(50),  -- 정책 적용된 enduser
    
    -- 집계/예측용 필드
    cylinder_type_key VARCHAR(32),  -- MD5 해시 (dashboard 값 기준)
    cylinder_type_key_raw VARCHAR(32),  -- MD5 해시 (raw 값 기준, 감사용)
    
    -- 상태/위치 정보
    condition_code VARCHAR(10),
    move_date TIMESTAMP,
    pressure_due_date TIMESTAMP,
    last_event_at TIMESTAMP,
    
    -- 메타데이터
    source_updated_at TIMESTAMP,  -- FCMS에서 마지막 업데이트 시각
    snapshot_updated_at TIMESTAMP DEFAULT NOW(),  -- 스냅샷 갱신 시각
    
    -- 인덱스용 컬럼
    status_category VARCHAR(20),  -- 가용/비가용 분류
    is_available BOOLEAN,  -- 가용 여부 (보관/충전)
    
    -- 인덱스
    CONSTRAINT fk_cylinder_no FOREIGN KEY (cylinder_no) REFERENCES "fcms_cdc"."ma_cylinders"("CYLINDER_NO") ON DELETE CASCADE
);

-- 집계 쿼리 최적화를 위한 인덱스
CREATE INDEX idx_cy_cylinder_current_type_key ON cy_cylinder_current(cylinder_type_key);
CREATE INDEX idx_cy_cylinder_current_status ON cy_cylinder_current(dashboard_status);
CREATE INDEX idx_cy_cylinder_current_enduser ON cy_cylinder_current(dashboard_enduser);
CREATE INDEX idx_cy_cylinder_current_location ON cy_cylinder_current(dashboard_location);
CREATE INDEX idx_cy_cylinder_current_available ON cy_cylinder_current(is_available) WHERE is_available = TRUE;
CREATE INDEX idx_cy_cylinder_current_gas ON cy_cylinder_current(dashboard_gas_name);
CREATE INDEX idx_cy_cylinder_current_updated ON cy_cylinder_current(snapshot_updated_at);

-- 복합 인덱스 (자주 사용되는 조합)
CREATE INDEX idx_cy_cylinder_current_dashboard_lookup ON cy_cylinder_current(
    dashboard_gas_name, 
    dashboard_capacity, 
    dashboard_valve_group_name, 
    dashboard_cylinder_spec_name, 
    dashboard_enduser, 
    dashboard_status
);
```

## 2. cy_cylinder_current 컬럼 구성 상세

### 2.1 Raw 값 (FCMS 원천 데이터)
- `raw_*` 접두사로 시작하는 모든 컬럼
- FCMS에서 직접 가져온 값, 변경 없이 보존
- 감사(audit) 및 이력 추적용

### 2.2 Dashboard 값 (CYNOW 정책 적용)
- `dashboard_*` 접두사로 시작하는 모든 컬럼
- 운영 정책이 적용된 값
- 대시보드/집계/예측에 사용

### 2.3 집계/예측용 필드
- `cylinder_type_key`: Dashboard 값 기준 MD5 해시
  - 그룹화, 집계, 예측 모델 입력값으로 사용
- `cylinder_type_key_raw`: Raw 값 기준 MD5 해시
  - 원천 데이터 추적용
- `status_category`: 상태 카테고리 (가용/비가용)
- `is_available`: 가용 여부 (보관/충전 = TRUE)

## 3. cy_cylinder_current 갱신 전략

### 3.1 CDC 이벤트 기반 증분 Upsert (권장)

```sql
-- CDC 이벤트 처리 함수 (PostgreSQL)
CREATE OR REPLACE FUNCTION sync_cylinder_current()
RETURNS TRIGGER AS $$
DECLARE
    v_gas_name VARCHAR(100);
    v_capacity NUMERIC;
    v_valve_spec_code VARCHAR(50);
    v_valve_spec_name VARCHAR(200);
    v_cylinder_spec_code VARCHAR(50);
    v_cylinder_spec_name VARCHAR(200);
    v_usage_place VARCHAR(50);
    v_location VARCHAR(100);
    v_condition_code VARCHAR(10);
    v_status VARCHAR(20);
    v_enduser VARCHAR(50);
    v_valve_group_name VARCHAR(100);
    v_cylinder_type_key VARCHAR(32);
    v_is_available BOOLEAN;
BEGIN
    -- FCMS 테이블 조인하여 Raw 값 조회
    SELECT 
        COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", ''),
        c."CAPACITY",
        c."VALVE_SPEC_CODE",
        COALESCE(vs."NAME", ''),
        c."CYLINDER_SPEC_CODE",
        COALESCE(cs."NAME", ''),
        COALESCE(c."USE_DEPARTMENT_CODE", ''),
        COALESCE(ls."POSITION_USER_NAME", ''),
        COALESCE(ls."CONDITION_CODE", '')
    INTO 
        v_gas_name, v_capacity, v_valve_spec_code, v_valve_spec_name,
        v_cylinder_spec_code, v_cylinder_spec_name, v_usage_place,
        v_location, v_condition_code
    FROM "fcms_cdc"."ma_cylinders" c
    LEFT JOIN "fcms_cdc"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
    LEFT JOIN "fcms_cdc"."ma_cylinder_specs" cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
    LEFT JOIN "fcms_cdc"."ma_valve_specs" vs ON c."VALVE_SPEC_CODE" = vs."VALVE_SPEC_CODE"
    LEFT JOIN "fcms_cdc"."tr_latest_cylinder_statuses" ls ON c."CYLINDER_NO" = ls."CYLINDER_NO"
    WHERE c."CYLINDER_NO" = NEW."CYLINDER_NO";
    
    -- 상태 코드 → 상태명 변환
    v_status := CASE 
        WHEN v_condition_code IN ('100', '102') THEN '보관'
        WHEN v_condition_code IN ('210', '220') THEN '충전'
        WHEN v_condition_code = '420' THEN '분석'
        WHEN v_condition_code = '500' THEN '창입'
        WHEN v_condition_code = '600' THEN '출하'
        WHEN v_condition_code = '190' THEN '이상'
        WHEN v_condition_code IN ('950', '952') THEN '폐기'
        ELSE '기타'
    END;
    
    -- EndUser 결정 (예외 우선, 기본값 차순)
    SELECT COALESCE(
        (SELECT enduser FROM cy_enduser_exception WHERE cylinder_no = NEW."CYLINDER_NO" AND is_active = TRUE),
        (SELECT default_enduser FROM cy_enduser_default 
         WHERE gas_name = v_gas_name 
           AND (capacity IS NULL OR capacity = v_capacity)
           AND (valve_spec_code IS NULL OR valve_spec_code = v_valve_spec_code)
           AND (cylinder_spec_code IS NULL OR cylinder_spec_code = v_cylinder_spec_code)
           AND is_active = TRUE
         ORDER BY 
           CASE WHEN capacity IS NOT NULL THEN 1 ELSE 2 END,
           CASE WHEN valve_spec_code IS NOT NULL THEN 1 ELSE 2 END,
           CASE WHEN cylinder_spec_code IS NOT NULL THEN 1 ELSE 2 END
         LIMIT 1),
        'SDC'  -- 최종 기본값
    ) INTO v_enduser;
    
    -- 밸브 그룹 조회
    SELECT vg.group_name INTO v_valve_group_name
    FROM cy_valve_group_mapping vgm
    JOIN cy_valve_group vg ON vgm.group_id = vg.id
    WHERE vgm.valve_spec_code = v_valve_spec_code
      AND vgm.valve_spec_name = v_valve_spec_name
      AND vgm.is_active = TRUE
      AND vg.is_active = TRUE
    LIMIT 1;
    
    -- Dashboard 밸브명 결정 (그룹이 있으면 그룹의 primary 밸브, 없으면 원본)
    IF v_valve_group_name IS NOT NULL THEN
        SELECT vgm2.valve_spec_name INTO v_valve_spec_name
        FROM cy_valve_group_mapping vgm2
        JOIN cy_valve_group vg2 ON vgm2.group_id = vg2.id
        WHERE vg2.group_name = v_valve_group_name
          AND vgm2.is_primary = TRUE
          AND vgm2.is_active = TRUE
        LIMIT 1;
    END IF;
    
    -- cylinder_type_key 생성 (Dashboard 값 기준)
    v_cylinder_type_key := MD5(
        COALESCE(v_gas_name, '') || '|' ||
        COALESCE(CAST(v_capacity AS TEXT), '') || '|' ||
        COALESCE(v_valve_group_name, v_valve_spec_name, '') || '|' ||
        COALESCE(v_cylinder_spec_name, '') || '|' ||
        COALESCE(v_enduser, '')
    );
    
    -- 가용 여부
    v_is_available := v_status IN ('보관', '충전');
    
    -- Upsert
    INSERT INTO cy_cylinder_current (
        cylinder_no,
        raw_gas_name, raw_capacity, raw_valve_spec_code, raw_valve_spec_name,
        raw_cylinder_spec_code, raw_cylinder_spec_name, raw_usage_place,
        raw_location, raw_condition_code, raw_position_user_name,
        dashboard_gas_name, dashboard_capacity, dashboard_valve_spec_code,
        dashboard_valve_spec_name, dashboard_valve_group_name,
        dashboard_cylinder_spec_code, dashboard_cylinder_spec_name,
        dashboard_usage_place, dashboard_location, dashboard_status,
        dashboard_enduser, cylinder_type_key, condition_code,
        status_category, is_available, source_updated_at
    ) VALUES (
        NEW."CYLINDER_NO",
        v_gas_name, v_capacity, v_valve_spec_code, v_valve_spec_name,
        v_cylinder_spec_code, v_cylinder_spec_name, v_usage_place,
        v_location, v_condition_code, v_location,
        v_gas_name, v_capacity, v_valve_spec_code,
        COALESCE(v_valve_spec_name, ''), v_valve_group_name,
        v_cylinder_spec_code, v_cylinder_spec_name,
        v_usage_place, v_location, v_status,
        v_enduser, v_cylinder_type_key, v_condition_code,
        CASE WHEN v_is_available THEN '가용' ELSE '비가용' END,
        v_is_available, NOW()
    )
    ON CONFLICT (cylinder_no) DO UPDATE SET
        raw_gas_name = EXCLUDED.raw_gas_name,
        raw_capacity = EXCLUDED.raw_capacity,
        raw_valve_spec_code = EXCLUDED.raw_valve_spec_code,
        raw_valve_spec_name = EXCLUDED.raw_valve_spec_name,
        raw_cylinder_spec_code = EXCLUDED.raw_cylinder_spec_code,
        raw_cylinder_spec_name = EXCLUDED.raw_cylinder_spec_name,
        raw_usage_place = EXCLUDED.raw_usage_place,
        raw_location = EXCLUDED.raw_location,
        raw_condition_code = EXCLUDED.raw_condition_code,
        raw_position_user_name = EXCLUDED.raw_position_user_name,
        dashboard_gas_name = EXCLUDED.dashboard_gas_name,
        dashboard_capacity = EXCLUDED.dashboard_capacity,
        dashboard_valve_spec_code = EXCLUDED.dashboard_valve_spec_code,
        dashboard_valve_spec_name = EXCLUDED.dashboard_valve_spec_name,
        dashboard_valve_group_name = EXCLUDED.dashboard_valve_group_name,
        dashboard_cylinder_spec_code = EXCLUDED.dashboard_cylinder_spec_code,
        dashboard_cylinder_spec_name = EXCLUDED.dashboard_cylinder_spec_name,
        dashboard_usage_place = EXCLUDED.raw_usage_place,
        dashboard_location = EXCLUDED.dashboard_location,
        dashboard_status = EXCLUDED.dashboard_status,
        dashboard_enduser = EXCLUDED.dashboard_enduser,
        cylinder_type_key = EXCLUDED.cylinder_type_key,
        condition_code = EXCLUDED.condition_code,
        status_category = EXCLUDED.status_category,
        is_available = EXCLUDED.is_available,
        source_updated_at = EXCLUDED.source_updated_at,
        snapshot_updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger 설정 (ma_cylinders 변경 시)
CREATE TRIGGER trigger_sync_cylinder_current_cylinders
AFTER INSERT OR UPDATE ON "fcms_cdc"."ma_cylinders"
FOR EACH ROW EXECUTE FUNCTION sync_cylinder_current();

-- Trigger 설정 (tr_latest_cylinder_statuses 변경 시)
CREATE TRIGGER trigger_sync_cylinder_current_status
AFTER INSERT OR UPDATE ON "fcms_cdc"."tr_latest_cylinder_statuses"
FOR EACH ROW EXECUTE FUNCTION sync_cylinder_current();
```

### 3.2 배치 갱신 방식 (대안)

```python
# Django Management Command: core/management/commands/sync_cylinder_current.py
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

class Command(BaseCommand):
    help = 'cy_cylinder_current 스냅샷 테이블 전체 갱신'
    
    def add_arguments(self, parser):
        parser.add_argument('--incremental', action='store_true', help='증분 갱신 (최근 1시간)')
    
    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            if options['incremental']:
                # 증분 갱신: 최근 1시간 내 변경된 용기만
                cutoff_time = timezone.now() - timedelta(hours=1)
                cursor.execute("""
                    WITH updated_cylinders AS (
                        SELECT DISTINCT c."CYLINDER_NO"
                        FROM "fcms_cdc"."ma_cylinders" c
                        LEFT JOIN "fcms_cdc"."tr_latest_cylinder_statuses" ls 
                            ON c."CYLINDER_NO" = ls."CYLINDER_NO"
                        WHERE c."UPDATE_DATETIME" >= %s
                           OR ls."MOVE_DATE" >= %s
                    )
                    SELECT "CYLINDER_NO" FROM updated_cylinders
                """, [cutoff_time, cutoff_time])
            else:
                # 전체 갱신
                cursor.execute('SELECT "CYLINDER_NO" FROM "fcms_cdc"."ma_cylinders"')
            
            cylinder_nos = [row[0] for row in cursor.fetchall()]
            
            # 각 용기에 대해 sync_cylinder_current 함수 호출
            for cylinder_no in cylinder_nos:
                cursor.execute("""
                    SELECT sync_cylinder_current_single(%s)
                """, [cylinder_no])
            
            self.stdout.write(self.style.SUCCESS(f'{len(cylinder_nos)}개 용기 갱신 완료'))
```

## 4. 조회/집계 시 적용 규칙

### 4.1 EndUser 결정 우선순위

1. **예외 테이블 확인** (`cy_enduser_exception`)
   - `cylinder_no`로 직접 매칭
   - `is_active = TRUE`인 것만
   - 매칭되면 해당 `enduser` 사용

2. **기본값 테이블 확인** (`cy_enduser_default`)
   - `gas_name`, `capacity`, `valve_spec_code`, `cylinder_spec_code`로 매칭
   - NULL 값은 와일드카드로 처리 (부분 매칭)
   - 가장 구체적인 매칭 우선 (NULL이 적은 것)
   - `is_active = TRUE`인 것만

3. **최종 기본값**
   - 위에서 매칭되지 않으면 `'SDC'` 사용

### 4.2 밸브 Raw vs Dashboard 구분

- **Raw 값**: `raw_valve_spec_name` (FCMS 원본, 감사용)
- **Dashboard 값**: `dashboard_valve_spec_name` (표준화된 값)
- **그룹화/집계**: `dashboard_valve_group_name` 또는 `dashboard_valve_spec_name` 사용
- **원천 추적**: `raw_valve_spec_name`으로 원본 확인

### 4.3 집계 쿼리 예시

```sql
-- 용기종류별 집계 (Dashboard 값 기준)
SELECT 
    cylinder_type_key,
    dashboard_gas_name,
    dashboard_capacity,
    dashboard_valve_group_name,
    dashboard_cylinder_spec_name,
    dashboard_enduser,
    dashboard_status,
    dashboard_location,
    COUNT(*) as qty,
    SUM(CASE WHEN is_available THEN 1 ELSE 0 END) as available_qty
FROM cy_cylinder_current
GROUP BY 
    cylinder_type_key,
    dashboard_gas_name,
    dashboard_capacity,
    dashboard_valve_group_name,
    dashboard_cylinder_spec_name,
    dashboard_enduser,
    dashboard_status,
    dashboard_location;
```

## 5. 마이그레이션 절차

### 5.1 단계 1: CYNOW 정책 테이블 생성

```bash
# 1. DDL 실행
psql -h 10.78.30.98 -p 5434 -U postgres -d cycy_db -f create_cynow_policy_tables.sql

# 2. 초기 데이터 입력
python manage.py load_enduser_defaults  # 기본값 설정
python manage.py load_valve_groups      # 밸브 그룹 설정
```

### 5.2 단계 2: cy_cylinder_current 테이블 생성 및 초기 데이터 로드

```bash
# 1. 테이블 생성
psql -h 10.78.30.98 -p 5434 -U postgres -d cycy_db -f create_cy_cylinder_current.sql

# 2. 초기 전체 스냅샷 생성
python manage.py sync_cylinder_current

# 3. 데이터 검증
python manage.py verify_cylinder_current
```

### 5.3 단계 3: Trigger 설정 (CDC 기반 자동 갱신)

```bash
# Trigger 및 함수 생성
psql -h 10.78.30.98 -p 5434 -U postgres -d cycy_db -f create_sync_triggers.sql
```

### 5.4 단계 4: Repository 레이어 수정

```python
# core/repositories/cylinder_repository.py (신규)
from django.db import connection
from typing import List, Dict, Optional

class CylinderRepository:
    """cy_cylinder_current 테이블 조회 전용 Repository"""
    
    @staticmethod
    def get_inventory_summary(filters: Optional[Dict] = None) -> List[Dict]:
        """용기종류별 집계 (대시보드용)"""
        with connection.cursor() as cursor:
            query = """
                SELECT 
                    cylinder_type_key,
                    dashboard_gas_name as gas_name,
                    dashboard_capacity as capacity,
                    dashboard_valve_group_name as valve_spec,
                    dashboard_cylinder_spec_name as cylinder_spec,
                    dashboard_enduser as usage_place,
                    dashboard_status as status,
                    dashboard_location as location,
                    COUNT(*) as qty,
                    SUM(CASE WHEN is_available THEN 1 ELSE 0 END) as available_qty
                FROM cy_cylinder_current
            """
            # 필터 적용...
            cursor.execute(query)
            # 결과 반환...
    
    @staticmethod
    def get_cylinder_list(filters: Optional[Dict] = None, limit: Optional[int] = None) -> List[Dict]:
        """개별 용기 리스트"""
        # cy_cylinder_current에서 조회
        pass
```

### 5.5 단계 5: ViewRepository → CylinderRepository 전환

```python
# dashboard/views.py 수정
# 기존: ViewRepository.get_inventory_view()
# 변경: CylinderRepository.get_inventory_summary()
```

### 5.6 단계 6: 기존 VIEW 제거 (선택사항)

```sql
-- 검증 완료 후 기존 VIEW 제거
DROP VIEW IF EXISTS vw_cynow_inventory CASCADE;
DROP VIEW IF EXISTS vw_cynow_cylinder_list CASCADE;
```

## 6. 초기 데이터 로드 스크립트

```python
# core/management/commands/load_enduser_defaults.py
from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'EndUser 기본값 설정'
    
    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # CF4 YC 440L 기본값: SDC
            cursor.execute("""
                INSERT INTO cy_enduser_default 
                (gas_name, capacity, default_enduser, is_active)
                VALUES ('CF4', 440, 'SDC', TRUE)
                ON CONFLICT DO NOTHING
            """)
            
            # 예외: LGD 납품 전용 29병
            # (용기번호 리스트는 별도로 입력 필요)
            self.stdout.write(self.style.SUCCESS('EndUser 기본값 설정 완료'))
```

```python
# core/management/commands/load_valve_groups.py
from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = '밸브 그룹 설정'
    
    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # COS CGA330 그룹 생성
            cursor.execute("""
                INSERT INTO cy_valve_group (group_name, description, is_active)
                VALUES ('COS_CGA330', 'COS CGA330 통합 그룹 (NERIKI/HAMAI)', TRUE)
                ON CONFLICT (group_name) DO UPDATE SET is_active = TRUE
                RETURNING id
            """)
            group_id = cursor.fetchone()[0]
            
            # NERIKI를 primary로 설정
            cursor.execute("""
                INSERT INTO cy_valve_group_mapping 
                (valve_spec_code, valve_spec_name, group_id, is_primary, is_active)
                VALUES 
                ('VALVE_CODE_1', 'SUS general Y CGA330 Y NERIKI', %s, TRUE, TRUE),
                ('VALVE_CODE_2', 'SUS general Y CGA330 Y HAMAI', %s, FALSE, TRUE)
                ON CONFLICT (valve_spec_code, valve_spec_name) DO UPDATE 
                SET group_id = EXCLUDED.group_id, is_active = TRUE
            """, [group_id, group_id])
            
            self.stdout.write(self.style.SUCCESS('밸브 그룹 설정 완료'))
```

## 7. 성능 최적화

### 7.1 인덱스 전략
- `cylinder_type_key`: 집계 쿼리 최적화
- `dashboard_status`, `is_available`: 상태별 필터링
- 복합 인덱스: 자주 사용되는 조합

### 7.2 배치 갱신 주기
- **실시간**: Trigger 기반 (권장)
- **배치**: 5분 간격 증분 갱신 (대안)
- **전체**: 일 1회 (정합성 검증용)

## 8. 모니터링

```sql
-- 스냅샷 갱신 상태 확인
SELECT 
    COUNT(*) as total_cylinders,
    COUNT(CASE WHEN snapshot_updated_at > NOW() - INTERVAL '1 hour' THEN 1 END) as updated_last_hour,
    MAX(snapshot_updated_at) as last_update_time
FROM cy_cylinder_current;

-- 정책 적용 현황
SELECT 
    dashboard_enduser,
    COUNT(*) as qty
FROM cy_cylinder_current
GROUP BY dashboard_enduser;
```

