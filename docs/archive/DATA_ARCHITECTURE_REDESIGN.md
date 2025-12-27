# CYNOW 데이터 아키텍처 재설계

## 1. CYNOW 전용 테이블 설계 (DDL)

### 1.1 EndUser 정책 테이블

```sql
-- EndUser 기본값 및 예외 정책 테이블
CREATE TABLE cy_enduser_policy (
    id SERIAL PRIMARY KEY,
    -- 기본값 정의 (모든 용기종류에 적용)
    default_enduser_code VARCHAR(50) NOT NULL DEFAULT 'SDC',
    default_enduser_name VARCHAR(100) NOT NULL DEFAULT 'SDC',
    -- 예외 규칙 (특정 용기종류만 지정)
    cylinder_type_key VARCHAR(32),  -- NULL이면 기본값 적용
    gas_name VARCHAR(100),
    capacity NUMERIC,
    valve_spec VARCHAR(180),
    cylinder_spec VARCHAR(180),
    usage_place VARCHAR(100),
    -- 예외 enduser
    exception_enduser_code VARCHAR(50),
    exception_enduser_name VARCHAR(100),
    -- 메타데이터
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(50),
    updated_by VARCHAR(50),
    -- 제약조건
    CONSTRAINT chk_enduser_policy CHECK (
        (cylinder_type_key IS NULL AND gas_name IS NULL) OR
        (cylinder_type_key IS NOT NULL)
    )
);

CREATE INDEX idx_enduser_policy_type_key ON cy_enduser_policy(cylinder_type_key) WHERE is_active = TRUE;
CREATE INDEX idx_enduser_policy_gas ON cy_enduser_policy(gas_name, capacity) WHERE is_active = TRUE AND cylinder_type_key IS NULL;

COMMENT ON TABLE cy_enduser_policy IS 'EndUser 전용 분리 정책: 기본값(SDC) + 예외 규칙';
COMMENT ON COLUMN cy_enduser_policy.cylinder_type_key IS 'NULL이면 기본값, 값이 있으면 해당 용기종류에만 예외 적용';
COMMENT ON COLUMN cy_enduser_policy.default_enduser_code IS '기본 EndUser 코드 (대부분 용기에 적용)';
```

### 1.2 밸브 표준화(통합) 테이블

```sql
-- 밸브 표준화/통합 정책 테이블
CREATE TABLE cy_valve_alias (
    id SERIAL PRIMARY KEY,
    -- 원본 밸브 스펙 (FCMS raw 값)
    raw_valve_spec VARCHAR(180) NOT NULL,
    -- 표준화된 밸브 스펙 (대시보드 표시용)
    standard_valve_spec VARCHAR(180) NOT NULL,
    -- 밸브 그룹 코드 (통합 그룹 식별)
    valve_group_code VARCHAR(50),
    -- 메타데이터
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,  -- 우선순위 (낮을수록 우선)
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    -- 제약조건
    CONSTRAINT uq_valve_alias_raw UNIQUE(raw_valve_spec, is_active) WHERE is_active = TRUE
);

CREATE INDEX idx_valve_alias_raw ON cy_valve_alias(raw_valve_spec) WHERE is_active = TRUE;
CREATE INDEX idx_valve_alias_standard ON cy_valve_alias(standard_valve_spec) WHERE is_active = TRUE;

COMMENT ON TABLE cy_valve_alias IS '밸브 표준화 정책: NERIKI/HAMAI → CGA330 통합 등';
COMMENT ON COLUMN cy_valve_alias.raw_valve_spec IS 'FCMS 원본 밸브 스펙 (감사용)';
COMMENT ON COLUMN cy_valve_alias.standard_valve_spec IS '대시보드 표시용 표준 밸브 스펙';
```

### 1.3 대시보드 조회용 스냅샷 테이블

