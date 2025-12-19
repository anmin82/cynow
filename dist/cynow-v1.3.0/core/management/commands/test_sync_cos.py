"""COS 용기 하나 테스트 동기화"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'COS 용기 하나를 테스트로 동기화하여 EndUser 확인'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # SDC로 표시되는 COS 용기 하나 선택
            cursor.execute("""
                SELECT cylinder_no, dashboard_enduser, raw_valve_spec_code, raw_cylinder_spec_code
                FROM cy_cylinder_current
                WHERE dashboard_gas_name = 'COS'
                  AND dashboard_enduser = 'SDC'
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            if not result:
                self.stdout.write("SDC로 표시되는 COS 용기가 없습니다.")
                return
            
            cylinder_no, old_enduser, valve_code, cylinder_code = result
            self.stdout.write(f"\n테스트 용기: {cylinder_no}")
            self.stdout.write(f"  현재 EndUser: {old_enduser}")
            self.stdout.write(f"  밸브코드: {valve_code}")
            self.stdout.write(f"  용기코드: {cylinder_code}")
            
            # 정책 확인
            cursor.execute("""
                SELECT id, gas_name, capacity, valve_spec_code, cylinder_spec_code, default_enduser
                FROM cy_enduser_default
                WHERE gas_name = 'COS'
                  AND is_active = TRUE
            """)
            
            policies = cursor.fetchall()
            self.stdout.write(f"\n정책 목록:")
            for row in policies:
                self.stdout.write(f"  ID {row[0]}: 용량={row[2]}, 밸브={row[3]}, 용기={row[4]}, EndUser={row[5]}")
            
            # 재동기화
            self.stdout.write(f"\n재동기화 실행...")
            cursor.execute("SELECT sync_cylinder_current_single(%s)", [cylinder_no])
            
            # 결과 확인
            cursor.execute("""
                SELECT cylinder_no, dashboard_enduser
                FROM cy_cylinder_current
                WHERE cylinder_no = %s
            """, [cylinder_no])
            
            result = cursor.fetchone()
            if result:
                new_enduser = result[1]
                self.stdout.write(f"  재동기화 후 EndUser: {new_enduser}")
                if new_enduser != old_enduser:
                    self.stdout.write(self.style.SUCCESS("  [OK] EndUser가 변경되었습니다."))
                else:
                    self.stdout.write(self.style.WARNING("  [경고] EndUser가 변경되지 않았습니다."))










