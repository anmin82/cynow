"""CF4 YC NULL EndUser 용기의 정책 매칭 확인"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'CF4 YC NULL EndUser 용기의 정책 매칭 확인'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # NULL EndUser 용기의 Raw 값 확인
            self.stdout.write("=== NULL EndUser 용기의 Raw 값 샘플 ===\n")
            cursor.execute("""
                SELECT 
                    c.cylinder_no,
                    c.raw_gas_name,
                    c.raw_capacity,
                    c.raw_valve_spec_code,
                    c.raw_cylinder_spec_code,
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    c.dashboard_enduser
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name LIKE '%CF4%'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_capacity = 440
                  AND c.dashboard_enduser IS NULL
                LIMIT 5
            """)
            
            null_samples = cursor.fetchall()
            for row in null_samples:
                self.stdout.write(f"  용기번호: {row[0]}\n")
                self.stdout.write(f"    Raw 가스: {row[1]}, 용량: {row[2]}, 밸브코드: {row[3]}, 용기코드: {row[4]}\n")
                self.stdout.write(f"    Dashboard 가스: {row[5]}, 용량: {row[6]}, EndUser: {row[7]}\n")
            
            # CF4 EndUser 기본 정책 확인
            self.stdout.write("\n=== CF4 EndUser 기본 정책 ===\n")
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
            
            # NULL EndUser 용기가 정책과 매칭되는지 확인
            if null_samples:
                sample = null_samples[0]
                self.stdout.write(f"\n=== 정책 매칭 테스트 (용기번호: {sample[0]}) ===\n")
                self.stdout.write(f"  Raw 값: 가스={sample[1]}, 용량={sample[2]}, 밸브코드={sample[3]}, 용기코드={sample[4]}\n")
                
                # 정책 매칭 쿼리 (sync_cylinder_current_single과 동일한 로직)
                cursor.execute("""
                    SELECT 
                        id, gas_name, capacity, valve_spec_code, cylinder_spec_code, default_enduser
                    FROM cy_enduser_default 
                    WHERE gas_name = %s 
                      AND (capacity IS NULL OR capacity = %s)
                      AND (valve_spec_code IS NULL OR valve_spec_code = %s)
                      AND (cylinder_spec_code IS NULL OR cylinder_spec_code = %s)
                      AND is_active = TRUE
                    ORDER BY 
                      CASE WHEN capacity IS NOT NULL THEN 1 ELSE 2 END,
                      CASE WHEN valve_spec_code IS NOT NULL THEN 1 ELSE 2 END,
                      CASE WHEN cylinder_spec_code IS NOT NULL THEN 1 ELSE 2 END
                    LIMIT 1
                """, [sample[1], sample[2], sample[3], sample[4]])
                
                matched_policy = cursor.fetchone()
                if matched_policy:
                    self.stdout.write(f"  [매칭됨] 정책 ID={matched_policy[0]}, EndUser={matched_policy[5]}\n")
                else:
                    self.stdout.write(f"  [매칭 안됨] 정책이 없습니다.\n")
            
            # NULL EndUser 용기들의 밸브코드/용기코드 분포 확인
            self.stdout.write("\n=== NULL EndUser 용기의 밸브코드/용기코드 분포 ===\n")
            cursor.execute("""
                SELECT 
                    c.raw_valve_spec_code,
                    c.raw_cylinder_spec_code,
                    COUNT(*) as 수량
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name LIKE '%CF4%'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_capacity = 440
                  AND c.dashboard_enduser IS NULL
                GROUP BY c.raw_valve_spec_code, c.raw_cylinder_spec_code
                ORDER BY 수량 DESC
            """)
            
            distributions = cursor.fetchall()
            for row in distributions:
                self.stdout.write(f"  밸브코드={row[0]}, 용기코드={row[1]}: {row[2]}개\n")










