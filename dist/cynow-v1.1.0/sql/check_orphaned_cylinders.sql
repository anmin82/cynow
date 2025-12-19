-- cy_cylinder_current에 있지만 fcms_cdc.ma_cylinders에 없는 용기 확인 (고아 데이터)

-- 1. cy_cylinder_current에 있지만 ma_cylinders에 없는 용기 (삭제되어야 함)
SELECT 
    c.cylinder_no,
    c.dashboard_gas_name as 가스명,
    c.dashboard_status as 상태,
    c.snapshot_updated_at as 마지막갱신일시
FROM cy_cylinder_current c
LEFT JOIN "fcms_cdc"."ma_cylinders" mc 
    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
WHERE mc."CYLINDER_NO" IS NULL
ORDER BY c.cylinder_no;

-- 2. 개수 확인
SELECT 
    COUNT(*) as 고아용기수
FROM cy_cylinder_current c
LEFT JOIN "fcms_cdc"."ma_cylinders" mc 
    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
WHERE mc."CYLINDER_NO" IS NULL;

-- 3. 용기종류별 고아 용기 수
SELECT 
    c.dashboard_gas_name as 가스명,
    c.dashboard_capacity as 용량,
    COUNT(*) as 고아용기수
FROM cy_cylinder_current c
LEFT JOIN "fcms_cdc"."ma_cylinders" mc 
    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
WHERE mc."CYLINDER_NO" IS NULL
GROUP BY c.dashboard_gas_name, c.dashboard_capacity
ORDER BY 고아용기수 DESC;

-- 4. 고아 용기 삭제 (주의: 실행 전 확인 필요)
-- DELETE FROM cy_cylinder_current
-- WHERE cylinder_no IN (
--     SELECT c.cylinder_no
--     FROM cy_cylinder_current c
--     LEFT JOIN "fcms_cdc"."ma_cylinders" mc 
--         ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
--     WHERE mc."CYLINDER_NO" IS NULL
-- );

