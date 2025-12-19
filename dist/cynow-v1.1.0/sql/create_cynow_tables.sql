-- CYNOW 전용 테이블 생성 DDL
-- PostgreSQL 기준

-- ============================================
-- 1. EndUser 정책 테이블
-- ============================================
CREATE TABLE IF NOT EXISTS cy_enduser_policy (
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

CREATE INDEX IF NOT EXISTS idx_enduser_policy_type_key ON cy_enduser_policy(cylinder_type_key) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_enduser_policy_gas ON cy_enduser_policy(gas_name, capacity) WHERE is_active = TRUE AND cylinder_type_key IS NULL;

COMMENT ON TABLE cy_enduser_policy IS 'EndUser 전용 분리 정책: 기본값(SDC) + 예외 규칙';
COMMENT ON COLUMN cy_enduser_policy.cylinder_type_key IS 'NULL이면 기본값, 값이 있으면 해당 용기종류에만 예외 적용';
COMMENT ON COLUMN cy_enduser_policy.default_enduser_code IS '기본 EndUser 코드 (대부분 용기에 적용)';

-- ============================================
-- 2. 밸브 표준화(통합) 테이블
-- ============================================
CREATE TABLE IF NOT EXISTS cy_valve_alias (
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
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 부분 인덱스 (활성화된 것만)
CREATE UNIQUE INDEX IF NOT EXISTS idx_valve_alias_raw_unique ON cy_valve_alias(raw_valve_spec) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_valve_alias_raw ON cy_valve_alias(raw_valve_spec) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_valve_alias_standard ON cy_valve_alias(standard_valve_spec) WHERE is_active = TRUE;

COMMENT ON TABLE cy_valve_alias IS '밸브 표준화 정책: NERIKI/HAMAI → CGA330 통합 등';
COMMENT ON COLUMN cy_valve_alias.raw_valve_spec IS 'FCMS 원본 밸브 스펙 (감사용)';
COMMENT ON COLUMN cy_valve_alias.standard_valve_spec IS '대시보드 표시용 표준 밸브 스펙';

-- ============================================
-- 3. 대시보드 조회용 스냅샷 테이블
-- ============================================
CREATE TABLE IF NOT EXISTS cy_cylinder_current (
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
    policy_version INTEGER DEFAULT 1  -- 정책 버전 (정책 변경 추적용)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_cy_current_type_key ON cy_cylinder_current(dashboard_cylinder_type_key);
CREATE INDEX IF NOT EXISTS idx_cy_current_gas ON cy_cylinder_current(LOWER(dashboard_gas_name));
CREATE INDEX IF NOT EXISTS idx_cy_current_status ON cy_cylinder_current(LOWER(dashboard_status));
CREATE INDEX IF NOT EXISTS idx_cy_current_enduser ON cy_cylinder_current(dashboard_enduser_code);
CREATE INDEX IF NOT EXISTS idx_cy_current_location ON cy_cylinder_current(dashboard_location);
CREATE INDEX IF NOT EXISTS idx_cy_current_available ON cy_cylinder_current(is_available) WHERE is_available = TRUE;
CREATE INDEX IF NOT EXISTS idx_cy_current_updated ON cy_cylinder_current(snapshot_updated_at);

-- 집계 쿼리 최적화용 복합 인덱스
CREATE INDEX IF NOT EXISTS idx_cy_current_agg ON cy_cylinder_current(
    dashboard_cylinder_type_key, 
    dashboard_status, 
    is_available
) WHERE is_available = TRUE;

COMMENT ON TABLE cy_cylinder_current IS '용기 현재 상태 스냅샷 (대시보드 조회 전용)';
COMMENT ON COLUMN cy_cylinder_current.raw_* IS 'FCMS 원본 값 (감사/이력용, 변경 불가)';
COMMENT ON COLUMN cy_cylinder_current.dashboard_* IS 'CYNOW 정책 적용된 값 (대시보드 표시용)';
COMMENT ON COLUMN cy_cylinder_current.dashboard_cylinder_type_key IS '정책 적용 후 생성된 용기종류 키 (enduser 포함)';

-- ============================================
-- 초기 데이터 입력
-- ============================================

-- 기본 EndUser 정책
INSERT INTO cy_enduser_policy (default_enduser_code, default_enduser_name, is_active, notes)
VALUES ('SDC', 'SDC', TRUE, '기본 EndUser (대부분 용기)')
ON CONFLICT DO NOTHING;

-- 밸브 표준화 정책 예시 (COS CGA330 NERIKI/HAMAI 통합)
INSERT INTO cy_valve_alias (raw_valve_spec, standard_valve_spec, valve_group_code, is_active, notes)
VALUES 
    ('SUS general Y CGA330 Y NERIKI', 'SUS general Y CGA330', 'CGA330', TRUE, 'NERIKI/HAMAI 통합'),
    ('SUS general Y CGA330 Y HAMAI', 'SUS general Y CGA330', 'CGA330', TRUE, 'NERIKI/HAMAI 통합')
ON CONFLICT DO NOTHING;

