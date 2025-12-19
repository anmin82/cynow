"""CF4 YC 용기의 Raw 값과 Dashboard 값 비교"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'CF4 YC 용기의 Raw 값과 Dashboard 값 비교'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 두 개의 다른 cylinder_type_key를 가진 SDC 용기의 샘플 확인
            self.stdout.write("=== SDC 카드 1 (cylinder_type_key=362701c9c43ad1ef1f6116358659529c) 샘플 ===\n")
            cursor.execute("""
                SELECT 
                    c.cylinder_no,
                    c.raw_gas_name,
                    c.raw_capacity,
                    c.raw_valve_spec_code,
                    c.raw_valve_spec_name,
                    c.raw_cylinder_spec_code,
                    c.raw_cylinder_spec_name,
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_valve_spec_name,
                    c.dashboard_valve_group_name,
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
                LIMIT 3
            """)
            
            samples1 = cursor.fetchall()
            for row in samples1:
                self.stdout.write(f"  용기번호: {row[0]}")
                self.stdout.write(f"    Raw: 가스={row[1]}, 용량={row[2]}, 밸브코드={row[3]}, 밸브명={row[4]}, 용기코드={row[5]}, 용기명={row[6]}")
                self.stdout.write(f"    Dashboard: 가스={row[7]}, 용량={row[8]}, 밸브명={row[9]}, 밸브그룹={row[10]}, 용기명={row[11]}, EndUser={row[12]}")
                self.stdout.write(f"    cylinder_type_key={row[13]}\n")
            
            self.stdout.write("\n=== SDC 카드 2 (cylinder_type_key=9367e39fe029bc81f8c6a8ffed8045f7) 샘플 ===\n")
            cursor.execute("""
                SELECT 
                    c.cylinder_no,
                    c.raw_gas_name,
                    c.raw_capacity,
                    c.raw_valve_spec_code,
                    c.raw_valve_spec_name,
                    c.raw_cylinder_spec_code,
                    c.raw_cylinder_spec_name,
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_valve_spec_name,
                    c.dashboard_valve_group_name,
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
                LIMIT 3
            """)
            
            samples2 = cursor.fetchall()
            for row in samples2:
                self.stdout.write(f"  용기번호: {row[0]}")
                self.stdout.write(f"    Raw: 가스={row[1]}, 용량={row[2]}, 밸브코드={row[3]}, 밸브명={row[4]}, 용기코드={row[5]}, 용기명={row[6]}")
                self.stdout.write(f"    Dashboard: 가스={row[7]}, 용량={row[8]}, 밸브명={row[9]}, 밸브그룹={row[10]}, 용기명={row[11]}, EndUser={row[12]}")
                self.stdout.write(f"    cylinder_type_key={row[13]}\n")
            
            # NULL EndUser 용기 샘플 확인
            self.stdout.write("\n=== NULL EndUser 용기 샘플 ===\n")
            cursor.execute("""
                SELECT 
                    c.cylinder_no,
                    c.raw_gas_name,
                    c.raw_capacity,
                    c.raw_valve_spec_code,
                    c.raw_valve_spec_name,
                    c.raw_cylinder_spec_code,
                    c.raw_cylinder_spec_name,
                    c.dashboard_gas_name,
                    c.dashboard_enduser
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name LIKE '%CF4%'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_enduser IS NULL
                LIMIT 5
            """)
            
            null_samples = cursor.fetchall()
            for row in null_samples:
                self.stdout.write(f"  용기번호: {row[0]}, Raw 가스={row[1]}, Raw 용량={row[2]}, Raw 밸브코드={row[3]}, Raw 용기코드={row[5]}, Dashboard 가스={row[7]}, EndUser={row[8]}\n")
            
            # EndUser 기본 정책 확인
            self.stdout.write("\n=== CF4 EndUser 기본 정책 확인 ===\n")
            cursor.execute("""
                SELECT 
                    id, gas_name, capacity, valve_spec_code, cylinder_spec_code, default_enduser, is_active
                FROM cy_enduser_default
                WHERE gas_name LIKE '%CF4%'
                  AND is_active = TRUE
                ORDER BY 
                    CASE WHEN capacity IS NOT NULL THEN 1 ELSE 2 END,
                    CASE WHEN valve_spec_code IS NOT NULL THEN 1 ELSE 2 END,
                    CASE WHEN cylinder_spec_code IS NOT NULL THEN 1 ELSE 2 END
            """)
            
            policies = cursor.fetchall()
            if not policies:
                self.stdout.write("  [없음] CF4에 대한 EndUser 기본 정책이 없습니다.\n")
            else:
                for row in policies:
                    self.stdout.write(f"  ID={row[0]}, 가스={row[1]}, 용량={row[2]}, 밸브코드={row[3]}, 용기코드={row[4]}, EndUser={row[5]}, 활성={row[6]}\n")










