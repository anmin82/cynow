-- PostgreSQL VIEW 생성 SQL
-- 실제 CDC 테이블 구조 기반 (fcms_cdc 스키마)

-- 1. vw_cynow_cylinder_list VIEW 생성
-- 개별 용기 리스트를 제공하는 VIEW
DROP VIEW IF EXISTS vw_cynow_cylinder_list CASCADE;

CREATE OR REPLACE VIEW vw_cynow_cylinder_list AS
SELECT 
    c."CYLINDER_NO" as cylinder_no,
    COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') as gas_name,
    c."CAPACITY" as capacity,
    COALESCE(vs."NAME", '') as valve_spec,
    COALESCE(cs."NAME", '') as cylinder_spec,
    COALESCE(c."USE_DEPARTMENT_CODE", '') as usage_place,
    CASE 
        WHEN ls."CONDITION_CODE" IN ('100', '102') THEN '보관'
        WHEN ls."CONDITION_CODE" IN ('210', '220') THEN '충전'
        WHEN ls."CONDITION_CODE" = '420' THEN '분석'
        WHEN ls."CONDITION_CODE" = '500' THEN '창입'
        WHEN ls."CONDITION_CODE" = '600' THEN '출하'
        WHEN ls."CONDITION_CODE" = '190' THEN '이상'
        WHEN ls."CONDITION_CODE" IN ('950', '952') THEN '정비'
        WHEN ls."CONDITION_CODE" = '990' THEN '폐기'
        ELSE '기타'
    END as status,
    COALESCE(ls."POSITION_USER_NAME", '') as location,
    c."WITHSTAND_PRESSURE_MAINTE_DATE" as pressure_due_date,
    ls."MOVE_DATE" as last_event_at,
    GREATEST(
        COALESCE(c."UPDATE_DATETIME", c."ADD_DATETIME"),
        COALESCE(ls."MOVE_DATE", NOW())
    ) as source_updated_at
FROM "fcms_cdc"."ma_cylinders" c
LEFT JOIN "fcms_cdc"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
LEFT JOIN "fcms_cdc"."ma_cylinder_specs" cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
LEFT JOIN "fcms_cdc"."ma_valve_specs" vs ON c."VALVE_SPEC_CODE" = vs."VALVE_SPEC_CODE"
LEFT JOIN "fcms_cdc"."tr_latest_cylinder_statuses" ls ON c."CYLINDER_NO" = ls."CYLINDER_NO";


-- 2. vw_cynow_inventory VIEW 생성
-- 용기종류 × 상태 × 위치별 수량 집계를 제공하는 VIEW (SSOT)
DROP VIEW IF EXISTS vw_cynow_inventory CASCADE;

CREATE OR REPLACE VIEW vw_cynow_inventory AS
SELECT 
    MD5(
        COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') || '|' ||
        COALESCE(CAST(c."CAPACITY" AS TEXT), '') || '|' ||
        COALESCE(vs."NAME", '') || '|' ||
        COALESCE(cs."NAME", '') || '|' ||
        COALESCE(c."USE_DEPARTMENT_CODE", '')
    ) as cylinder_type_key,
    COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') as gas_name,
    c."CAPACITY" as capacity,
    COALESCE(vs."NAME", '') as valve_spec,
    COALESCE(cs."NAME", '') as cylinder_spec,
    COALESCE(c."USE_DEPARTMENT_CODE", '') as usage_place,
    CASE 
        WHEN ls."CONDITION_CODE" IN ('100', '102') THEN '보관'
        WHEN ls."CONDITION_CODE" IN ('210', '220') THEN '충전'
        WHEN ls."CONDITION_CODE" = '420' THEN '분석'
        WHEN ls."CONDITION_CODE" = '500' THEN '창입'
        WHEN ls."CONDITION_CODE" = '600' THEN '출하'
        WHEN ls."CONDITION_CODE" = '190' THEN '이상'
        WHEN ls."CONDITION_CODE" IN ('950', '952') THEN '정비'
        WHEN ls."CONDITION_CODE" = '990' THEN '폐기'
        ELSE '기타'
    END as status,
    COALESCE(ls."POSITION_USER_NAME", '') as location,
    COUNT(DISTINCT c."CYLINDER_NO") as qty,
    NOW() as updated_at
FROM "fcms_cdc"."ma_cylinders" c
LEFT JOIN "fcms_cdc"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
LEFT JOIN "fcms_cdc"."ma_cylinder_specs" cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
LEFT JOIN "fcms_cdc"."ma_valve_specs" vs ON c."VALVE_SPEC_CODE" = vs."VALVE_SPEC_CODE"
LEFT JOIN "fcms_cdc"."tr_latest_cylinder_statuses" ls ON c."CYLINDER_NO" = ls."CYLINDER_NO"
GROUP BY 
    cylinder_type_key,
    gas_name,
    c."CAPACITY",
    valve_spec,
    cylinder_spec,
    usage_place,
    status,
    location;


-- VIEW 확인
SELECT COUNT(*) as inventory_count FROM vw_cynow_inventory;
SELECT COUNT(*) as cylinder_count FROM vw_cynow_cylinder_list;
SELECT gas_name, status, location, qty FROM vw_cynow_inventory LIMIT 10;












