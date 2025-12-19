"""LGD 예외 용기 재동기화"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'LGD 예외 용기 재동기화'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 1. LGD 예외 용기번호 확인
            self.stdout.write("=== LGD 예외 용기번호 확인 ===\n")
            cursor.execute("""
                SELECT 
                    cylinder_no,
                    LENGTH(cylinder_no) as len,
                    enduser
                FROM cy_enduser_exception
                WHERE enduser = 'LGD'
                  AND is_active = TRUE
                ORDER BY cylinder_no
                LIMIT 10
            """)
            
            exceptions = cursor.fetchall()
            self.stdout.write(f"  LGD 예외: {len(exceptions)}개 (샘플)\n")
            for row in exceptions[:5]:
                self.stdout.write(f"    '{row[0]}' (len={row[1]})\n")
            
            # 2. 예외 용기번호가 CDC에 존재하는지 확인
            self.stdout.write("\n=== 예외 용기번호 CDC 존재 확인 ===\n")
            cursor.execute("""
                SELECT 
                    e.cylinder_no,
                    CASE WHEN mc."CYLINDER_NO" IS NOT NULL THEN 'Y' ELSE 'N' END as in_cdc,
                    mc."CYLINDER_NO" as cdc_cylinder_no
                FROM cy_enduser_exception e
                LEFT JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(e.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE e.enduser = 'LGD'
                  AND e.is_active = TRUE
                ORDER BY e.cylinder_no
                LIMIT 10
            """)
            
            cdc_checks = cursor.fetchall()
            for row in cdc_checks[:5]:
                self.stdout.write(f"    예외 '{row[0]}' -> CDC: {row[1]}, CDC용기번호: '{row[2]}'\n")
            
            # 3. LGD 예외 용기 재동기화
            self.stdout.write("\n=== LGD 예외 용기 재동기화 ===\n")
            cursor.execute("""
                SELECT DISTINCT RTRIM(e.cylinder_no) as cylinder_no
                FROM cy_enduser_exception e
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(e.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE e.enduser = 'LGD'
                  AND e.is_active = TRUE
            """)
            
            lgd_cylinder_nos = [row[0] for row in cursor.fetchall()]
            self.stdout.write(f"  재동기화 대상: {len(lgd_cylinder_nos)}개\n")
            
            success_count = 0
            for i, cylinder_no in enumerate(lgd_cylinder_nos, 1):
                try:
                    cursor.execute("SELECT sync_cylinder_current_single(%s)", [cylinder_no])
                    success_count += 1
                except Exception as e:
                    self.stdout.write(f"  [오류] {cylinder_no}: {str(e)}\n")
            
            self.stdout.write(f"  성공: {success_count}개\n")
            
            # 4. 결과 확인
            self.stdout.write("\n=== 재동기화 후 CF4 YC 용기 현황 ===\n")
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

