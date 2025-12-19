"""대시보드에서 "폐기"로 표시되는 용기들의 실제 상태 확인"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = '대시보드에서 "폐기"로 표시되는 용기들의 실제 상태 코드 확인'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            self.stdout.write("\n=== 폐기 상태 용기 확인 ===\n")
            
            # 1. "폐기" 상태로 표시되는 용기들의 실제 상태 코드 확인
            self.stdout.write("1. '폐기' 상태로 표시되는 모든 용기:\n")
            cursor.execute("""
                SELECT 
                    c.cylinder_no,
                    c.dashboard_status as 표시상태,
                    c.raw_condition_code as 실제상태코드,
                    c.pressure_due_date as 내압만료일,
                    CASE 
                        WHEN c.pressure_due_date < NOW() THEN '만료'
                        WHEN c.pressure_due_date IS NULL THEN '미지정'
                        ELSE '유효'
                    END as 내압상태
                FROM cy_cylinder_current c
                WHERE c.dashboard_status = '폐기'
                ORDER BY c.cylinder_no
            """)
            
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            if not results:
                self.stdout.write(self.style.SUCCESS("   [OK] '폐기' 상태로 표시되는 용기가 없습니다.\n"))
            else:
                self.stdout.write(f"   총 {len(results)}개 용기:\n")
                for row in results:
                    status_icon = "[경고]" if row['실제상태코드'] != '990' else "[OK]"
                    self.stdout.write(f"   {status_icon} {row['cylinder_no']}: 상태코드={row['실제상태코드']}, 내압={row['내압상태']}, 내압일={row['내압만료일']}")
            
            # 2. 상태 코드별 "폐기"로 표시되는 용기 수 집계
            self.stdout.write("\n2. 상태 코드별 '폐기'로 표시된 용기 수:\n")
            cursor.execute("""
                SELECT 
                    c.raw_condition_code as 상태코드,
                    COUNT(*) as 수량
                FROM cy_cylinder_current c
                WHERE c.dashboard_status = '폐기'
                GROUP BY c.raw_condition_code
                ORDER BY c.raw_condition_code
            """)
            
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            for row in results:
                status_code = row['상태코드'] or '(NULL)'
                qty = row['수량']
                if status_code == '990':
                    self.stdout.write(self.style.SUCCESS(f"   [OK] 상태코드 {status_code}: {qty}개 (정상)"))
                else:
                    self.stdout.write(self.style.ERROR(f"   [오류] 상태코드 {status_code}: {qty}개 (잘못된 매핑!)"))
            
            # 3. 내압만료 용기 중 "폐기"로 표시되는 것 확인
            self.stdout.write("\n3. 내압만료 용기 중 '폐기'로 표시되는 것:\n")
            cursor.execute("""
                SELECT 
                    c.cylinder_no,
                    c.dashboard_status as 표시상태,
                    c.raw_condition_code as 실제상태코드,
                    c.pressure_due_date as 내압만료일
                FROM cy_cylinder_current c
                WHERE c.dashboard_status = '폐기'
                  AND c.pressure_due_date < NOW()
                ORDER BY c.cylinder_no
            """)
            
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            if not results:
                self.stdout.write(self.style.SUCCESS("   [OK] 내압만료 용기가 '폐기'로 표시되지 않습니다.\n"))
            else:
                self.stdout.write(self.style.WARNING(f"   [경고] {len(results)}개 용기가 내압만료인데 '폐기'로 표시됩니다:\n"))
                for row in results:
                    self.stdout.write(f"      - {row['cylinder_no']}: 상태코드={row['실제상태코드']}, 내압만료일={row['내압만료일']}")
            
            # 4. "이상" 상태 코드(190)인데 "폐기"로 표시되는 것 확인
            self.stdout.write("\n4. '이상'(190) 상태인데 '폐기'로 표시되는 것:\n")
            cursor.execute("""
                SELECT 
                    c.cylinder_no,
                    c.dashboard_status as 표시상태,
                    c.raw_condition_code as 실제상태코드
                FROM cy_cylinder_current c
                WHERE c.raw_condition_code = '190'
                  AND c.dashboard_status = '폐기'
                ORDER BY c.cylinder_no
            """)
            
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            if not results:
                self.stdout.write(self.style.SUCCESS("   [OK] '이상' 상태가 '폐기'로 잘못 표시되지 않습니다.\n"))
            else:
                self.stdout.write(self.style.ERROR(f"   [오류] {len(results)}개 용기가 '이상' 상태인데 '폐기'로 표시됩니다:\n"))
                for row in results:
                    self.stdout.write(f"      - {row['cylinder_no']}")
            
            # 5. 요약
            self.stdout.write("\n=== 요약 ===\n")
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM cy_cylinder_current
                WHERE dashboard_status = '폐기'
            """)
            total_disposal = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM cy_cylinder_current
                WHERE dashboard_status = '폐기'
                  AND raw_condition_code = '990'
            """)
            correct_disposal = cursor.fetchone()[0]
            
            incorrect_disposal = total_disposal - correct_disposal
            
            self.stdout.write(f"총 '폐기'로 표시된 용기: {total_disposal}개")
            self.stdout.write(self.style.SUCCESS(f"올바른 폐기(990): {correct_disposal}개"))
            if incorrect_disposal > 0:
                self.stdout.write(self.style.ERROR(f"잘못된 폐기(990 아님): {incorrect_disposal}개"))
                self.stdout.write("\n[경고] 상태 매핑을 확인하거나 데이터를 수정해야 합니다.")
            else:
                self.stdout.write(self.style.SUCCESS("\n[OK] 모든 '폐기' 상태가 올바르게 매핑되어 있습니다."))










