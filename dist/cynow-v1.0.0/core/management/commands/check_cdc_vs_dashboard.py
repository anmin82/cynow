"""CDC 실제 데이터 vs 대시보드 수량 비교"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'CDC 실제 데이터 vs 대시보드 수량 비교'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 1. fcms_cdc.ma_cylinders 실제 용기 수 (CF4 YC 440L)
            self.stdout.write("=== fcms_cdc.ma_cylinders 실제 용기 수 ===\n")
            cursor.execute("""
                SELECT COUNT(*) as 수량
                FROM "fcms_cdc"."ma_cylinders" c
                INNER JOIN "fcms_cdc"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
                INNER JOIN "fcms_cdc"."ma_cylinder_specs" cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
                WHERE COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') = 'CF4'
                  AND cs."NAME" LIKE '%YC%'
                  AND c."CAPACITY" = 440
            """)
            
            cdc_count = cursor.fetchone()[0]
            self.stdout.write(f"  CF4 YC 440L 실제 용기: {cdc_count}개\n")
            
            # 2. cy_cylinder_current 테이블의 CF4 YC 440L 용기 수
            self.stdout.write("\n=== cy_cylinder_current 테이블 용기 수 ===\n")
            cursor.execute("""
                SELECT COUNT(*) as 수량
                FROM cy_cylinder_current c
                WHERE c.dashboard_gas_name = 'CF4'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_capacity = 440
            """)
            
            snapshot_count = cursor.fetchone()[0]
            self.stdout.write(f"  CF4 YC 440L 스냅샷: {snapshot_count}개\n")
            
            # 3. 고아 데이터 확인 (cy_cylinder_current에만 있고 fcms_cdc.ma_cylinders에 없는 것)
            self.stdout.write("\n=== 고아 데이터 확인 ===\n")
            cursor.execute("""
                SELECT COUNT(*) as 수량
                FROM cy_cylinder_current c
                WHERE c.dashboard_gas_name = 'CF4'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_capacity = 440
                  AND NOT EXISTS (
                      SELECT 1
                      FROM "fcms_cdc"."ma_cylinders" mc
                      WHERE RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                  )
            """)
            
            orphan_count = cursor.fetchone()[0]
            self.stdout.write(f"  고아 데이터 (CDC에 없는 용기): {orphan_count}개\n")
            
            # 4. 고아 데이터 샘플
            if orphan_count > 0:
                self.stdout.write("\n=== 고아 데이터 샘플 (최대 10개) ===\n")
                cursor.execute("""
                    SELECT 
                        c.cylinder_no,
                        c.dashboard_gas_name,
                        c.dashboard_capacity,
                        c.dashboard_enduser,
                        c.snapshot_updated_at
                    FROM cy_cylinder_current c
                    WHERE c.dashboard_gas_name = 'CF4'
                      AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                      AND c.dashboard_capacity = 440
                      AND NOT EXISTS (
                          SELECT 1
                          FROM "fcms_cdc"."ma_cylinders" mc
                          WHERE RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                      )
                    LIMIT 10
                """)
                
                orphans = cursor.fetchall()
                for row in orphans:
                    self.stdout.write(f"  {row[0]}: {row[1]} {row[2]}L, EndUser={row[3]}, 업데이트={row[4]}\n")
            
            # 5. 전체 용기 수량 비교
            self.stdout.write("\n=== 전체 용기 수량 비교 ===\n")
            cursor.execute("""
                SELECT COUNT(*) FROM "fcms_cdc"."ma_cylinders"
            """)
            total_cdc = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM cy_cylinder_current
            """)
            total_snapshot = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) 
                FROM cy_cylinder_current c
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM "fcms_cdc"."ma_cylinders" mc
                    WHERE RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                )
            """)
            total_orphan = cursor.fetchone()[0]
            
            self.stdout.write(f"  fcms_cdc.ma_cylinders 전체: {total_cdc}개\n")
            self.stdout.write(f"  cy_cylinder_current 전체: {total_snapshot}개\n")
            self.stdout.write(f"  고아 데이터 전체: {total_orphan}개\n")
            self.stdout.write(f"  차이: {total_snapshot - total_cdc}개\n")

