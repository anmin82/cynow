"""COS 가스의 EndUser 확인"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'COS 가스의 EndUser 정책 및 실제 데이터 확인'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 1. COS 가스의 EndUser 정책 확인
            self.stdout.write("=== COS 가스 EndUser 정책 ===\n")
            cursor.execute("""
                SELECT 
                    id,
                    gas_name,
                    capacity,
                    valve_spec_code,
                    cylinder_spec_code,
                    default_enduser,
                    is_active
                FROM cy_enduser_default
                WHERE gas_name = 'COS'
                  AND is_active = TRUE
                ORDER BY id
            """)
            
            policies = cursor.fetchall()
            if not policies:
                self.stdout.write("  [없음] COS 가스에 대한 EndUser 기본 정책이 없습니다.\n")
            else:
                for row in policies:
                    self.stdout.write(f"  ID {row[0]}: {row[1]} | 용량={row[2]}, 밸브={row[3]}, 용기={row[4]}, EndUser={row[5]}, 활성={row[6]}")
            
            # 2. COS 가스의 EndUser 예외 확인
            cursor.execute("""
                SELECT 
                    id,
                    cylinder_no,
                    enduser,
                    is_active
                FROM cy_enduser_exception
                WHERE cylinder_no IN (
                    SELECT cylinder_no 
                    FROM cy_cylinder_current 
                    WHERE dashboard_gas_name = 'COS'
                )
                  AND is_active = TRUE
                ORDER BY cylinder_no
            """)
            
            exceptions = cursor.fetchall()
            if not exceptions:
                self.stdout.write("\n  [없음] COS 가스에 대한 EndUser 예외가 없습니다.\n")
            else:
                self.stdout.write(f"\n  COS 가스 EndUser 예외: {len(exceptions)}개\n")
                for row in exceptions:
                    self.stdout.write(f"    {row[1]}: {row[2]}")
            
            # 3. cy_cylinder_current에서 COS 가스의 실제 EndUser 확인
            self.stdout.write("\n=== cy_cylinder_current에서 COS 가스 EndUser ===\n")
            cursor.execute("""
                SELECT 
                    dashboard_gas_name,
                    COALESCE(dashboard_enduser::text, 'NULL') as enduser_display,
                    COUNT(*) as 수량
                FROM cy_cylinder_current
                WHERE dashboard_gas_name = 'COS'
                GROUP BY dashboard_gas_name, dashboard_enduser
                ORDER BY dashboard_enduser NULLS LAST
            """)
            
            results = cursor.fetchall()
            if not results:
                self.stdout.write("  [없음] COS 가스 데이터가 없습니다.\n")
            else:
                for row in results:
                    self.stdout.write(f"  {row[0]}: EndUser={row[1]}, 수량={row[2]}개")
            
            # 4. COS 가스의 스펙별 EndUser 확인
            self.stdout.write("\n=== COS 가스 스펙별 EndUser ===\n")
            cursor.execute("""
                SELECT 
                    dashboard_capacity,
                    dashboard_valve_spec_name,
                    dashboard_cylinder_spec_name,
                    dashboard_enduser,
                    COUNT(*) as 수량
                FROM cy_cylinder_current
                WHERE dashboard_gas_name = 'COS'
                GROUP BY 
                    dashboard_capacity,
                    dashboard_valve_spec_name,
                    dashboard_cylinder_spec_name,
                    dashboard_enduser
                ORDER BY dashboard_enduser, dashboard_capacity
            """)
            
            results = cursor.fetchall()
            if not results:
                self.stdout.write("  [없음] COS 가스 데이터가 없습니다.\n")
            else:
                for row in results:
                    self.stdout.write(f"  용량={row[0]}, 밸브={row[1]}, 용기={row[2]}, EndUser={row[3]}, 수량={row[4]}개")
            
            # 5. COS 가스의 EndUser 결정 로직 확인 (정책 매칭)
            self.stdout.write("\n=== COS 가스 정책 매칭 확인 ===\n")
            cursor.execute("""
                SELECT 
                    c.cylinder_no,
                    c.dashboard_capacity,
                    c.dashboard_valve_spec_code,
                    c.dashboard_cylinder_spec_code,
                    c.dashboard_enduser,
                    CASE 
                        WHEN c.dashboard_capacity = '47' 
                         AND c.dashboard_valve_spec_code = '0000000005'
                         AND c.dashboard_cylinder_spec_code = '0000000002'
                        THEN '정책 매칭 (SEC)'
                        ELSE '정책 미매칭 (기본값 SDC)'
                    END as 정책매칭여부
                FROM cy_cylinder_current c
                WHERE c.dashboard_gas_name = 'COS'
                  AND c.dashboard_enduser = 'SDC'
                LIMIT 10
            """)
            
            samples = cursor.fetchall()
            if samples:
                self.stdout.write("  SDC로 표시된 COS 용기 샘플 (최대 10개):\n")
                for row in samples:
                    self.stdout.write(f"    {row[0]}: 용량={row[1]}, 밸브코드={row[2]}, 용기코드={row[3]}, EndUser={row[4]}, {row[5]}")










