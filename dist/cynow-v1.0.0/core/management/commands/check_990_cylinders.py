"""condition_code가 990인 용기 확인"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'condition_code가 990인 용기 확인'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # fcms_cdc에서 condition_code가 990인 용기 확인
            cursor.execute("""
                SELECT 
                    RTRIM(c."CYLINDER_NO") as cylinder_no,
                    ls."CONDITION_CODE" as condition_code,
                    CASE WHEN ls."CONDITION_CODE" IS NULL THEN 'NULL' ELSE 'NOT NULL' END as is_null
                FROM "fcms_cdc"."ma_cylinders" c
                LEFT JOIN "fcms_cdc"."tr_latest_cylinder_statuses" ls 
                    ON RTRIM(c."CYLINDER_NO") = RTRIM(ls."CYLINDER_NO")
                WHERE RTRIM(c."CYLINDER_NO") IN ('HP398818', 'HP398918')
                ORDER BY c."CYLINDER_NO"
            """)
            
            results = cursor.fetchall()
            self.stdout.write(f"\ncondition_code가 990인 용기: {len(results)}개\n")
            for row in results:
                self.stdout.write(f"  {row[0]}: {row[1]}")
            
            # cy_cylinder_current에서 확인
            cursor.execute("""
                SELECT 
                    cylinder_no,
                    raw_condition_code,
                    dashboard_status
                FROM cy_cylinder_current
                WHERE raw_condition_code = '990'
                ORDER BY cylinder_no
            """)
            
            results = cursor.fetchall()
            self.stdout.write(f"\ncy_cylinder_current에서 condition_code가 990인 용기: {len(results)}개\n")
            for row in results:
                self.stdout.write(f"  {row[0]}: raw={row[1]}, dashboard={row[2]}")
            
            # 재동기화
            if results:
                self.stdout.write("\n재동기화 중...\n")
                for row in results:
                    cylinder_no = row[0]
                    cursor.execute("SELECT sync_cylinder_current_single(%s)", [cylinder_no])
                    self.stdout.write(f"  {cylinder_no} 동기화 완료")
                
                # 다시 확인
                cursor.execute("""
                    SELECT 
                        cylinder_no,
                        raw_condition_code,
                        dashboard_status
                    FROM cy_cylinder_current
                    WHERE raw_condition_code = '990'
                    ORDER BY cylinder_no
                """)
                
                results = cursor.fetchall()
                self.stdout.write(f"\n재동기화 후:\n")
                for row in results:
                    self.stdout.write(f"  {row[0]}: raw={row[1]}, dashboard={row[2]}")

