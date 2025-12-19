-- EndUser 마스터 테이블 생성
CREATE TABLE IF NOT EXISTS cy_enduser_master (
    id SERIAL PRIMARY KEY,
    enduser_code VARCHAR(50) NOT NULL UNIQUE,
    enduser_name VARCHAR(200) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cy_enduser_master_code ON cy_enduser_master(enduser_code) WHERE is_active = TRUE;

-- 기본 EndUser 데이터 삽입
INSERT INTO cy_enduser_master (enduser_code, enduser_name, description, is_active)
VALUES 
    ('SDC', 'SDC', '기본 EndUser', TRUE),
    ('LGD', 'LGD', 'LGD EndUser', TRUE)
ON CONFLICT (enduser_code) DO NOTHING;










