-- CF4 YC 용기의 cylinder_type_key 재계산 및 업데이트
-- sync_cylinder_current_single 함수와 동일한 로직으로 재계산

UPDATE cy_cylinder_current c
SET cylinder_type_key = MD5(
    COALESCE(c.dashboard_gas_name, '') || '|' ||
    COALESCE(CAST(c.dashboard_capacity AS TEXT), '') || '|' ||
    COALESCE(c.dashboard_valve_group_name, c.dashboard_valve_spec_name, '') || '|' ||
    COALESCE(c.dashboard_cylinder_spec_name, '') || '|' ||
    COALESCE(c.dashboard_enduser, '')
),
snapshot_updated_at = NOW()
WHERE c.dashboard_gas_name = 'CF4'
  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
  AND c.dashboard_capacity = 440
  AND c.dashboard_enduser = 'SDC'
  AND EXISTS (
      SELECT 1
      FROM "fcms_cdc"."ma_cylinders" mc
      WHERE RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
  );










