"""CF4 YC 용기의 cylinder_type_key 재계산"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'CF4 YC 용기의 cylinder_type_key 재계산 및 업데이트'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # cylinder_type_key 재계산 및 업데이트
            self.stdout.write("=== CF4 YC SDC 용기의 cylinder_type_key 재계산 ===\n")
            
            cursor.execute("""
                UPDATE cy_cylinder_current c
                SET cylinder_type_key = MD5(
                    COALESCE(c.dashboard_gas_name, '') || '|' ||
                    COALESCE(CAST(c.dashboard_capacity AS TEXT), '') || '|' ||
                    COALESCE(c.dashboard_valve_group_name, c.dashboard_valve_spec_name, '') || '|' ||
                    COALESCE(c.dashboard_cylinder_spec_name, '') || '|' ||
                    COALESCE(c.dashboard_enduser, '')
                ),
                snapshot_updated_at = NOW()
                WHERE c.dashboard_gas_name = 'CF4'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_capacity = 440
                  AND c.dashboard_enduser = 'SDC'
                  AND EXISTS (
                      SELECT 1
                      FROM "fcms_cdc"."ma_cylinders" mc
                      WHERE RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                  )
            """)
            
            updated_count = cursor.rowcount
            self.stdout.write(f"  업데이트된 레코드 수: {updated_count}개\n")
            
            # 결과 확인
            self.stdout.write("\n=== 업데이트 후 대시보드 카드 확인 ===\n")
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
                ORDER BY c.dashboard_enduser, c.cylinder_type_key
            """)
            
            cards = cursor.fetchall()
            self.stdout.write(f"  대시보드 카드 수: {len(cards)}개\n")
            total_sdc = 0
            for row in cards:
                self.stdout.write(f"    {row[1]} {row[2]}L {row[3]} | EndUser={row[4]} | 수량={row[5]}개\n")
                if row[4] == 'SDC':
                    total_sdc += row[5]
            
            self.stdout.write(f"\n  SDC 총 수량: {total_sdc}개\n")
            
            # 전체 수량 확인
            self.stdout.write("\n=== 전체 수량 확인 ===\n")
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

