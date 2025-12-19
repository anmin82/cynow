-- cy_cylinder_current 테이블에 내압 관련 컬럼 추가
-- 실행: psql -U postgres -d cycy_db -f alter_add_pressure_columns.sql

-- 1. 새 컬럼 추가
ALTER TABLE cy_cylinder_current 
    ADD COLUMN IF NOT EXISTS manufacture_date DATE,                    -- 제조일
    ADD COLUMN IF NOT EXISTS pressure_test_date DATE,                  -- 내압시험일
    ADD COLUMN IF NOT EXISTS pressure_test_term INTEGER,               -- 검사갱신년수 (3년 또는 5년)
    ADD COLUMN IF NOT EXISTS pressure_expire_date DATE,                -- 내압만료일 (계산값)
    ADD COLUMN IF NOT EXISTS needs_fcms_fix BOOLEAN DEFAULT FALSE;     -- FCMS 수정 필요 여부

-- 2. 기존 pressure_due_date 컬럼명 변경 설명
-- 기존 pressure_due_date는 실제로 WITHSTAND_PRESSURE_MAINTE_DATE (내압시험일)
-- 혼란 방지를 위해 새 컬럼 pressure_test_date를 사용하고, 기존 컬럼은 유지

-- 3. 인덱스 추가 (내압만료일 검색용)
CREATE INDEX IF NOT EXISTS idx_cy_cylinder_current_pressure_expire 
    ON cy_cylinder_current(pressure_expire_date);

CREATE INDEX IF NOT EXISTS idx_cy_cylinder_current_fcms_fix 
    ON cy_cylinder_current(needs_fcms_fix) 
    WHERE needs_fcms_fix = TRUE;

-- 4. 코멘트 추가
COMMENT ON COLUMN cy_cylinder_current.manufacture_date IS '용기 제조일 (FCMS MANUFACTURE_DATE)';
COMMENT ON COLUMN cy_cylinder_current.pressure_test_date IS '내압시험일 (FCMS WITHSTAND_PRESSURE_MAINTE_DATE)';
COMMENT ON COLUMN cy_cylinder_current.pressure_test_term IS '검사갱신년수 (FCMS WITHSTAND_PRESSURE_TEST_TERM, 보통 5년, 10년 경과 시 3년)';
COMMENT ON COLUMN cy_cylinder_current.pressure_expire_date IS '내압만료일 (내압시험일 + 검사갱신년수)';
COMMENT ON COLUMN cy_cylinder_current.needs_fcms_fix IS 'FCMS 수정 필요 여부 (제조일로부터 10년 경과했는데 검사갱신년수가 3이 아닌 경우)';


