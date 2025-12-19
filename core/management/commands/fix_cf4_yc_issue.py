"""CF4 YC 용기 문제 해결"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'CF4 YC 용기 문제 해결: NULL EndUser 정책 추가 및 cylinder_type_key 재계산'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 1. NULL EndUser 용기들을 위한 정책 추가 (밸브코드 0000000006)
            self.stdout.write("=== CF4 YC NULL EndUser 용기를 위한 정책 추가 ===\n")
            
            # 기존 정책 확인
            cursor.execute("""
                SELECT id, gas_name, capacity, valve_spec_code, cylinder_spec_code, default_enduser
                FROM cy_enduser_default
                WHERE gas_name = 'CF4'
                  AND capacity = 440
                  AND valve_spec_code = '0000000006'
                  AND cylinder_spec_code = '0000000006'
                  AND is_active = TRUE
            """)
            
            existing_policy = cursor.fetchone()
            if existing_policy:
                self.stdout.write(f"  [이미 존재] 정책 ID={existing_policy[0]}, EndUser={existing_policy[5]}\n")
            else:
                # 새 정책 추가
                cursor.execute("""
                    INSERT INTO cy_enduser_default (gas_name, capacity, valve_spec_code, cylinder_spec_code, default_enduser, is_active, created_at, updated_at)
                    VALUES ('CF4', 440, '0000000006', '0000000006', 'SDC', TRUE, NOW(), NOW())
                    RETURNING id
                """)
                new_policy_id = cursor.fetchone()[0]
                self.stdout.write(f"  [추가됨] 정책 ID={new_policy_id}, EndUser=SDC\n")
            
            # 2. NULL EndUser 용기들 재동기화
            self.stdout.write("\n=== NULL EndUser 용기 재동기화 ===\n")
            cursor.execute("""
                SELECT DISTINCT RTRIM(c."CYLINDER_NO") as cylinder_no
                FROM "fcms_cdc"."ma_cylinders" c
                INNER JOIN "fcms_cdc"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
                INNER JOIN "fcms_cdc"."ma_cylinder_specs" cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
                WHERE COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') = 'CF4'
                  AND cs."NAME" LIKE '%YC%'
                  AND c."CAPACITY" = 440
                  AND c."VALVE_SPEC_CODE" = '0000000006'
                  AND c."CYLINDER_SPEC_CODE" = '0000000006'
            """)
            
            null_cylinder_nos = [row[0] for row in cursor.fetchall()]
            self.stdout.write(f"  재동기화 대상: {len(null_cylinder_nos)}개 용기\n")
            
            success_count = 0
            for i, cylinder_no in enumerate(null_cylinder_nos, 1):
                try:
                    cursor.execute("SELECT sync_cylinder_current_single(%s)", [cylinder_no])
                    success_count += 1
                    if i % 20 == 0:
                        self.stdout.write(f"  진행 중: {i}/{len(null_cylinder_nos)}...\n")
                except Exception as e:
                    self.stdout.write(f"  [오류] {cylinder_no}: {str(e)}\n")
            
            self.stdout.write(f"  성공: {success_count}개\n")
            
            # 3. 모든 CF4 YC 용기 재동기화 (cylinder_type_key 재계산)
            self.stdout.write("\n=== 모든 CF4 YC 용기 재동기화 (cylinder_type_key 재계산) ===\n")
            cursor.execute("""
                SELECT DISTINCT RTRIM(c."CYLINDER_NO") as cylinder_no
                FROM "fcms_cdc"."ma_cylinders" c
                INNER JOIN "fcms_cdc"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
                INNER JOIN "fcms_cdc"."ma_cylinder_specs" cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
                WHERE COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') = 'CF4'
                  AND cs."NAME" LIKE '%YC%'
                  AND c."CAPACITY" = 440
            """)
            
            all_cylinder_nos = [row[0] for row in cursor.fetchall()]
            self.stdout.write(f"  재동기화 대상: {len(all_cylinder_nos)}개 용기\n")
            
            success_count = 0
            for i, cylinder_no in enumerate(all_cylinder_nos, 1):
                try:
                    cursor.execute("SELECT sync_cylinder_current_single(%s)", [cylinder_no])
                    success_count += 1
                    if i % 20 == 0:
                        self.stdout.write(f"  진행 중: {i}/{len(all_cylinder_nos)}...\n")
                except Exception as e:
                    self.stdout.write(f"  [오류] {cylinder_no}: {str(e)}\n")
            
            self.stdout.write(f"  성공: {success_count}개\n")
            
            # 4. 최종 결과 확인
            self.stdout.write("\n=== 최종 결과 확인 ===\n")
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
                WHERE c.dashboard_gas_name = 'CF4'
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
            self.stdout.write("\n=== 대시보드 카드 확인 ===\n")
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
                WHERE c.dashboard_gas_name = 'CF4'
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










