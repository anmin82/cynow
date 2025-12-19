-- cy_cylinder_current 동기화 함수 업데이트 (내압 관련 컬럼 추가)
-- 실행: psql -U postgres -d cycy_db -f update_sync_function_pressure.sql
-- 주의: alter_add_pressure_columns.sql 먼저 실행 필요

-- 단일 용기 동기화 함수 (내압 컬럼 추가 버전)
CREATE OR REPLACE FUNCTION sync_cylinder_current_single(p_cylinder_no VARCHAR)
RETURNS VOID AS $$
DECLARE
    v_cylinder_no_trimmed VARCHAR(20);
    v_gas_name VARCHAR(100);
    v_capacity NUMERIC;
    v_valve_spec_code VARCHAR(50);
    v_valve_spec_name VARCHAR(200);
    v_cylinder_spec_code VARCHAR(50);
    v_cylinder_spec_name VARCHAR(200);
    v_usage_place VARCHAR(50);
    v_location VARCHAR(100);
    v_condition_code VARCHAR(10);
    v_position_user_name VARCHAR(100);
    v_move_date TIMESTAMP;
    v_pressure_due_date TIMESTAMP;  -- 기존 호환용
    v_status VARCHAR(20);
    v_enduser VARCHAR(50);
    v_valve_group_name VARCHAR(100);
    v_dashboard_valve_spec_name VARCHAR(200);
    v_cylinder_type_key VARCHAR(32);
    v_cylinder_type_key_raw VARCHAR(32);
    v_is_available BOOLEAN;
    v_source_updated_at TIMESTAMP;
    -- 번역된 값
    v_dashboard_gas_name VARCHAR(100);
    v_dashboard_valve_spec_name_translated VARCHAR(200);
    v_dashboard_cylinder_spec_name_translated VARCHAR(200);
    v_dashboard_location_translated VARCHAR(100);
    -- 내압 관련 새 컬럼
    v_manufacture_date DATE;
    v_pressure_test_date DATE;
    v_pressure_test_term INTEGER;
    v_pressure_expire_date DATE;
    v_needs_fcms_fix BOOLEAN;
    v_years_since_manufacture NUMERIC;
