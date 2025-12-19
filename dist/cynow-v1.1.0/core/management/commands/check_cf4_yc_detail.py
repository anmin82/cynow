"""CF4 YC 용기의 상세 정보 확인"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'CF4 YC 용기의 밸브 스펙별 EndUser 확인'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # CF4 YC 용기의 밸브 스펙별 EndUser 확인
            self.stdout.write("=== CF4 YC 용기 밸브 스펙별 EndUser ===\n")
            cursor.execute("""
                SELECT 
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_valve_spec_name,
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_enduser,
                    COUNT(*) as 수량
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name LIKE '%CF4%'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_enduser IS NOT NULL
                GROUP BY 
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_valve_spec_name,
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_enduser
                ORDER BY c.dashboard_enduser, c.dashboard_valve_spec_name
            """)
            
            results = cursor.fetchall()
            if not results:
                self.stdout.write("  [없음] CF4 YC 용기 데이터가 없습니다.\n")
            else:
                for row in results:
                    self.stdout.write(f"  {row[0]} {row[1]}L | 밸브={row[2]} | 용기={row[3]} | EndUser={row[4]} | 수량={row[5]}개")
            
            # 대시보드 카드 그룹화 확인 (cylinder_type_key 기준)
            self.stdout.write("\n=== 대시보드 카드 그룹화 확인 (cylinder_type_key) ===\n")
            cursor.execute("""
                SELECT 
                    c.cylinder_type_key,
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_valve_spec_name,
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_enduser,
                    COUNT(*) as qty
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name LIKE '%CF4%'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_enduser IS NOT NULL
                GROUP BY 
                    c.cylinder_type_key,
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_valve_spec_name,
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_enduser
                ORDER BY c.dashboard_enduser, c.cylinder_type_key
            """)
            
            cards = cursor.fetchall()
            if not cards:
                self.stdout.write("  [없음] 대시보드 카드가 없습니다.\n")
            else:
                self.stdout.write(f"  대시보드 카드 수: {len(cards)}개\n")
                for row in cards:
                    self.stdout.write(f"    cylinder_type_key={row[0]} | {row[1]} {row[2]}L | 밸브={row[3]} | EndUser={row[4]} | 수량={row[5]}개")

