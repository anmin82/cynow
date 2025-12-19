-- CYNOW 정책 테이블 생성 DDL

-- 1. EndUser 기본값 테이블
CREATE TABLE IF NOT EXISTS cy_enduser_default (
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

CREATE INDEX IF NOT EXISTS idx_cy_enduser_default_lookup 
ON cy_enduser_default(gas_name, capacity, valve_spec_code, cylinder_spec_code) 
WHERE is_active = TRUE;

-- 2. EndUser 예외 테이블
CREATE TABLE IF NOT EXISTS cy_enduser_exception (
    id SERIAL PRIMARY KEY,
    cylinder_no VARCHAR(20) NOT NULL UNIQUE,
    enduser VARCHAR(50) NOT NULL,
    reason TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cy_enduser_exception_cylinder 
ON cy_enduser_exception(cylinder_no) 
WHERE is_active = TRUE;

-- 3. 밸브 그룹 테이블
CREATE TABLE IF NOT EXISTS cy_valve_group (
    id SERIAL PRIMARY KEY,
    group_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 4. 밸브 그룹 매핑 테이블
CREATE TABLE IF NOT EXISTS cy_valve_group_mapping (
    id SERIAL PRIMARY KEY,
    valve_spec_code VARCHAR(50) NOT NULL,
    valve_spec_name VARCHAR(200) NOT NULL,
    group_id INTEGER NOT NULL REFERENCES cy_valve_group(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(valve_spec_code, valve_spec_name)
);

CREATE INDEX IF NOT EXISTS idx_cy_valve_group_mapping_lookup 
ON cy_valve_group_mapping(valve_spec_code, valve_spec_name) 
WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_cy_valve_group_mapping_group 
ON cy_valve_group_mapping(group_id) 
WHERE is_active = TRUE;

