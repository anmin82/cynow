"""COS 가스의 SDC EndUser를 강제로 NULL로 수정"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'COS 가스의 정책이 매칭되지 않아 SDC로 표시된 용기를 강제로 NULL로 수정'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # COS 가스의 정책 확인
            cursor.execute("""
                SELECT id, gas_name, capacity, valve_spec_code, cylinder_spec_code, default_enduser
                FROM cy_enduser_default
                WHERE gas_name = 'COS'
                  AND is_active = TRUE
            """)
            
            policies = cursor.fetchall()
            if not policies:
                self.stdout.write("COS 가스에 대한 정책이 없습니다.")
                return
            
            # 정책이 매칭되지 않는 COS 용기를 찾아서 NULL로 업데이트
            # 정책: 용량=47, 밸브=0000000005, 용기=0000000002 → SEC
            # 정책이 매칭되지 않는 용기 (밸브코드가 0000000005가 아닌 용기)를 NULL로 설정
            self.stdout.write("COS 가스의 정책이 매칭되지 않는 용기를 NULL로 업데이트 중...\n")
            
            cursor.execute("""
                UPDATE cy_cylinder_current
                SET dashboard_enduser = NULL
                WHERE dashboard_gas_name = 'COS'
                  AND dashboard_enduser = 'SDC'
                  AND NOT EXISTS (
                      SELECT 1 
                      FROM cy_enduser_exception 
                      WHERE RTRIM(cy_enduser_exception.cylinder_no) = RTRIM(cy_cylinder_current.cylinder_no)
                        AND cy_enduser_exception.is_active = TRUE
                  )
                  AND NOT EXISTS (
                      SELECT 1 
                      FROM cy_enduser_default 
                      WHERE cy_enduser_default.gas_name = 'COS'
                        AND (cy_enduser_default.capacity IS NULL OR cy_enduser_default.capacity = cy_cylinder_current.raw_capacity)
                        AND (cy_enduser_default.valve_spec_code IS NULL OR cy_enduser_default.valve_spec_code = cy_cylinder_current.raw_valve_spec_code)
                        AND (cy_enduser_default.cylinder_spec_code IS NULL OR cy_enduser_default.cylinder_spec_code = cy_cylinder_current.raw_cylinder_spec_code)
                        AND cy_enduser_default.is_active = TRUE
                  )
            """)
            
            updated_count = cursor.rowcount
            self.stdout.write(self.style.SUCCESS(f"업데이트된 행 수: {updated_count}개"))
            
            # 결과 확인
            cursor.execute("""
                SELECT 
                    COALESCE(dashboard_enduser::text, 'NULL') as enduser_display,
                    COUNT(*) as 수량
                FROM cy_cylinder_current
                WHERE dashboard_gas_name = 'COS'
                GROUP BY dashboard_enduser
                ORDER BY dashboard_enduser NULLS LAST
            """)
            
            results = cursor.fetchall()
            self.stdout.write("\n=== 최종 결과 ===\n")
            for row in results:
                self.stdout.write(f"  EndUser={row[0]}: {row[1]}개")










