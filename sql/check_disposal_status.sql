-- 대시보드에서 "폐기"로 표시되는 용기들의 실제 상태 코드 확인
-- 내압만료/불량 용기가 "폐기"로 잘못 표시되는지 확인

-- 1. "폐기" 상태로 표시되는 용기들의 실제 상태 코드 확인
SELECT 
    c.cylinder_no,
    c.dashboard_status as 표시상태,
    c.raw_condition_code as 실제상태코드,
    c.pressure_due_date as 내압만료일,
    CASE 
        WHEN c.pressure_due_date < NOW() THEN '만료'
        WHEN c.pressure_due_date IS NULL THEN '미지정'
        ELSE '유효'
    END as 내압상태,
    c.dashboard_status as 현재상태
FROM cy_cylinder_current c
WHERE c.dashboard_status = '폐기'
ORDER BY c.cylinder_no;

-- 2. 내압만료 용기 중 "폐기"로 표시되는 것 확인
SELECT 
    c.cylinder_no,
    c.dashboard_status as 표시상태,
    c.raw_condition_code as 실제상태코드,
    c.pressure_due_date as 내압만료일,
    CASE 
        WHEN c.pressure_due_date < NOW() THEN '만료'
        ELSE '유효'
    END as 내압상태
FROM cy_cylinder_current c
WHERE c.dashboard_status = '폐기'
  AND c.pressure_due_date < NOW()
ORDER BY c.cylinder_no;

-- 3. "이상" 상태 코드(190)인데 "폐기"로 표시되는 것 확인
SELECT 
    c.cylinder_no,
    c.dashboard_status as 표시상태,
    c.raw_condition_code as 실제상태코드,
    c.pressure_due_date as 내압만료일
FROM cy_cylinder_current c
WHERE c.raw_condition_code = '190'
  AND c.dashboard_status = '폐기'
ORDER BY c.cylinder_no;

-- 4. 상태 코드별 "폐기"로 표시되는 용기 수 집계
SELECT 
    c.raw_condition_code as 상태코드,
    COUNT(*) as 폐기로표시된수량
FROM cy_cylinder_current c
WHERE c.dashboard_status = '폐기'
GROUP BY c.raw_condition_code
ORDER BY c.raw_condition_code;










