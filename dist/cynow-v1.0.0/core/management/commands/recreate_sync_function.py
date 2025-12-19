"""sync_cylinder_current_single 함수 재생성"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'sync_cylinder_current_single 함수 재생성 (정책이 없으면 NULL 사용)'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 함수 재생성 (EndUser 결정 부분만)
            update_sql = """
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
                v_pressure_due_date TIMESTAMP;
                v_status VARCHAR(20);
                v_enduser VARCHAR(50);
                v_valve_group_name VARCHAR(100);
                v_dashboard_valve_spec_name VARCHAR(200);
                v_cylinder_type_key VARCHAR(32);
                v_cylinder_type_key_raw VARCHAR(32);
                v_is_available BOOLEAN;
                v_source_updated_at TIMESTAMP;
                v_dashboard_gas_name VARCHAR(100);
                v_dashboard_valve_spec_name_translated VARCHAR(200);
                v_dashboard_cylinder_spec_name_translated VARCHAR(200);
                v_dashboard_location_translated VARCHAR(100);
            BEGIN
                v_cylinder_no_trimmed := RTRIM(p_cylinder_no);
                
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
                    )
                INTO 
                    v_gas_name, v_capacity, v_valve_spec_code, v_valve_spec_name,
                    v_cylinder_spec_code, v_cylinder_spec_name, v_usage_place,
                    v_location, v_condition_code, v_position_user_name,
                    v_move_date, v_pressure_due_date, v_source_updated_at
                FROM "fcms_cdc"."ma_cylinders" c
                LEFT JOIN "fcms_cdc"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
                LEFT JOIN "fcms_cdc"."ma_cylinder_specs" cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
                LEFT JOIN "fcms_cdc"."ma_valve_specs" vs ON c."VALVE_SPEC_CODE" = vs."VALVE_SPEC_CODE"
                LEFT JOIN "fcms_cdc"."tr_latest_cylinder_statuses" ls ON RTRIM(c."CYLINDER_NO") = RTRIM(ls."CYLINDER_NO")
                WHERE RTRIM(c."CYLINDER_NO") = v_cylinder_no_trimmed;
                
                IF v_gas_name IS NULL THEN
                    RETURN;
                END IF;
                
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
                
                -- EndUser 결정: 정책이 없으면 NULL (기본값 SDC 사용 안 함)
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
                
                -- 나머지 로직은 기존과 동일 (생략)
                -- 실제로는 전체 함수를 재생성해야 하지만, 여기서는 핵심 부분만 수정
                -- 전체 함수 재생성을 위해서는 sql/create_sync_triggers.sql 파일을 직접 실행해야 함
            END;
            $$ LANGUAGE plpgsql;
            """
            
            # 전체 함수를 파일에서 읽어서 실행
            from pathlib import Path
            sql_file = Path(__file__).parent.parent.parent.parent / 'sql' / 'create_sync_triggers.sql'
            
            if sql_file.exists():
                with open(sql_file, 'r', encoding='utf-8') as f:
                    full_sql = f.read()
                
                try:
                    # SQL을 세미콜론으로 분리하여 실행
                    # 함수 정의는 하나의 블록이므로 전체를 실행
                    cursor.execute(full_sql)
                    self.stdout.write(self.style.SUCCESS("함수 재생성 완료"))
                    
                    # COS 용기 하나 테스트
                    self.stdout.write("\n테스트: COS 용기 하나 재동기화...")
                    cursor.execute("""
                        SELECT "CYLINDER_NO" 
                        FROM "fcms_cdc"."ma_cylinders" 
                        WHERE RTRIM("CYLINDER_NO") = '22E11131'
                    """)
                    test_result = cursor.fetchone()
                    if test_result:
                        cursor.execute("SELECT sync_cylinder_current_single(%s)", [test_result[0]])
                        cursor.execute("""
                            SELECT dashboard_enduser 
                            FROM cy_cylinder_current 
                            WHERE cylinder_no = '22E11131'
                        """)
                        enduser_result = cursor.fetchone()
                        if enduser_result:
                            self.stdout.write(f"  결과: EndUser = {enduser_result[0]}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"오류: {str(e)}"))
            else:
                self.stdout.write(self.style.ERROR(f"SQL 파일을 찾을 수 없습니다: {sql_file}"))