```sql
-- 용기 현재 상태 스냅샷 테이블 (대시보드 전용)
CREATE TABLE cy_cylinder_current (
    -- 식별자
    cylinder_no VARCHAR(12) PRIMARY KEY,
    
    -- ===== FCMS Raw 값 (감사/이력용, 변경 불가) =====
    raw_gas_name VARCHAR(100),
    raw_capacity NUMERIC,
    raw_valve_spec VARCHAR(180),
    raw_cylinder_spec VARCHAR(180),
    raw_usage_place VARCHAR(100),
    raw_location VARCHAR(90),
    raw_condition_code VARCHAR(10),
    raw_position_user_name VARCHAR(90),
    raw_move_date TIMESTAMP,
    raw_withstand_pressure_mainte_date TIMESTAMP,
    
    -- ===== CYNOW Dashboard 값 (정책 적용) =====
    -- 가스 정보
    dashboard_gas_name VARCHAR(100),
    dashboard_capacity NUMERIC,
    
    -- 밸브 정보 (표준화 적용)
    dashboard_valve_spec VARCHAR(180),  -- 표준화된 밸브 스펙
    dashboard_valve_format VARCHAR(50),  -- CGA330 등
    dashboard_valve_material VARCHAR(50),  -- SUS, BRASS 등
    
    -- 용기 정보
    dashboard_cylinder_spec VARCHAR(180),
    dashboard_cylinder_format VARCHAR(50),  -- BN, YC 등
    dashboard_cylinder_material VARCHAR(50),  -- SUS, Mn-St 등
    
    -- EndUser 정보 (정책 적용)
    dashboard_enduser_code VARCHAR(50),
    dashboard_enduser_name VARCHAR(100),
    dashboard_usage_place VARCHAR(100),  -- location + usage_place 조합
    
    -- 상태 정보
    dashboard_status VARCHAR(20),  -- 보관, 충전, 분석 등
    dashboard_location VARCHAR(90),  -- 번역 적용된 위치
    
    -- 용기종류 키 (정책 적용 후)
    dashboard_cylinder_type_key VARCHAR(32),  -- MD5 해시
    
    -- 날짜 정보
    dashboard_pressure_due_date TIMESTAMP,
    dashboard_last_event_at TIMESTAMP,
    
    -- ===== 집계/예측용 파생 필드 =====
    is_available BOOLEAN,  -- 가용 여부 (보관/충전)
    available_days INTEGER,  -- 가용일수 (예측용)
    risk_level VARCHAR(10),  -- HIGH, MEDIUM, LOW, NORMAL
    
    -- ===== 메타데이터 =====
    source_updated_at TIMESTAMP,  -- FCMS 원본 데이터 갱신 시각
    snapshot_updated_at TIMESTAMP DEFAULT NOW(),  -- 스냅샷 갱신 시각
    policy_version INTEGER DEFAULT 1,  -- 정책 버전 (정책 변경 추적용)
    
    -- ===== 인덱스용 컬럼 =====
    dashboard_gas_name_lower VARCHAR(100) GENERATED ALWAYS AS (LOWER(dashboard_gas_name)) STORED,
    dashboard_status_lower VARCHAR(20) GENERATED ALWAYS AS (LOWER(dashboard_status)) STORED
);

-- 인덱스
CREATE INDEX idx_cy_current_type_key ON cy_cylinder_current(dashboard_cylinder_type_key);
CREATE INDEX idx_cy_current_gas ON cy_cylinder_current(dashboard_gas_name_lower);
CREATE INDEX idx_cy_current_status ON cy_cylinder_current(dashboard_status_lower);
CREATE INDEX idx_cy_current_enduser ON cy_cylinder_current(dashboard_enduser_code);
CREATE INDEX idx_cy_current_location ON cy_cylinder_current(dashboard_location);
CREATE INDEX idx_cy_current_available ON cy_cylinder_current(is_available) WHERE is_available = TRUE;
CREATE INDEX idx_cy_current_updated ON cy_cylinder_current(snapshot_updated_at);

COMMENT ON TABLE cy_cylinder_current IS '용기 현재 상태 스냅샷 (대시보드 조회 전용)';
COMMENT ON COLUMN cy_cylinder_current.raw_* IS 'FCMS 원본 값 (감사/이력용, 변경 불가)';
COMMENT ON COLUMN cy_cylinder_current.dashboard_* IS 'CYNOW 정책 적용된 값 (대시보드 표시용)';
COMMENT ON COLUMN cy_cylinder_current.dashboard_cylinder_type_key IS '정책 적용 후 생성된 용기종류 키 (enduser 포함)';
```

---

## 2. cy_cylinder_current 컬럼 구성 상세

### 2.1 FCMS Raw 값 (감사/이력용)

