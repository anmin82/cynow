"""잘못된 폐기 상태 수정"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = '잘못된 폐기 상태 수정 (상태 코드 950, 952를 정비로)'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 상태 코드 950, 952인데 '폐기'로 표시된 것들을 '정비'로 수정
            cursor.execute("""
                UPDATE cy_cylinder_current 
                SET dashboard_status = '정비' 
                WHERE raw_condition_code IN ('950', '952') 
                  AND dashboard_status = '폐기'
            """)
            updated_count = cursor.rowcount
            self.stdout.write(self.style.SUCCESS(f"수정된 행 수 (950/952 → 정비): {updated_count}"))
            
            # 상태 코드 990인데 '기타'로 표시된 것들을 '폐기'로 수정
            cursor.execute("""
                UPDATE cy_cylinder_current 
                SET dashboard_status = '폐기' 
                WHERE raw_condition_code = '990' 
                  AND dashboard_status != '폐기'
            """)
            updated_count_990 = cursor.rowcount
            self.stdout.write(self.style.SUCCESS(f"수정된 행 수 (990 → 폐기): {updated_count_990}"))
            
            # 확인
            cursor.execute("""
                SELECT COUNT(*) 
                FROM cy_cylinder_current 
                WHERE dashboard_status = '폐기' 
                  AND raw_condition_code != '990'
            """)
            remaining_errors = cursor.fetchone()[0]
            if remaining_errors > 0:
                self.stdout.write(self.style.WARNING(f"남은 오류 수: {remaining_errors}"))
            else:
                self.stdout.write(self.style.SUCCESS("모든 오류가 수정되었습니다."))
            
            # 최종 확인
            cursor.execute("""
                SELECT COUNT(*) 
                FROM cy_cylinder_current 
                WHERE dashboard_status = '폐기'
            """)
            total_disposal = cursor.fetchone()[0]
            self.stdout.write(f"\n총 '폐기' 상태 용기: {total_disposal}개")

