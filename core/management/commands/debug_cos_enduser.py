"""COS 용기의 EndUser 결정 로직 디버깅"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'COS 용기의 EndUser 결정 로직 디버깅'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 테스트 용기 선택
            cursor.execute("""
                SELECT cylinder_no, raw_valve_spec_code, raw_cylinder_spec_code, raw_capacity
                FROM cy_cylinder_current
                WHERE dashboard_gas_name = 'COS'
                  AND dashboard_enduser = 'SDC'
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            if not result:
                self.stdout.write("SDC로 표시되는 COS 용기가 없습니다.")
                return
            
            cylinder_no, valve_code, cylinder_code, capacity = result
            self.stdout.write(f"\n테스트 용기: {cylinder_no}")
            self.stdout.write(f"  밸브코드: {valve_code}")
            self.stdout.write(f"  용기코드: {cylinder_code}")
            self.stdout.write(f"  용량: {capacity}")
            
            # 정책 매칭 확인
            cursor.execute("""
                SELECT 
                    id,
                    gas_name,
                    capacity,
                    valve_spec_code,
                    cylinder_spec_code,
                    default_enduser,
                    CASE 
                        WHEN gas_name = 'COS' THEN '매칭'
                        ELSE '불일치'
                    END as gas_match,
                    CASE 
                        WHEN capacity IS NULL OR capacity = %s THEN '매칭'
                        ELSE '불일치'
                    END as capacity_match,
                    CASE 
                        WHEN valve_spec_code IS NULL OR valve_spec_code = %s THEN '매칭'
                        ELSE '불일치'
                    END as valve_match,
                    CASE 
                        WHEN cylinder_spec_code IS NULL OR cylinder_spec_code = %s THEN '매칭'
                        ELSE '불일치'
                    END as cylinder_match
                FROM cy_enduser_default
                WHERE gas_name = 'COS'
                  AND is_active = TRUE
            """, [capacity, valve_code, cylinder_code])
            
            policies = cursor.fetchall()
            self.stdout.write(f"\n정책 매칭 확인:")
            for row in policies:
                self.stdout.write(f"  ID {row[0]}: {row[1]} | 용량={row[2]} ({row[7]}) | 밸브={row[3]} ({row[8]}) | 용기={row[4]} ({row[9]}) | EndUser={row[5]}")
            
            # 예외 확인
            cursor.execute("""
                SELECT enduser
                FROM cy_enduser_exception
                WHERE RTRIM(cylinder_no) = RTRIM(%s)
                  AND is_active = TRUE
            """, [cylinder_no])
            
            exception = cursor.fetchone()
            if exception:
                self.stdout.write(f"\n예외 정책: {exception[0]}")
            else:
                self.stdout.write("\n예외 정책: 없음")
            
            # 함수 실행 전후 비교
            cursor.execute("""
                SELECT dashboard_enduser
                FROM cy_cylinder_current
                WHERE cylinder_no = %s
            """, [cylinder_no])
            
            before = cursor.fetchone()[0]
            self.stdout.write(f"\n함수 실행 전 EndUser: {before}")
            
            # 함수 실행
            cursor.execute("SELECT sync_cylinder_current_single(%s)", [cylinder_no])
            
            cursor.execute("""
                SELECT dashboard_enduser
                FROM cy_cylinder_current
                WHERE cylinder_no = %s
            """, [cylinder_no])
            
            after = cursor.fetchone()[0]
            self.stdout.write(f"함수 실행 후 EndUser: {after}")
            
            if before != after:
                self.stdout.write(self.style.SUCCESS("  [OK] EndUser가 변경되었습니다."))
            else:
                self.stdout.write(self.style.WARNING("  [경고] EndUser가 변경되지 않았습니다."))










