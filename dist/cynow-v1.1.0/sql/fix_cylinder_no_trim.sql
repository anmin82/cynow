-- 용기번호 오른쪽 공백 제거 및 정리

-- 1. cy_enduser_exception 테이블의 용기번호 오른쪽 공백 제거
UPDATE cy_enduser_exception
SET cylinder_no = RTRIM(cylinder_no)
WHERE cylinder_no != RTRIM(cylinder_no);

-- 2. cy_cylinder_current 테이블의 용기번호 오른쪽 공백 제거 (이미 TRIM으로 저장되어야 하지만 확인)
-- 주의: 이 작업은 PRIMARY KEY를 변경하므로 신중하게 진행해야 함
-- 먼저 중복 확인
SELECT 
    TRIM(cylinder_no) as trimmed_no,
    COUNT(*) as count
FROM cy_cylinder_current
GROUP BY TRIM(cylinder_no)
HAVING COUNT(*) > 1;

-- 중복이 없으면 업데이트 가능
-- UPDATE cy_cylinder_current
-- SET cylinder_no = RTRIM(cylinder_no)
-- WHERE cylinder_no != RTRIM(cylinder_no);

-- 3. cy_enduser_exception 테이블에 TRIM된 용기번호로 인덱스 재생성
-- (UNIQUE 제약조건이 있으므로 자동으로 처리됨)

-- 4. 확인 쿼리: 공백이 있는 용기번호 확인
SELECT 
    'cy_enduser_exception' as table_name,
    cylinder_no,
    LENGTH(cylinder_no) as length,
    LENGTH(RTRIM(cylinder_no)) as trimmed_length
FROM cy_enduser_exception
WHERE cylinder_no != RTRIM(cylinder_no)
LIMIT 10;

SELECT 
    'cy_cylinder_current' as table_name,
    cylinder_no,
    LENGTH(cylinder_no) as length,
    LENGTH(RTRIM(cylinder_no)) as trimmed_length
FROM cy_cylinder_current
WHERE cylinder_no != RTRIM(cylinder_no)
LIMIT 10;

