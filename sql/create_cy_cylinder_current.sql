-- cy_cylinder_current 스냅샷 테이블 생성 DDL

CREATE TABLE IF NOT EXISTS cy_cylinder_current (
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
    dashboard_valve_spec_name VARCHAR(200),
    dashboard_valve_group_name VARCHAR(100),
    dashboard_cylinder_spec_code VARCHAR(50),
    dashboard_cylinder_spec_name VARCHAR(200),
    dashboard_usage_place VARCHAR(50),
    dashboard_location VARCHAR(100),
    dashboard_status VARCHAR(20),
    dashboard_enduser VARCHAR(50),
    
    -- 집계/예측용 필드
    cylinder_type_key VARCHAR(32),
    cylinder_type_key_raw VARCHAR(32),
    
    -- 상태/위치 정보
    condition_code VARCHAR(10),
    move_date TIMESTAMP,
    pressure_due_date TIMESTAMP,
    last_event_at TIMESTAMP,
    
    -- 메타데이터
    source_updated_at TIMESTAMP,
    snapshot_updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 인덱스용 컬럼
    status_category VARCHAR(20),
    is_available BOOLEAN
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_cy_cylinder_current_type_key ON cy_cylinder_current(cylinder_type_key);
CREATE INDEX IF NOT EXISTS idx_cy_cylinder_current_status ON cy_cylinder_current(dashboard_status);
CREATE INDEX IF NOT EXISTS idx_cy_cylinder_current_enduser ON cy_cylinder_current(dashboard_enduser);
CREATE INDEX IF NOT EXISTS idx_cy_cylinder_current_location ON cy_cylinder_current(dashboard_location);
CREATE INDEX IF NOT EXISTS idx_cy_cylinder_current_available ON cy_cylinder_current(is_available) WHERE is_available = TRUE;
CREATE INDEX IF NOT EXISTS idx_cy_cylinder_current_gas ON cy_cylinder_current(dashboard_gas_name);
CREATE INDEX IF NOT EXISTS idx_cy_cylinder_current_updated ON cy_cylinder_current(snapshot_updated_at);

-- 복합 인덱스
CREATE INDEX IF NOT EXISTS idx_cy_cylinder_current_dashboard_lookup ON cy_cylinder_current(
    dashboard_gas_name, 
    dashboard_capacity, 
    dashboard_valve_group_name, 
    dashboard_cylinder_spec_name, 
    dashboard_enduser, 
    dashboard_status
);










