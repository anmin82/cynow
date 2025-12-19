"""CF4 YC 용기의 cylinder_type_key 간단 확인"""
from django.core.management.base import BaseCommand
from django.db import connection
import hashlib


class Command(BaseCommand):
    help = 'CF4 YC 용기의 cylinder_type_key 간단 확인'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 각 cylinder_type_key별 샘플 확인
            self.stdout.write("=== SDC 카드별 샘플 확인 ===\n")
            cursor.execute("""
                SELECT 
                    c.cylinder_type_key,
                    COUNT(*) as qty,
                    MIN(c.cylinder_no) as sample_cylinder_no,
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_valve_group_name,
                    c.dashboard_valve_spec_name,
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_enduser
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name = 'CF4'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_capacity = 440
                  AND c.dashboard_enduser = 'SDC'
                GROUP BY 
                    c.cylinder_type_key,
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_valve_group_name,
                    c.dashboard_valve_spec_name,
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_enduser
                ORDER BY qty DESC
            """)
            
            cards = cursor.fetchall()
            for idx, row in enumerate(cards, 1):
                self.stdout.write(f"\n  카드 {idx}: 수량={row[1]}개, cylinder_type_key={row[0]}\n")
                self.stdout.write(f"    샘플 용기번호: {row[2]}\n")
                self.stdout.write(f"    dashboard_gas_name: '{row[3]}'\n")
                self.stdout.write(f"    dashboard_capacity: {row[4]}\n")
                self.stdout.write(f"    dashboard_valve_group_name: {row[5]}\n")
                self.stdout.write(f"    dashboard_valve_spec_name: '{row[6]}'\n")
                self.stdout.write(f"    dashboard_cylinder_spec_name: '{row[7]}'\n")
                self.stdout.write(f"    dashboard_enduser: '{row[8]}'\n")
                
                # Key String 생성
                key_string = (
                    (row[3] or '') + '|' +
                    (str(row[4]) if row[4] is not None else '') + '|' +
                    (row[5] or row[6] or '') + '|' +
                    (row[7] or '') + '|' +
                    (row[8] or '')
                )
                calculated_key = hashlib.md5(key_string.encode('utf-8')).hexdigest()
                self.stdout.write(f"    Key String: '{key_string}'\n")
                self.stdout.write(f"    Calculated Key: {calculated_key}\n")
                self.stdout.write(f"    Actual Key: {row[0]}\n")
                self.stdout.write(f"    Match: {'YES' if calculated_key == row[0] else 'NO'}\n")
                
                # 실제 샘플 용기의 상세 값 확인
                cursor.execute("""
                    SELECT 
                        c.cylinder_no,
                        c.dashboard_gas_name,
                        c.dashboard_capacity,
                        c.dashboard_valve_group_name,
                        c.dashboard_valve_spec_name,
                        c.dashboard_cylinder_spec_name,
                        c.dashboard_enduser,
                        c.cylinder_type_key,
                        -- Raw 값도 확인
                        c.raw_gas_name,
                        c.raw_capacity,
                        c.raw_valve_spec_code,
                        c.raw_valve_spec_name,
                        c.raw_cylinder_spec_code,
                        c.raw_cylinder_spec_name
                    FROM cy_cylinder_current c
                    WHERE c.cylinder_no = %s
                """, [row[2]])
                
                sample = cursor.fetchone()
                if sample:
                    self.stdout.write(f"    [상세] Raw 가스={sample[8]}, Raw 용량={sample[9]}, Raw 밸브코드={sample[10]}, Raw 밸브명={sample[11]}, Raw 용기코드={sample[12]}, Raw 용기명={sample[13]}\n")

