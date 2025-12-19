"""cy_cylinder_current 중복 레코드 확인"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'cy_cylinder_current 중복 레코드 확인'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 1. 중복 용기번호 확인
            self.stdout.write("=== 중복 용기번호 확인 ===\n")
            cursor.execute("""
                SELECT 
                    cylinder_no,
                    COUNT(*) as 수량
                FROM cy_cylinder_current
                GROUP BY cylinder_no
                HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC
                LIMIT 20
            """)
            
            duplicates = cursor.fetchall()
            if duplicates:
                self.stdout.write(f"  중복된 용기번호: {len(duplicates)}개\n")
                for row in duplicates[:10]:
                    self.stdout.write(f"    {row[0]}: {row[1]}회\n")
            else:
                self.stdout.write("  [없음] 중복 용기번호가 없습니다.\n")
            
            # 2. RTRIM 후 중복 확인 (공백 문제)
            self.stdout.write("\n=== RTRIM 후 중복 확인 ===\n")
            cursor.execute("""
                SELECT 
                    RTRIM(cylinder_no) as trimmed_no,
                    COUNT(*) as 수량
                FROM cy_cylinder_current
                GROUP BY RTRIM(cylinder_no)
                HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC
                LIMIT 20
            """)
            
            trim_duplicates = cursor.fetchall()
            if trim_duplicates:
                self.stdout.write(f"  RTRIM 후 중복된 용기번호: {len(trim_duplicates)}개\n")
                for row in trim_duplicates[:10]:
                    self.stdout.write(f"    '{row[0]}': {row[1]}회\n")
                    
                    # 각 중복의 상세 확인
                    cursor.execute("""
                        SELECT 
                            cylinder_no,
                            LENGTH(cylinder_no) as len,
                            dashboard_enduser
                        FROM cy_cylinder_current
                        WHERE RTRIM(cylinder_no) = %s
                    """, [row[0]])
                    
                    details = cursor.fetchall()
                    for d in details:
                        self.stdout.write(f"      -> '{d[0]}' (len={d[1]}), EndUser={d[2]}\n")
            else:
                self.stdout.write("  [없음] RTRIM 후 중복 용기번호가 없습니다.\n")
            
            # 3. CF4 YC 440L 용기 중복 확인
            self.stdout.write("\n=== CF4 YC 440L 용기 중복 확인 ===\n")
            cursor.execute("""
                SELECT 
                    RTRIM(c.cylinder_no) as trimmed_no,
                    COUNT(*) as 수량
                FROM cy_cylinder_current c
                WHERE c.dashboard_gas_name = 'CF4'
                  AND c.dashboard_cylinder_spec_name LIKE '%YC%'
                  AND c.dashboard_capacity = 440
                GROUP BY RTRIM(c.cylinder_no)
                HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """)
            
            cf4_duplicates = cursor.fetchall()
            if cf4_duplicates:
                self.stdout.write(f"  CF4 YC 440L 중복: {len(cf4_duplicates)}개\n")
                for row in cf4_duplicates[:5]:
                    self.stdout.write(f"    '{row[0]}': {row[1]}회\n")
            else:
                self.stdout.write("  [없음] CF4 YC 440L 중복이 없습니다.\n")
            
            # 4. 전체 고유 용기번호 수
            self.stdout.write("\n=== 고유 용기번호 수 ===\n")
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT cylinder_no) as unique_raw,
                    COUNT(DISTINCT RTRIM(cylinder_no)) as unique_trimmed,
                    COUNT(*) as total
                FROM cy_cylinder_current
            """)
            
            counts = cursor.fetchone()
            self.stdout.write(f"  전체 레코드: {counts[2]}개\n")
            self.stdout.write(f"  고유 cylinder_no: {counts[0]}개\n")
            self.stdout.write(f"  고유 RTRIM(cylinder_no): {counts[1]}개\n")
            self.stdout.write(f"  중복 레코드 수: {counts[2] - counts[1]}개\n")

