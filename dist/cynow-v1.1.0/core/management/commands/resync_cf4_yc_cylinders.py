"""CF4 YC 용기 재동기화"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'CF4 YC 용기 재동기화하여 cylinder_type_key 재계산'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # CF4 YC 용기 목록 조회
            self.stdout.write("=== CF4 YC 용기 재동기화 시작 ===\n")
            cursor.execute("""
                SELECT DISTINCT RTRIM(c."CYLINDER_NO") as cylinder_no
                FROM "fcms_cdc"."ma_cylinders" c
                INNER JOIN "fcms_cdc"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
                INNER JOIN "fcms_cdc"."ma_cylinder_specs" cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
                WHERE COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') LIKE '%CF4%'
                  AND cs."NAME" LIKE '%YC%'
                  AND c."CAPACITY" = 440
            """)
            
            cylinder_nos = [row[0] for row in cursor.fetchall()]
            self.stdout.write(f"  재동기화 대상: {len(cylinder_nos)}개 용기\n")
            
            # 각 용기 재동기화
            success_count = 0
            error_count = 0
            
            for i, cylinder_no in enumerate(cylinder_nos, 1):
                try:
                    cursor.execute("SELECT sync_cylinder_current_single(%s)", [cylinder_no])
                    success_count += 1
                    if i % 20 == 0:
                        self.stdout.write(f"  진행 중: {i}/{len(cylinder_nos)}...\n")
                except Exception as e:
                    error_count += 1
                    self.stdout.write(f"  [오류] {cylinder_no}: {str(e)}\n")
            
            self.stdout.write(f"\n=== 재동기화 완료 ===\n")
            self.stdout.write(f"  성공: {success_count}개\n")
            self.stdout.write(f"  실패: {error_count}개\n")
            
            # 재동기화 후 결과 확인
            self.stdout.write("\n=== 재동기화 후 CF4 YC 용기 EndUser 확인 ===\n")
            cursor.execute("""
                SELECT 
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_cylinder_spec_name,
                    COALESCE(c.dashboard_enduser::text, 'NULL') as enduser_display,
                    COUNT(*) as 수량
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name LIKE '%CF4%'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_capacity = 440
                GROUP BY 
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_enduser
                ORDER BY c.dashboard_enduser NULLS LAST
            """)
            
            results = cursor.fetchall()
            total = 0
            for row in results:
                self.stdout.write(f"  {row[0]} {row[1]}L {row[2]}: EndUser={row[3]}, 수량={row[4]}개\n")
                total += row[4]
            self.stdout.write(f"\n  총 수량: {total}개\n")
            
            # 대시보드 카드 확인
            self.stdout.write("\n=== 재동기화 후 대시보드 카드 확인 ===\n")
            cursor.execute("""
                SELECT 
                    c.cylinder_type_key,
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_enduser,
                    COUNT(*) as qty
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name LIKE '%CF4%'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_capacity = 440
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
            self.stdout.write(f"  대시보드 카드 수: {len(cards)}개\n")
            for row in cards:
                self.stdout.write(f"    {row[1]} {row[2]}L {row[3]} | EndUser={row[4]} | 수량={row[5]}개\n")

