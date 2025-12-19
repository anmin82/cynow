"""CF4 YC 용기의 cylinder_type_key 구성 요소 확인"""
from django.core.management.base import BaseCommand
from django.db import connection
import hashlib


class Command(BaseCommand):
    help = 'CF4 YC 용기의 cylinder_type_key 구성 요소 확인'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # cylinder_type_key 생성에 사용되는 값들 확인
            self.stdout.write("=== SDC 카드 1 (cylinder_type_key=362701c9c43ad1ef1f6116358659529c) 구성 요소 ===\n")
            cursor.execute("""
                SELECT 
                    c.cylinder_no,
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_valve_group_name,
                    c.dashboard_valve_spec_name,
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_enduser,
                    c.cylinder_type_key
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name LIKE '%CF4%'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_enduser = 'SDC'
                  AND c.cylinder_type_key = '362701c9c43ad1ef1f6116358659529c'
                LIMIT 1
            """)
            
            row1 = cursor.fetchone()
            if row1:
                key_string1 = (
                    (row1[1] or '') + '|' +
                    (str(row1[2]) if row1[2] is not None else '') + '|' +
                    (row1[3] or row1[4] or '') + '|' +
                    (row1[5] or '') + '|' +
                    (row1[6] or '')
                )
                calculated_key1 = hashlib.md5(key_string1.encode('utf-8')).hexdigest()
                self.stdout.write(f"  용기번호: {row1[0]}\n")
                self.stdout.write(f"    dashboard_gas_name: '{row1[1]}'\n")
                self.stdout.write(f"    dashboard_capacity: {row1[2]}\n")
                self.stdout.write(f"    dashboard_valve_group_name: {row1[3]}\n")
                self.stdout.write(f"    dashboard_valve_spec_name: '{row1[4]}'\n")
                self.stdout.write(f"    dashboard_cylinder_spec_name: '{row1[5]}'\n")
                self.stdout.write(f"    dashboard_enduser: '{row1[6]}'\n")
                self.stdout.write(f"    Key String: '{key_string1}'\n")
                self.stdout.write(f"    Calculated Key: {calculated_key1}\n")
                self.stdout.write(f"    Actual Key: {row1[7]}\n")
                self.stdout.write(f"    Match: {'YES' if calculated_key1 == row1[7] else 'NO'}\n")
            
            self.stdout.write("\n=== SDC 카드 2 (cylinder_type_key=9367e39fe029bc81f8c6a8ffed8045f7) 구성 요소 ===\n")
            cursor.execute("""
                SELECT 
                    c.cylinder_no,
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_valve_group_name,
                    c.dashboard_valve_spec_name,
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_enduser,
                    c.cylinder_type_key
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name LIKE '%CF4%'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_enduser = 'SDC'
                  AND c.cylinder_type_key = '9367e39fe029bc81f8c6a8ffed8045f7'
                LIMIT 1
            """)
            
            row2 = cursor.fetchone()
            if row2:
                key_string2 = (
                    (row2[1] or '') + '|' +
                    (str(row2[2]) if row2[2] is not None else '') + '|' +
                    (row2[3] or row2[4] or '') + '|' +
                    (row2[5] or '') + '|' +
                    (row2[6] or '')
                )
                calculated_key2 = hashlib.md5(key_string2.encode('utf-8')).hexdigest()
                self.stdout.write(f"  용기번호: {row2[0]}\n")
                self.stdout.write(f"    dashboard_gas_name: '{row2[1]}'\n")
                self.stdout.write(f"    dashboard_capacity: {row2[2]}\n")
                self.stdout.write(f"    dashboard_valve_group_name: {row2[3]}\n")
                self.stdout.write(f"    dashboard_valve_spec_name: '{row2[4]}'\n")
                self.stdout.write(f"    dashboard_cylinder_spec_name: '{row2[5]}'\n")
                self.stdout.write(f"    dashboard_enduser: '{row2[6]}'\n")
                self.stdout.write(f"    Key String: '{key_string2}'\n")
                self.stdout.write(f"    Calculated Key: {calculated_key2}\n")
                self.stdout.write(f"    Actual Key: {row2[7]}\n")
                self.stdout.write(f"    Match: {'YES' if calculated_key2 == row2[7] else 'NO'}\n")
            
            # 두 카드의 차이점 비교
            if row1 and row2:
                self.stdout.write("\n=== 두 카드의 차이점 ===\n")
                self.stdout.write(f"  dashboard_gas_name: '{row1[1]}' vs '{row2[1]}' - {'SAME' if row1[1] == row2[1] else 'DIFFERENT'}\n")
                self.stdout.write(f"  dashboard_capacity: {row1[2]} vs {row2[2]} - {'SAME' if row1[2] == row2[2] else 'DIFFERENT'}\n")
                self.stdout.write(f"  dashboard_valve_group_name: {row1[3]} vs {row2[3]} - {'SAME' if row1[3] == row2[3] else 'DIFFERENT'}\n")
                self.stdout.write(f"  dashboard_valve_spec_name: '{row1[4]}' vs '{row2[4]}' - {'SAME' if row1[4] == row2[4] else 'DIFFERENT'}\n")
                self.stdout.write(f"  dashboard_cylinder_spec_name: '{row1[5]}' vs '{row2[5]}' - {'SAME' if row1[5] == row2[5] else 'DIFFERENT'}\n")
                self.stdout.write(f"  dashboard_enduser: '{row1[6]}' vs '{row2[6]}' - {'SAME' if row1[6] == row2[6] else 'DIFFERENT'}\n")
                
                # 실제로 cylinder_type_key 생성에 사용되는 값 확인
                valve_component1 = row1[3] or row1[4] or ''
                valve_component2 = row2[3] or row2[4] or ''
                self.stdout.write(f"\n  cylinder_type_key에 사용되는 밸브 값: '{valve_component1}' vs '{valve_component2}' - {'SAME' if valve_component1 == valve_component2 else 'DIFFERENT'}\n")
            
            # 총 수량 확인
            self.stdout.write("\n=== CF4 YC 용기 총 수량 확인 ===\n")
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_count,
                    COUNT(CASE WHEN c.dashboard_enduser = 'LGD' THEN 1 END) as lgd_count,
                    COUNT(CASE WHEN c.dashboard_enduser = 'SDC' THEN 1 END) as sdc_count,
                    COUNT(CASE WHEN c.dashboard_enduser IS NULL THEN 1 END) as null_count
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name LIKE '%CF4%'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_capacity = 440
            """)
            
            count_row = cursor.fetchone()
            if count_row:
                self.stdout.write(f"  총 수량: {count_row[0]}개\n")
                self.stdout.write(f"  LGD: {count_row[1]}개\n")
                self.stdout.write(f"  SDC: {count_row[2]}개\n")
                self.stdout.write(f"  NULL: {count_row[3]}개\n")