| 컬럼 | 설명 | 소스 |
|------|------|------|
| `raw_gas_name` | 원본 가스명 | `ma_items.DISPLAY_NAME` |
| `raw_capacity` | 원본 용량 | `ma_cylinders.CAPACITY` |
| `raw_valve_spec` | 원본 밸브 스펙 | `ma_valve_specs.NAME` (전체) |
| `raw_cylinder_spec` | 원본 용기 스펙 | `ma_cylinder_specs.NAME` (전체) |
| `raw_usage_place` | 원본 사용처 코드 | `ma_cylinders.USE_DEPARTMENT_CODE` |
| `raw_location` | 원본 위치 | `tr_latest_cylinder_statuses.POSITION_USER_NAME` |
| `raw_condition_code` | 원본 상태 코드 | `tr_latest_cylinder_statuses.CONDITION_CODE` |
| `raw_position_user_name` | 원본 위치 사용자명 | `tr_latest_cylinder_statuses.POSITION_USER_NAME` |
| `raw_move_date` | 원본 이동일시 | `tr_latest_cylinder_statuses.MOVE_DATE` |
| `raw_withstand_pressure_mainte_date` | 원본 내압 유지일 | `ma_cylinders.WITHSTAND_PRESSURE_MAINTE_DATE` |

**원칙**: Raw 값은 FCMS에서 온 그대로 저장, 절대 변경하지 않음.

### 2.2 CYNOW Dashboard 값 (정책 적용)

| 컬럼 | 설명 | 정책 적용 |
|------|------|----------|
| `dashboard_gas_name` | 표시용 가스명 | 번역 정책 |
| `dashboard_capacity` | 표시용 용량 | Raw와 동일 (정책 없음) |
| `dashboard_valve_spec` | 표준화된 밸브 스펙 | `cy_valve_alias` 적용 |
| `dashboard_valve_format` | 밸브 형식 | 파싱 (CGA330 등) |
| `dashboard_valve_material` | 밸브 재질 | 파싱 (SUS 등) |
| `dashboard_cylinder_spec` | 표시용 용기 스펙 | 번역 정책 |
| `dashboard_cylinder_format` | 용기 형식 | 파싱 (BN, YC) |
| `dashboard_cylinder_material` | 용기 재질 | 파싱 (SUS 등) |
| `dashboard_enduser_code` | EndUser 코드 | `cy_enduser_policy` 적용 |
| `dashboard_enduser_name` | EndUser 명 | `cy_enduser_policy` 적용 |
| `dashboard_usage_place` | 사용처 (조합) | `location + usage_place` |
| `dashboard_status` | 상태명 | `CONDITION_CODE` → 상태명 변환 |
| `dashboard_location` | 위치 (번역) | 번역 정책 |
| `dashboard_cylinder_type_key` | 용기종류 키 | 정책 적용 후 MD5 생성 |

**핵심**: `dashboard_cylinder_type_key`는 **enduser를 포함**하여 생성
```
MD5(gas_name|capacity|valve_spec(표준화)|cylinder_spec|usage_place|enduser_code)
```

### 2.3 집계/예측용 파생 필드

| 컬럼 | 설명 | 계산 로직 |
|------|------|----------|
| `is_available` | 가용 여부 | `dashboard_status IN ('보관', '충전')` |
| `available_days` | 가용일수 | 향후 예측 알고리즘 적용 |
| `risk_level` | 위험도 | 가용수량 비율 기반 계산 |

---

## 3. cy_cylinder_current 갱신 전략

### 3.1 CDC 이벤트 기반 증분 Upsert (권장)

**전제조건**: Debezium CDC에서 `ma_cylinders`, `tr_latest_cylinder_statuses` 변경 시 Kafka 이벤트 발생

#### Django Management Command 방식