BEGIN
    -- 용기번호 오른쪽 공백 제거 (RTRIM 사용)
    v_cylinder_no_trimmed := RTRIM(p_cylinder_no);
    
    -- FCMS 테이블 조인하여 Raw 값 조회 (내압 컬럼 추가)
    SELECT 
        COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", ''),
        c."CAPACITY",
        c."VALVE_SPEC_CODE",
        COALESCE(vs."NAME", ''),
        c."CYLINDER_SPEC_CODE",
        COALESCE(cs."NAME", ''),
        COALESCE(c."USE_DEPARTMENT_CODE", ''),
        COALESCE(ls."POSITION_USER_NAME", ''),
        COALESCE(ls."CONDITION_CODE", ''),
        ls."POSITION_USER_NAME",
        ls."MOVE_DATE",
        c."WITHSTAND_PRESSURE_MAINTE_DATE",
        GREATEST(
            COALESCE(c."UPDATE_DATETIME", c."ADD_DATETIME"),
            COALESCE(ls."MOVE_DATE", NOW())
        ),
        -- 새로 추가된 컬럼들
        c."MANUFACTURE_DATE"::DATE,
        c."WITHSTAND_PRESSURE_MAINTE_DATE"::DATE,
        COALESCE(c."WITHSTAND_PRESSURE_TEST_TERM", 5)::INTEGER  -- 기본값 5년
    INTO 
        v_gas_name, v_capacity, v_valve_spec_code, v_valve_spec_name,
        v_cylinder_spec_code, v_cylinder_spec_name, v_usage_place,
        v_location, v_condition_code, v_position_user_name,
        v_move_date, v_pressure_due_date, v_source_updated_at,
        v_manufacture_date, v_pressure_test_date, v_pressure_test_term
    FROM "fcms_cdc"."ma_cylinders" c
    LEFT JOIN "fcms_cdc"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
    LEFT JOIN "fcms_cdc"."ma_cylinder_specs" cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
    LEFT JOIN "fcms_cdc"."ma_valve_specs" vs ON c."VALVE_SPEC_CODE" = vs."VALVE_SPEC_CODE"
    LEFT JOIN "fcms_cdc"."tr_latest_cylinder_statuses" ls ON RTRIM(c."CYLINDER_NO") = RTRIM(ls."CYLINDER_NO")
    WHERE RTRIM(c."CYLINDER_NO") = v_cylinder_no_trimmed;
    
    -- 데이터가 없으면 종료
    IF v_gas_name IS NULL THEN
        RETURN;
    END IF;
    
    -- 내압만료일 계산 (내압시험일 + 검사갱신년수)
    IF v_pressure_test_date IS NOT NULL AND v_pressure_test_term IS NOT NULL THEN
        v_pressure_expire_date := v_pressure_test_date + (v_pressure_test_term || ' years')::INTERVAL;
    ELSE
        v_pressure_expire_date := NULL;
    END IF;
    
    -- FCMS 수정 필요 여부 판단
    -- 제조일로부터 10년 이상 경과했는데 검사갱신년수가 3이 아닌 경우
    v_needs_fcms_fix := FALSE;
    IF v_manufacture_date IS NOT NULL THEN
        v_years_since_manufacture := EXTRACT(YEAR FROM AGE(CURRENT_DATE, v_manufacture_date));
        IF v_years_since_manufacture >= 10 AND COALESCE(v_pressure_test_term, 5) != 3 THEN
            v_needs_fcms_fix := TRUE;
        END IF;
    END IF;
    
    -- 상태 코드 → 상태명 변환
    v_status := CASE 
        WHEN v_condition_code IN ('100', '102') THEN '보관'
        WHEN v_condition_code IN ('210', '220') THEN '충전'
        WHEN v_condition_code = '420' THEN '분석'
        WHEN v_condition_code = '500' THEN '창입'
        WHEN v_condition_code = '600' THEN '출하'
        WHEN v_condition_code = '190' THEN '이상'
        WHEN v_condition_code IN ('950', '952') THEN '정비'
        WHEN v_condition_code = '990' THEN '폐기'
        ELSE '기타'
    END;
    
    -- EndUser 결정 (예외 우선, 기본값 차순)
    SELECT COALESCE(
        (SELECT enduser FROM cy_enduser_exception WHERE RTRIM(cylinder_no) = v_cylinder_no_trimmed AND is_active = TRUE),
        (SELECT default_enduser FROM cy_enduser_default 
         WHERE gas_name = v_gas_name 
           AND (capacity IS NULL OR capacity = v_capacity)
           AND (valve_spec_code IS NULL OR valve_spec_code = v_valve_spec_code)
           AND (cylinder_spec_code IS NULL OR cylinder_spec_code = v_cylinder_spec_code)
           AND is_active = TRUE
         ORDER BY 
           CASE WHEN capacity IS NOT NULL THEN 1 ELSE 2 END,
           CASE WHEN valve_spec_code IS NOT NULL THEN 1 ELSE 2 END,
           CASE WHEN cylinder_spec_code IS NOT NULL THEN 1 ELSE 2 END
         LIMIT 1),
        NULL
    ) INTO v_enduser;
    
    -- 밸브 그룹 조회
    SELECT vg.group_name INTO v_valve_group_name
    FROM cy_valve_group_mapping vgm
    JOIN cy_valve_group vg ON vgm.group_id = vg.id
    WHERE vgm.valve_spec_code = v_valve_spec_code
      AND vgm.valve_spec_name = v_valve_spec_name
      AND vgm.is_active = TRUE
      AND vg.is_active = TRUE
    LIMIT 1;
    
    -- Dashboard 밸브명 결정
    v_dashboard_valve_spec_name := v_valve_spec_name;
    IF v_valve_group_name IS NOT NULL THEN
        SELECT vgm2.valve_spec_name INTO v_dashboard_valve_spec_name
        FROM cy_valve_group_mapping vgm2
        JOIN cy_valve_group vg2 ON vgm2.group_id = vg2.id
        WHERE vg2.group_name = v_valve_group_name
          AND vgm2.is_primary = TRUE
          AND vgm2.is_active = TRUE
        LIMIT 1;
        
        IF v_dashboard_valve_spec_name IS NULL THEN
            v_dashboard_valve_spec_name := v_valve_spec_name;
        END IF;
    END IF;
    
    -- 번역 적용
    SELECT COALESCE(
        (SELECT display_ko FROM core_translation 
         WHERE field_type = 'gas_name' 
           AND UPPER(TRIM(source_text)) = UPPER(TRIM(v_gas_name))
           AND is_active = TRUE
         LIMIT 1),
        v_gas_name
    ) INTO v_dashboard_gas_name;
    
    SELECT COALESCE(
        (SELECT display_ko FROM core_translation 
         WHERE field_type = 'valve_spec' 
           AND UPPER(TRIM(source_text)) = UPPER(TRIM(v_dashboard_valve_spec_name))
           AND is_active = TRUE
         LIMIT 1),
        v_dashboard_valve_spec_name
    ) INTO v_dashboard_valve_spec_name_translated;
    
    SELECT COALESCE(
        (SELECT display_ko FROM core_translation 
         WHERE field_type = 'cylinder_spec' 
           AND UPPER(TRIM(source_text)) = UPPER(TRIM(v_cylinder_spec_name))
           AND is_active = TRUE
         LIMIT 1),
        v_cylinder_spec_name
    ) INTO v_dashboard_cylinder_spec_name_translated;
    
    SELECT COALESCE(
        (SELECT display_ko FROM core_translation 
         WHERE field_type = 'location' 
           AND UPPER(TRIM(source_text)) = UPPER(TRIM(v_location))
           AND is_active = TRUE
         LIMIT 1),
        v_location
    ) INTO v_dashboard_location_translated;
    
    -- cylinder_type_key 생성
    v_cylinder_type_key := MD5(
        COALESCE(v_dashboard_gas_name, '') || '|' ||
        COALESCE(CAST(v_capacity AS TEXT), '') || '|' ||
        COALESCE(v_valve_group_name, v_dashboard_valve_spec_name_translated, '') || '|' ||
        COALESCE(v_dashboard_cylinder_spec_name_translated, '') || '|' ||
        COALESCE(v_enduser, '')
    );
    
    v_cylinder_type_key_raw := MD5(
        COALESCE(v_gas_name, '') || '|' ||
        COALESCE(CAST(v_capacity AS TEXT), '') || '|' ||
        COALESCE(v_valve_spec_name, '') || '|' ||
        COALESCE(v_cylinder_spec_name, '') || '|' ||
        COALESCE(v_usage_place, '')
    );
    
    v_is_available := v_status IN ('보관', '충전');
    
    -- Upsert (내압 컬럼 추가)
    INSERT INTO cy_cylinder_current (
        cylinder_no,
        raw_gas_name, raw_capacity, raw_valve_spec_code, raw_valve_spec_name,
        raw_cylinder_spec_code, raw_cylinder_spec_name, raw_usage_place,
        raw_location, raw_condition_code, raw_position_user_name,
        dashboard_gas_name, dashboard_capacity, dashboard_valve_spec_code,
        dashboard_valve_spec_name, dashboard_valve_group_name,
        dashboard_cylinder_spec_code, dashboard_cylinder_spec_name,
        dashboard_location, dashboard_status,
        dashboard_enduser, cylinder_type_key, cylinder_type_key_raw,
        condition_code, move_date, pressure_due_date, last_event_at,
        status_category, is_available, source_updated_at,
        -- 새 내압 컬럼
        manufacture_date, pressure_test_date, pressure_test_term,
        pressure_expire_date, needs_fcms_fix
    ) VALUES (
        v_cylinder_no_trimmed,
        v_gas_name, v_capacity, v_valve_spec_code, v_valve_spec_name,
        v_cylinder_spec_code, v_cylinder_spec_name, v_usage_place,
        v_location, v_condition_code, v_position_user_name,
        v_dashboard_gas_name, v_capacity, v_valve_spec_code,
        v_dashboard_valve_spec_name_translated, v_valve_group_name,
        v_cylinder_spec_code, v_dashboard_cylinder_spec_name_translated,
        v_dashboard_location_translated, v_status,
        v_enduser, v_cylinder_type_key, v_cylinder_type_key_raw,
        v_condition_code, v_move_date, v_pressure_due_date, v_move_date,
        CASE WHEN v_is_available THEN '가용' ELSE '비가용' END,
        v_is_available, v_source_updated_at,
        -- 새 내압 값
        v_manufacture_date, v_pressure_test_date, v_pressure_test_term,
        v_pressure_expire_date, v_needs_fcms_fix
    )
    ON CONFLICT (cylinder_no) DO UPDATE SET
        raw_gas_name = EXCLUDED.raw_gas_name,
        raw_capacity = EXCLUDED.raw_capacity,
        raw_valve_spec_code = EXCLUDED.raw_valve_spec_code,
        raw_valve_spec_name = EXCLUDED.raw_valve_spec_name,
        raw_cylinder_spec_code = EXCLUDED.raw_cylinder_spec_code,
        raw_cylinder_spec_name = EXCLUDED.raw_cylinder_spec_name,
        raw_usage_place = EXCLUDED.raw_usage_place,
        raw_location = EXCLUDED.raw_location,
        raw_condition_code = EXCLUDED.raw_condition_code,
        raw_position_user_name = EXCLUDED.raw_position_user_name,
        dashboard_gas_name = EXCLUDED.dashboard_gas_name,
        dashboard_capacity = EXCLUDED.dashboard_capacity,
        dashboard_valve_spec_code = EXCLUDED.dashboard_valve_spec_code,
        dashboard_valve_spec_name = EXCLUDED.dashboard_valve_spec_name,
        dashboard_valve_group_name = EXCLUDED.dashboard_valve_group_name,
        dashboard_cylinder_spec_code = EXCLUDED.dashboard_cylinder_spec_code,
        dashboard_cylinder_spec_name = EXCLUDED.dashboard_cylinder_spec_name,
        dashboard_location = EXCLUDED.dashboard_location,
        dashboard_status = EXCLUDED.dashboard_status,
        dashboard_enduser = EXCLUDED.dashboard_enduser,
        cylinder_type_key = EXCLUDED.cylinder_type_key,
        cylinder_type_key_raw = EXCLUDED.cylinder_type_key_raw,
        condition_code = EXCLUDED.condition_code,
        move_date = EXCLUDED.move_date,
        pressure_due_date = EXCLUDED.pressure_due_date,
        last_event_at = EXCLUDED.last_event_at,
        status_category = EXCLUDED.status_category,
        is_available = EXCLUDED.is_available,
        source_updated_at = EXCLUDED.source_updated_at,
        -- 새 내압 컬럼 업데이트
        manufacture_date = EXCLUDED.manufacture_date,
        pressure_test_date = EXCLUDED.pressure_test_date,
        pressure_test_term = EXCLUDED.pressure_test_term,
        pressure_expire_date = EXCLUDED.pressure_expire_date,
        needs_fcms_fix = EXCLUDED.needs_fcms_fix,
        snapshot_updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- 기존 데이터 일괄 업데이트 (새 컬럼 채우기)
-- 주의: 이 쿼리는 모든 용기를 다시 동기화함 (시간이 걸릴 수 있음)
DO $$
DECLARE
    r RECORD;
    cnt INTEGER := 0;
BEGIN
    RAISE NOTICE '기존 데이터 내압 컬럼 업데이트 시작...';
    
    FOR r IN SELECT cylinder_no FROM cy_cylinder_current LOOP
        PERFORM sync_cylinder_current_single(r.cylinder_no);
        cnt := cnt + 1;
        
        IF cnt % 1000 = 0 THEN
            RAISE NOTICE '  처리됨: % 건', cnt;
        END IF;
    END LOOP;
    
    RAISE NOTICE '완료: 총 % 건 업데이트됨', cnt;
END $$;


