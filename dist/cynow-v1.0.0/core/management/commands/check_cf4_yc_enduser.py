"""CF4 YC 용기의 EndUser 확인"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'CF4 YC 용기의 EndUser 예외 및 대시보드 카드 확인'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 1. CF4 YC 용기의 EndUser 예외 확인
            self.stdout.write("=== CF4 YC 용기 EndUser 예외 ===\n")
            cursor.execute("""
                SELECT 
                    id,
                    cylinder_no,
                    enduser,
                    is_active
                FROM cy_enduser_exception
                WHERE RTRIM(cylinder_no) IN (
                    SELECT RTRIM(cylinder_no) 
                    FROM cy_cylinder_current 
                    WHERE dashboard_gas_name LIKE '%CF4%'
                      AND dashboard_cylinder_spec_name LIKE '%YC%'
                )
                  AND is_active = TRUE
                ORDER BY enduser, cylinder_no
            """)
            
            exceptions = cursor.fetchall()
            if not exceptions:
                self.stdout.write("  [없음] CF4 YC 용기에 대한 EndUser 예외가 없습니다.\n")
            else:
                self.stdout.write(f"  CF4 YC 용기 EndUser 예외: {len(exceptions)}개\n")
                lgd_count = 0
                for row in exceptions:
                    if row[2] == 'LGD':
                        lgd_count += 1
                    self.stdout.write(f"    {row[1]}: {row[2]}")
                self.stdout.write(f"\n  LGD 예외: {lgd_count}개")
            
            # 2. cy_cylinder_current에서 CF4 YC 용기의 실제 EndUser 확인
            self.stdout.write("\n=== cy_cylinder_current에서 CF4 YC 용기 EndUser ===\n")
            cursor.execute("""
                SELECT 
                    dashboard_gas_name,
                    dashboard_capacity,
                    dashboard_cylinder_spec_name,
                    COALESCE(dashboard_enduser::text, 'NULL') as enduser_display,
                    COUNT(*) as 수량
                FROM cy_cylinder_current
                WHERE dashboard_gas_name LIKE '%CF4%'
                  AND dashboard_cylinder_spec_name LIKE '%YC%'
                GROUP BY 
                    dashboard_gas_name,
                    dashboard_capacity,
                    dashboard_cylinder_spec_name,
                    dashboard_enduser
                ORDER BY dashboard_enduser NULLS LAST
            """)
            
            results = cursor.fetchall()
            if not results:
                self.stdout.write("  [없음] CF4 YC 용기 데이터가 없습니다.\n")
            else:
                total = 0
                for row in results:
                    self.stdout.write(f"  {row[0]} {row[1]}L {row[2]}: EndUser={row[3]}, 수량={row[4]}개")
                    total += row[4]
                self.stdout.write(f"\n  총 수량: {total}개")
            
            # 3. 대시보드 카드 그룹화 확인 (cylinder_type_key 기준)
            self.stdout.write("\n=== 대시보드 카드 그룹화 확인 ===\n")
            cursor.execute("""
                SELECT 
                    c.cylinder_type_key,
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_enduser,
                    COUNT(*) as qty,
                    SUM(CASE WHEN c.is_available THEN 1 ELSE 0 END) as available_qty
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
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_enduser
                ORDER BY c.dashboard_enduser
            """)
            
            cards = cursor.fetchall()
            if not cards:
                self.stdout.write("  [없음] 대시보드 카드가 없습니다.\n")
            else:
                self.stdout.write(f"  대시보드 카드 수: {len(cards)}개\n")
                for row in cards:
                    self.stdout.write(f"    카드: {row[1]} {row[2]}L {row[3]} | EndUser={row[4]} | 총={row[5]}개, 가용={row[6]}개")