```python
# core/management/commands/sync_cylinder_snapshot.py
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from core.utils.view_helper import parse_cylinder_spec, parse_valve_spec, parse_usage_place
from core.utils.cylinder_type import generate_cylinder_type_key
import hashlib

class Command(BaseCommand):
    help = 'cy_cylinder_current 스냅샷 증분 갱신 (CDC 이벤트 기반)'
    
    def add_arguments(self, parser):
        parser.add_argument('--full', action='store_true', help='전체 재생성')
        parser.add_argument('--cylinder-no', type=str, help='특정 용기만 갱신')
    
    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            if options['full']:
                self.full_sync(cursor)
            elif options['cylinder_no']:
                self.sync_single(cursor, options['cylinder_no'])
            else:
                self.incremental_sync(cursor)
    
    def incremental_sync(self, cursor):
        """증분 갱신: VIEW와 스냅샷 비교하여 변경된 것만 업데이트"""
        # 1. VIEW에서 최신 데이터 조회
        cursor.execute("""
            SELECT 
                c."CYLINDER_NO",
                COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') as gas_name,
                c."CAPACITY",
                COALESCE(vs."NAME", '') as valve_spec,
                COALESCE(cs."NAME", '') as cylinder_spec,
                COALESCE(c."USE_DEPARTMENT_CODE", '') as usage_place,
                COALESCE(ls."POSITION_USER_NAME", '') as location,
                ls."CONDITION_CODE",
                ls."MOVE_DATE",
                c."WITHSTAND_PRESSURE_MAINTE_DATE",
                GREATEST(
                    COALESCE(c."UPDATE_DATETIME", c."ADD_DATETIME"),
                    COALESCE(ls."MOVE_DATE", NOW())
                ) as source_updated_at
            FROM "fcms_cdc"."ma_cylinders" c
            LEFT JOIN "fcms_cdc"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
            LEFT JOIN "fcms_cdc"."ma_cylinder_specs" cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
            LEFT JOIN "fcms_cdc"."ma_valve_specs" vs ON c."VALVE_SPEC_CODE" = vs."VALVE_SPEC_CODE"
            LEFT JOIN "fcms_cdc"."tr_latest_cylinder_statuses" ls ON c."CYLINDER_NO" = ls."CYLINDER_NO"
            WHERE c."CYLINDER_NO" IN (
                SELECT cylinder_no FROM cy_cylinder_current
                WHERE snapshot_updated_at < NOW() - INTERVAL '5 minutes'
                OR source_updated_at > snapshot_updated_at
            )
            OR c."CYLINDER_NO" NOT IN (SELECT cylinder_no FROM cy_cylinder_current)
        """)
        
        rows = cursor.fetchall()
        self.stdout.write(f"갱신 대상: {len(rows)}건")
        
        for row in rows:
            self.upsert_cylinder(cursor, row)
    
    def upsert_cylinder(self, cursor, raw_data):
        """단일 용기 Upsert (정책 적용)"""
        # Raw 값 추출
        cylinder_no = raw_data[0]
        raw_gas_name = raw_data[1] or ''
        raw_capacity = raw_data[2]
        raw_valve_spec = raw_data[3] or ''
        raw_cylinder_spec = raw_data[4] or ''
        raw_usage_place = raw_data[5] or ''
        raw_location = raw_data[6] or ''
        raw_condition_code = raw_data[7] or ''
        raw_move_date = raw_data[8]
        raw_withstand_pressure_mainte_date = raw_data[9]
        source_updated_at = raw_data[10]
        
        # ===== 정책 적용 =====
        
        # 1. 밸브 표준화
        dashboard_valve_spec = self.apply_valve_alias(cursor, raw_valve_spec)
        valve_parsed = parse_valve_spec(dashboard_valve_spec)
        
        # 2. 용기 스펙 파싱
        cylinder_parsed = parse_cylinder_spec(raw_cylinder_spec)
        
        # 3. EndUser 정책 적용
        enduser_code, enduser_name = self.apply_enduser_policy(
            cursor, raw_gas_name, raw_capacity, 
            dashboard_valve_spec, raw_cylinder_spec, raw_usage_place
        )
        
        # 4. 상태 변환
        dashboard_status = self.map_condition_code(raw_condition_code)
        
        # 5. 위치 번역 (간단화, 실제로는 Translation 테이블 조회)
        dashboard_location = raw_location  # TODO: 번역 적용
        
        # 6. 사용처 조합
        dashboard_usage_place = parse_usage_place(raw_usage_place, raw_location)
        
        # 7. 용기종류 키 생성 (enduser 포함!)
        dashboard_cylinder_type_key = self.generate_type_key(
            raw_gas_name, raw_capacity, dashboard_valve_spec,
            raw_cylinder_spec, dashboard_usage_place, enduser_code
        )
        
        # 8. 파생 필드 계산
        is_available = dashboard_status in ('보관', '충전')
        
        # Upsert 실행
        cursor.execute("""
            INSERT INTO cy_cylinder_current (
                cylinder_no,
                raw_gas_name, raw_capacity, raw_valve_spec, raw_cylinder_spec,
                raw_usage_place, raw_location, raw_condition_code,
                raw_position_user_name, raw_move_date, raw_withstand_pressure_mainte_date,
                dashboard_gas_name, dashboard_capacity,
                dashboard_valve_spec, dashboard_valve_format, dashboard_valve_material,
                dashboard_cylinder_spec, dashboard_cylinder_format, dashboard_cylinder_material,
                dashboard_enduser_code, dashboard_enduser_name, dashboard_usage_place,
                dashboard_status, dashboard_location,
                dashboard_cylinder_type_key,
                dashboard_pressure_due_date, dashboard_last_event_at,
                is_available,
                source_updated_at, snapshot_updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            )
            ON CONFLICT (cylinder_no) DO UPDATE SET
                raw_gas_name = EXCLUDED.raw_gas_name,
                raw_capacity = EXCLUDED.raw_capacity,
                raw_valve_spec = EXCLUDED.raw_valve_spec,
                raw_cylinder_spec = EXCLUDED.raw_cylinder_spec,
                raw_usage_place = EXCLUDED.raw_usage_place,
                raw_location = EXCLUDED.raw_location,
                raw_condition_code = EXCLUDED.raw_condition_code,
                raw_move_date = EXCLUDED.raw_move_date,
                raw_withstand_pressure_mainte_date = EXCLUDED.raw_withstand_pressure_mainte_date,
                dashboard_gas_name = EXCLUDED.dashboard_gas_name,
                dashboard_capacity = EXCLUDED.dashboard_capacity,
                dashboard_valve_spec = EXCLUDED.dashboard_valve_spec,
                dashboard_valve_format = EXCLUDED.dashboard_valve_format,
                dashboard_valve_material = EXCLUDED.dashboard_valve_material,
                dashboard_cylinder_spec = EXCLUDED.dashboard_cylinder_spec,
                dashboard_cylinder_format = EXCLUDED.dashboard_cylinder_format,
                dashboard_cylinder_material = EXCLUDED.dashboard_cylinder_material,
                dashboard_enduser_code = EXCLUDED.dashboard_enduser_code,
                dashboard_enduser_name = EXCLUDED.dashboard_enduser_name,
                dashboard_usage_place = EXCLUDED.dashboard_usage_place,
                dashboard_status = EXCLUDED.dashboard_status,
                dashboard_location = EXCLUDED.dashboard_location,
                dashboard_cylinder_type_key = EXCLUDED.dashboard_cylinder_type_key,
                dashboard_pressure_due_date = EXCLUDED.dashboard_pressure_due_date,
                dashboard_last_event_at = EXCLUDED.dashboard_last_event_at,
                is_available = EXCLUDED.is_available,
                source_updated_at = EXCLUDED.source_updated_at,
                snapshot_updated_at = NOW()
        """, [
            cylinder_no,
            raw_gas_name, raw_capacity, raw_valve_spec, raw_cylinder_spec,
            raw_usage_place, raw_location, raw_condition_code,
            raw_location, raw_move_date, raw_withstand_pressure_mainte_date,
            raw_gas_name, raw_capacity,  # dashboard_gas_name (번역은 별도)
            dashboard_valve_spec, valve_parsed['format'], valve_parsed['material'],
            raw_cylinder_spec, cylinder_parsed['format'], cylinder_parsed['material'],
            enduser_code, enduser_name, dashboard_usage_place,
            dashboard_status, dashboard_location,
            dashboard_cylinder_type_key,
            raw_withstand_pressure_mainte_date, raw_move_date,
            is_available,
            source_updated_at
        ])
    
    def apply_valve_alias(self, cursor, raw_valve_spec):
        """밸브 표준화 정책 적용"""
        cursor.execute("""
            SELECT standard_valve_spec 
            FROM cy_valve_alias 
            WHERE raw_valve_spec = %s AND is_active = TRUE
            ORDER BY priority ASC
            LIMIT 1
        """, [raw_valve_spec])
        result = cursor.fetchone()
        return result[0] if result else raw_valve_spec
    
    def apply_enduser_policy(self, cursor, gas_name, capacity, valve_spec, cylinder_spec, usage_place):
        """EndUser 정책 적용"""
        # 1. cylinder_type_key로 정확히 매칭되는 예외 찾기
        type_key = generate_cylinder_type_key(gas_name, capacity, valve_spec, cylinder_spec, usage_place)
        cursor.execute("""
            SELECT exception_enduser_code, exception_enduser_name
            FROM cy_enduser_policy
            WHERE cylinder_type_key = %s AND is_active = TRUE
            ORDER BY id DESC
            LIMIT 1
        """, [type_key])
        result = cursor.fetchone()
        if result:
            return result[0], result[1]
        
        # 2. 기본값 반환
        cursor.execute("""
            SELECT default_enduser_code, default_enduser_name
            FROM cy_enduser_policy
            WHERE cylinder_type_key IS NULL AND is_active = TRUE
            ORDER BY id DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        if result:
            return result[0], result[1]
        
        # 3. 하드코딩 기본값
        return 'SDC', 'SDC'
    
    def generate_type_key(self, gas_name, capacity, valve_spec, cylinder_spec, usage_place, enduser_code):
        """용기종류 키 생성 (enduser 포함)"""
        key_string = f"{gas_name}|{capacity or ''}|{valve_spec or ''}|{cylinder_spec or ''}|{usage_place or ''}|{enduser_code or ''}"
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    def map_condition_code(self, code):
        """상태 코드 → 상태명 변환"""
        mapping = {
            '100': '보관', '102': '보관',
            '210': '충전', '220': '충전',
            '420': '분석',
            '500': '창입',
            '600': '출하',
            '190': '이상',
            '950': '폐기', '952': '폐기',
        }
        return mapping.get(code, '기타')
```

