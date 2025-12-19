"""COS 가스의 SDC EndUser를 NULL로 수정"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'COS 가스의 정책이 매칭되지 않아 SDC로 표시된 용기를 NULL로 수정'

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
            # 정책이 매칭되는 용기는 그대로 두고, 매칭되지 않는 용기만 NULL로 설정
            self.stdout.write("COS 가스의 정책이 매칭되지 않는 용기를 NULL로 업데이트 중...\n")
            
            # COS 가스의 모든 용기를 재동기화
            cursor.execute("""
                SELECT "CYLINDER_NO" 
                FROM "fcms_cdc"."ma_cylinders" 
                WHERE RTRIM("CYLINDER_NO") IN (
                    SELECT RTRIM(cylinder_no) 
                    FROM cy_cylinder_current 
                    WHERE dashboard_gas_name = 'COS'
                      AND dashboard_enduser = 'SDC'
                )
            """)
            
            sdc_cylinders = [row[0] for row in cursor.fetchall()]
            self.stdout.write(f"SDC로 표시된 COS 용기: {len(sdc_cylinders)}개\n")
            
            updated = 0
            for cylinder_no in sdc_cylinders:
                try:
                    cursor.execute("SELECT sync_cylinder_current_single(%s)", [cylinder_no])
                    updated += 1
                    if updated % 100 == 0:
                        self.stdout.write(f"  진행: {updated}/{len(sdc_cylinders)}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  오류 ({cylinder_no}): {str(e)}"))
            
            self.stdout.write(self.style.SUCCESS(f"\n재동기화 완료: {updated}개"))
            
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










