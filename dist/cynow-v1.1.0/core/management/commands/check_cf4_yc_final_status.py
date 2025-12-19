"""CF4 YC 용기 최종 상태 확인"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'CF4 YC 용기 최종 상태 확인'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 전체 CF4 YC 용기 수량 확인
            self.stdout.write("=== CF4 YC 용기 전체 현황 ===\n")
            cursor.execute("""
                SELECT 
                    COALESCE(c.dashboard_enduser::text, 'NULL') as enduser_display,
                    COUNT(*) as 수량
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name = 'CF4'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_capacity = 440
                GROUP BY c.dashboard_enduser
                ORDER BY c.dashboard_enduser NULLS LAST
            """)
            
            results = cursor.fetchall()
            total = 0
            for row in results:
                self.stdout.write(f"  EndUser={row[0]}: {row[1]}개\n")
                total += row[1]
            self.stdout.write(f"\n  총 수량: {total}개\n")
            
            # EndUser 예외 확인
            self.stdout.write("\n=== CF4 YC EndUser 예외 (LGD) ===\n")
            cursor.execute("""
                SELECT COUNT(*) as 수량
                FROM cy_enduser_exception
                WHERE RTRIM(cylinder_no) IN (
                    SELECT RTRIM(cylinder_no) 
                    FROM cy_cylinder_current 
                    WHERE dashboard_gas_name = 'CF4'
                      AND dashboard_cylinder_spec_name LIKE '%YC%'
                      AND dashboard_capacity = 440
                ) AND is_active = TRUE
                  AND enduser = 'LGD'
            """)
            
            exception_count = cursor.fetchone()[0]
            self.stdout.write(f"  LGD 예외 등록: {exception_count}개\n")
            
            # 실제 LGD 용기 확인
            cursor.execute("""
                SELECT COUNT(*) as 수량
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name = 'CF4'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_capacity = 440
                  AND c.dashboard_enduser = 'LGD'
            """)
            
            lgd_count = cursor.fetchone()[0]
            self.stdout.write(f"  실제 LGD 용기: {lgd_count}개\n")
            
            # SDC 용기 확인
            cursor.execute("""
                SELECT COUNT(*) as 수량
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name = 'CF4'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_capacity = 440
                  AND c.dashboard_enduser = 'SDC'
            """)
            
            sdc_count = cursor.fetchone()[0]
            self.stdout.write(f"  실제 SDC 용기: {sdc_count}개\n")
            
            # 정책 확인
            self.stdout.write("\n=== CF4 YC EndUser 기본 정책 ===\n")
            cursor.execute("""
                SELECT 
                    id, gas_name, capacity, valve_spec_code, cylinder_spec_code, default_enduser, is_active
                FROM cy_enduser_default
                WHERE gas_name = 'CF4'
                  AND capacity = 440
                  AND is_active = TRUE
                ORDER BY 
                    CASE WHEN valve_spec_code IS NOT NULL THEN 1 ELSE 2 END,
                    CASE WHEN cylinder_spec_code IS NOT NULL THEN 1 ELSE 2 END
            """)
            
            policies = cursor.fetchall()
            for row in policies:
                self.stdout.write(f"  ID={row[0]}, 가스={row[1]}, 용량={row[2]}, 밸브코드={row[3]}, 용기코드={row[4]}, EndUser={row[5]}, 활성={row[6]}\n")
            
            # 밸브코드별 분포 확인
            self.stdout.write("\n=== CF4 YC 용기 밸브코드별 분포 ===\n")
            cursor.execute("""
                SELECT 
                    c.raw_valve_spec_code,
                    COALESCE(c.dashboard_enduser::text, 'NULL') as enduser_display,
                    COUNT(*) as 수량
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name = 'CF4'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_capacity = 440
                GROUP BY c.raw_valve_spec_code, c.dashboard_enduser
                ORDER BY c.raw_valve_spec_code, c.dashboard_enduser
            """)
            
            distributions = cursor.fetchall()
            for row in distributions:
                self.stdout.write(f"  밸브코드={row[0]}, EndUser={row[1]}: {row[2]}개\n")