#### 순수 SQL 방식 (PostgreSQL Function)

```sql
-- 밸브 표준화 함수
CREATE OR REPLACE FUNCTION get_standard_valve_spec(raw_spec VARCHAR)
RETURNS VARCHAR AS $$
BEGIN
    RETURN COALESCE(
        (SELECT standard_valve_spec 
         FROM cy_valve_alias 
         WHERE raw_valve_spec = raw_spec AND is_active = TRUE
         ORDER BY priority ASC LIMIT 1),
        raw_spec
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- EndUser 정책 적용 함수
CREATE OR REPLACE FUNCTION get_enduser_code(
    p_type_key VARCHAR,
    p_gas_name VARCHAR,
    p_capacity NUMERIC
) RETURNS VARCHAR AS $$
DECLARE
    v_code VARCHAR;
BEGIN
    -- 예외 규칙 확인
    SELECT exception_enduser_code INTO v_code
    FROM cy_enduser_policy
    WHERE cylinder_type_key = p_type_key AND is_active = TRUE
    ORDER BY id DESC LIMIT 1;
    
    IF v_code IS NOT NULL THEN
        RETURN v_code;
    END IF;
    
    -- 기본값
    SELECT default_enduser_code INTO v_code
    FROM cy_enduser_policy
    WHERE cylinder_type_key IS NULL AND is_active = TRUE
    ORDER BY id DESC LIMIT 1;
    
    RETURN COALESCE(v_code, 'SDC');
END;
$$ LANGUAGE plpgsql STABLE;

-- 스냅샷 갱신 함수
CREATE OR REPLACE FUNCTION sync_cylinder_snapshot(p_cylinder_no VARCHAR)
RETURNS VOID AS $$
DECLARE
    v_raw RECORD;
    v_dashboard RECORD;
BEGIN
    -- VIEW에서 원본 데이터 조회
    SELECT * INTO v_raw FROM vw_cynow_cylinder_list WHERE cylinder_no = p_cylinder_no;
    
    IF NOT FOUND THEN
        -- 용기가 삭제된 경우
        DELETE FROM cy_cylinder_current WHERE cylinder_no = p_cylinder_no;
        RETURN;
    END IF;
    
    -- 정책 적용
    v_dashboard.valve_spec := get_standard_valve_spec(v_raw.valve_spec);
    v_dashboard.type_key := MD5(...);  -- 정책 적용 후 키 생성
    v_dashboard.enduser_code := get_enduser_code(...);
    
    -- Upsert
    INSERT INTO cy_cylinder_current (...) VALUES (...)
    ON CONFLICT (cylinder_no) DO UPDATE SET ...;
END;
$$ LANGUAGE plpgsql;
```

