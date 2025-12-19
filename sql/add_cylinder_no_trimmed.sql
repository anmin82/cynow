-- cy_cylinder_current 테이블에 cylinder_no_trimmed 컬럼 추가
-- 이 컬럼을 UNIQUE KEY로 사용하여 중복 방지

-- 1. 기존 UNIQUE 제약조건 제거
ALTER TABLE cy_cylinder_current DROP CONSTRAINT IF EXISTS cy_cylinder_current_pkey;
ALTER TABLE cy_cylinder_current DROP CONSTRAINT IF EXISTS cy_cylinder_current_cylinder_no_key;

-- 2. cylinder_no_trimmed 컬럼 추가
ALTER TABLE cy_cylinder_current 
ADD COLUMN IF NOT EXISTS cylinder_no_trimmed VARCHAR(20);

-- 3. 기존 데이터에 RTRIM 값 채우기
UPDATE cy_cylinder_current 
SET cylinder_no_trimmed = RTRIM(cylinder_no)
WHERE cylinder_no_trimmed IS NULL;

-- 4. 중복 제거 (cylinder_no_trimmed 기준으로 하나만 남기기)
-- 가장 최신 업데이트된 것 유지
DELETE FROM cy_cylinder_current c1
USING cy_cylinder_current c2
WHERE RTRIM(c1.cylinder_no) = RTRIM(c2.cylinder_no)
  AND c1.ctid < c2.ctid;

-- 5. NOT NULL 및 UNIQUE 제약조건 추가
ALTER TABLE cy_cylinder_current 
ALTER COLUMN cylinder_no_trimmed SET NOT NULL;

ALTER TABLE cy_cylinder_current 
ADD CONSTRAINT cy_cylinder_current_cylinder_no_trimmed_key UNIQUE (cylinder_no_trimmed);

-- 6. 인덱스 추가
CREATE INDEX IF NOT EXISTS idx_cy_cylinder_current_no_trimmed 
ON cy_cylinder_current(cylinder_no_trimmed);

-- 7. 확인
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT cylinder_no) as unique_cylinder_no,
    COUNT(DISTINCT cylinder_no_trimmed) as unique_trimmed
FROM cy_cylinder_current;










