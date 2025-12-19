-- 특정 용기종류 확인 (CF4 CGA716 용량 360)

-- 1. cy_cylinder_current에서 해당 용기종류 확인
SELECT 
    cylinder_no,
    dashboard_gas_name as 가스명,
    dashboard_capacity as 용량,
    COALESCE(dashboard_valve_group_name, dashboard_valve_spec_name) as 밸브스펙,
    dashboard_cylinder_spec_name as 용기스펙,
    dashboard_status as 상태,
    dashboard_enduser as EndUser,
    cylinder_type_key,
    snapshot_updated_at as 갱신일시
FROM cy_cylinder_current
WHERE dashboard_gas_name LIKE '%CF4%'
  AND dashboard_capacity = 360
  AND (dashboard_valve_group_name LIKE '%CGA716%' OR dashboard_valve_spec_name LIKE '%CGA716%')
ORDER BY cylinder_no;

-- 2. 집계 확인
SELECT 
    cylinder_type_key,
    dashboard_gas_name as 가스명,
    dashboard_capacity as 용량,
    COALESCE(dashboard_valve_group_name, dashboard_valve_spec_name) as 밸브스펙,
    dashboard_cylinder_spec_name as 용기스펙,
    dashboard_status as 상태,
    STRING_AGG(DISTINCT dashboard_enduser, ', ' ORDER BY dashboard_enduser) as EndUser,
    COUNT(*) as 수량
FROM cy_cylinder_current
WHERE dashboard_gas_name LIKE '%CF4%'
  AND dashboard_capacity = 360
  AND (dashboard_valve_group_name LIKE '%CGA716%' OR dashboard_valve_spec_name LIKE '%CGA716%')
GROUP BY 
    cylinder_type_key,
    dashboard_gas_name,
    dashboard_capacity,
    COALESCE(dashboard_valve_group_name, dashboard_valve_spec_name),
    dashboard_cylinder_spec_name,
    dashboard_status
ORDER BY dashboard_status;

-- 3. fcms_cdc.ma_cylinders에 존재하는지 확인
SELECT 
    c."CYLINDER_NO",
    COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') as 가스명,
    c."CAPACITY" as 용량,
    COALESCE(vs."NAME", '') as 밸브스펙,
    COALESCE(cs."NAME", '') as 용기스펙
FROM "fcms_cdc"."ma_cylinders" c
LEFT JOIN "fcms_cdc"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
LEFT JOIN "fcms_cdc"."ma_valve_specs" vs ON c."VALVE_SPEC_CODE" = vs."VALVE_SPEC_CODE"
LEFT JOIN "fcms_cdc"."ma_cylinder_specs" cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
WHERE COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') LIKE '%CF4%'
  AND c."CAPACITY" = 360
  AND (COALESCE(vs."NAME", '') LIKE '%CGA716%' OR c."VALVE_SPEC_CODE" LIKE '%CGA716%')
ORDER BY c."CYLINDER_NO";

-- 4. 고아 데이터 확인 (cy_cylinder_current에는 있지만 ma_cylinders에는 없음)
SELECT 
    c.cylinder_no,
    c.dashboard_gas_name as 가스명,
    c.dashboard_capacity as 용량,
    c.dashboard_status as 상태,
    c.snapshot_updated_at as 갱신일시
FROM cy_cylinder_current c
LEFT JOIN "fcms_cdc"."ma_cylinders" mc 
    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
WHERE mc."CYLINDER_NO" IS NULL
  AND c.dashboard_gas_name LIKE '%CF4%'
  AND c.dashboard_capacity = 360
  AND (c.dashboard_valve_group_name LIKE '%CGA716%' OR c.dashboard_valve_spec_name LIKE '%CGA716%')
ORDER BY c.cylinder_no;