### 3.2 배치 갱신 방식 (대안)

**사용 시나리오**: CDC 이벤트가 없거나, 주기적 전체 동기화가 필요한 경우

```python
# core/management/commands/sync_cylinder_snapshot_batch.py
def full_sync(self, cursor):
    """전체 재생성 (배치)"""
    cursor.execute("TRUNCATE TABLE cy_cylinder_current;")
    
    cursor.execute("""
        SELECT ... FROM vw_cynow_cylinder_list
    """)
    
    batch_size = 1000
    rows = cursor.fetchmany(batch_size)
    
    while rows:
        for row in rows:
            self.upsert_cylinder(cursor, row)
        rows = cursor.fetchmany(batch_size)
```

**실행 주기**: Cron으로 5분마다 또는 1시간마다 실행

---

## 4. 조회/집계 시 적용 규칙

### 4.1 EndUser 결정 우선순위

1. **예외 규칙 확인**: `cy_enduser_policy`에서 `cylinder_type_key`로 정확히 매칭되는 예외가 있으면 해당 `exception_enduser_code` 사용
2. **기본값 적용**: 예외가 없으면 `cy_enduser_policy`의 `default_enduser_code` 사용 (기본값: 'SDC')
3. **하드코딩 폴백**: 정책 테이블에 데이터가 없으면 'SDC' 사용

