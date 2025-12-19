"""sync_cylinder_current_single 함수 확인"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'sync_cylinder_current_single 함수의 EndUser 결정 로직 확인'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 함수 정의 확인
            cursor.execute("""
                SELECT pg_get_functiondef(oid) 
                FROM pg_proc 
                WHERE proname = 'sync_cylinder_current_single'
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            if not result or not result[0]:
                self.stdout.write(self.style.ERROR("함수를 찾을 수 없습니다."))
                return
            
            func_def = result[0]
            
            # 'SDC' 또는 NULL 사용 여부 확인
            if "NULL" in func_def and "'SDC'" not in func_def.split("NULL")[0].split("COALESCE")[-1]:
                self.stdout.write(self.style.SUCCESS("[OK] 함수가 정책이 없으면 NULL을 사용하도록 설정되어 있습니다."))
            elif "'SDC'" in func_def.split("COALESCE")[-1] if "COALESCE" in func_def else False:
                self.stdout.write(self.style.WARNING("[경고] 함수가 여전히 기본값 'SDC'를 사용하고 있습니다."))
                # 함수 정의에서 해당 부분 찾기
                lines = func_def.split('\n')
                for i, line in enumerate(lines):
                    if "'SDC'" in line and "COALESCE" in '\n'.join(lines[max(0, i-5):i+1]):
                        self.stdout.write(f"  라인 {i+1}: {line.strip()}")
            else:
                self.stdout.write("[정보] 함수 정의를 확인할 수 없습니다.")