**주의**: `dashboard_cylinder_type_key`는 **enduser를 포함**하여 생성하므로, enduser가 다른 용기는 다른 용기종류로 분리됨.

### 4.2 밸브 Raw vs Dashboard 구분

- **Raw 값 (`raw_valve_spec`)**: 
  - FCMS 원본 값 그대로 저장
  - 감사(audit), 이력 추적용
  - 절대 변경하지 않음
  
- **Dashboard 값 (`dashboard_valve_spec`)**:
  - `cy_valve_alias` 정책 적용
  - 대시보드 표시, 집계, 그룹화용
  - 정책 변경 시 재계산됨

**집계 시**: 항상 `dashboard_valve_spec` 사용
**감사 시**: `raw_valve_spec` 확인

### 4.3 용기종류 그룹화 규칙

```sql
-- 대시보드 집계 쿼리 예시
SELECT 
    dashboard_cylinder_type_key,
    dashboard_gas_name,
    dashboard_capacity,
    dashboard_valve_spec,  -- 표준화된 값
    dashboard_cylinder_spec,
    dashboard_enduser_code,  -- enduser 포함!
    dashboard_status,
    COUNT(*) as qty
FROM cy_cylinder_current
WHERE is_available = TRUE
GROUP BY 
    dashboard_cylinder_type_key,
    dashboard_gas_name,
    dashboard_capacity,
    dashboard_valve_spec,
    dashboard_cylinder_spec,
    dashboard_enduser_code,
    dashboard_status;
```

---

## 5. VIEW → 스냅샷 테이블 마이그레이션 절차

### 5.1 단계별 마이그레이션

#### Phase 1: 정책 테이블 생성 및 초기 데이터 입력

```sql
-- 1. 정책 테이블 생성
-- (위 DDL 실행)

-- 2. 기본 EndUser 정책 입력
INSERT INTO cy_enduser_policy (default_enduser_code, default_enduser_name, is_active)
VALUES ('SDC', 'SDC', TRUE);

-- 3. 예외 규칙 입력 (CF4 YC 440L LGD 전용 29병)
INSERT INTO cy_enduser_policy (
    cylinder_type_key, gas_name, capacity, valve_spec, cylinder_spec,
    exception_enduser_code, exception_enduser_name, is_active, notes
)
SELECT 
    MD5('CF4|440|...|LGD')::VARCHAR,  -- 정확한 키는 실제 값으로 계산
    'CF4', 440, '...', '...',
    'LGD', 'LGD', TRUE,
    'CF4 YC 440L LGD 전용 29병'
WHERE EXISTS (
    SELECT 1 FROM vw_cynow_cylinder_list 
    WHERE gas_name = 'CF4' AND capacity = 440
    LIMIT 1
);

-- 4. 밸브 표준화 정책 입력 (COS CGA330 NERIKI/HAMAI 통합)
INSERT INTO cy_valve_alias (raw_valve_spec, standard_valve_spec, valve_group_code, is_active, notes)
VALUES 
    ('SUS general Y CGA330 Y NERIKI', 'SUS general Y CGA330', 'CGA330', TRUE, 'NERIKI/HAMAI 통합'),
    ('SUS general Y CGA330 Y HAMAI', 'SUS general Y CGA330', 'CGA330', TRUE, 'NERIKI/HAMAI 통합');
```

#### Phase 2: 스냅샷 테이블 생성 및 초기 데이터 적재

```bash
# Django management command 실행
python manage.py sync_cylinder_snapshot --full
```

#### Phase 3: Repository 레이어 수정

```python
# core/repositories/cylinder_repository.py (신규)
class CylinderRepository:
    @staticmethod
    def get_inventory_view(filters=None):
        """스냅샷 테이블에서 조회"""
        with connection.cursor() as cursor:
            query = """
                SELECT 
                    dashboard_cylinder_type_key as cylinder_type_key,
                    dashboard_gas_name as gas_name,
                    dashboard_capacity as capacity,
                    dashboard_valve_spec as valve_spec,
                    dashboard_cylinder_spec as cylinder_spec,
                    dashboard_usage_place as usage_place,
                    dashboard_status as status,
                    dashboard_location as location,
                    COUNT(*) as qty
                FROM cy_cylinder_current
                WHERE 1=1
            """
            # 필터 적용...
            cursor.execute(query)
            # ...
    
    @staticmethod
    def get_cylinder_list(filters=None, limit=None):
        """스냅샷 테이블에서 조회"""
        with connection.cursor() as cursor:
            query = """
                SELECT 
                    cylinder_no,
                    dashboard_gas_name as gas_name,
                    dashboard_capacity as capacity,
                    dashboard_valve_spec as valve_spec,
                    dashboard_cylinder_spec as cylinder_spec,
                    dashboard_usage_place as usage_place,
                    dashboard_status as status,
                    dashboard_location as location,
                    dashboard_pressure_due_date as pressure_due_date,
                    dashboard_last_event_at as last_event_at
                FROM cy_cylinder_current
                WHERE 1=1
            """
            # ...
```

#### Phase 4: 점진적 전환 (Dual Read)

```python
# settings.py
USE_SNAPSHOT_TABLE = os.getenv('USE_SNAPSHOT_TABLE', 'False') == 'True'

# core/repositories/view_repository.py
class ViewRepository:
    @staticmethod
    def get_inventory_view(filters=None):
        if settings.USE_SNAPSHOT_TABLE:
            return CylinderRepository.get_inventory_view(filters)
        else:
            # 기존 VIEW 조회
            ...
```

#### Phase 5: 완전 전환

1. `.env`에 `USE_SNAPSHOT_TABLE=True` 설정
2. 모든 뷰에서 스냅샷 테이블 사용 확인
3. 기존 VIEW는 유지 (감사용)
4. CDC 이벤트 기반 갱신 활성화

---

## 6. 성능 최적화

### 6.1 인덱스 전략

```sql
-- 집계 쿼리 최적화
CREATE INDEX idx_cy_current_agg ON cy_cylinder_current(
    dashboard_cylinder_type_key, 
    dashboard_status, 
    is_available
) WHERE is_available = TRUE;

-- 필터링 최적화
CREATE INDEX idx_cy_current_filter ON cy_cylinder_current(
    dashboard_gas_name_lower, 
    dashboard_status_lower, 
    dashboard_enduser_code
);
```

### 6.2 파티셔닝 (선택사항)

```sql
-- 상태별 파티셔닝 (대용량 시)
CREATE TABLE cy_cylinder_current_available PARTITION OF cy_cylinder_current
    FOR VALUES IN (TRUE);
CREATE TABLE cy_cylinder_current_unavailable PARTITION OF cy_cylinder_current
    FOR VALUES IN (FALSE);
```

---

## 7. 정책 관리 UI (Django Admin)

```python
# core/admin.py
@admin.register(EndUserPolicy)
class EndUserPolicyAdmin(admin.ModelAdmin):
    list_display = ['cylinder_type_key', 'exception_enduser_code', 'is_active', 'updated_at']
    list_filter = ['is_active', 'exception_enduser_code']
    search_fields = ['gas_name', 'cylinder_type_key']

@admin.register(ValveAlias)
class ValveAliasAdmin(admin.ModelAdmin):
    list_display = ['raw_valve_spec', 'standard_valve_spec', 'valve_group_code', 'is_active']
    list_filter = ['is_active', 'valve_group_code']
    search_fields = ['raw_valve_spec', 'standard_valve_spec']
```

---

## 8. 검증 쿼리

```sql
-- EndUser 정책 적용 확인
SELECT 
    dashboard_gas_name,
    dashboard_capacity,
    dashboard_enduser_code,
    COUNT(*) as qty
FROM cy_cylinder_current
WHERE dashboard_gas_name = 'CF4' AND dashboard_capacity = 440
GROUP BY dashboard_gas_name, dashboard_capacity, dashboard_enduser_code;

-- 밸브 표준화 확인
SELECT 
    raw_valve_spec,
    dashboard_valve_spec,
    COUNT(*) as qty
FROM cy_cylinder_current
WHERE raw_valve_spec LIKE '%CGA330%'
GROUP BY raw_valve_spec, dashboard_valve_spec;

-- 성능 비교
EXPLAIN ANALYZE SELECT * FROM vw_cynow_inventory;  -- 기존
EXPLAIN ANALYZE SELECT * FROM cy_cylinder_current;  -- 신규
```

