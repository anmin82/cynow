"""sync_cylinder_current_single 함수 업데이트 적용"""
from django.core.management.base import BaseCommand
from django.db import connection
import os


class Command(BaseCommand):
    help = 'sync_cylinder_current_single 함수를 cylinder_no_trimmed 기준으로 업데이트'

    def handle(self, *args, **options):
        # SQL 파일 읽기
        sql_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'sql', 'update_sync_function_with_trimmed.sql')
        sql_path = os.path.abspath(sql_path)
        
        self.stdout.write(f"SQL 파일 경로: {sql_path}\n")
        
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        with connection.cursor() as cursor:
            # SQL 실행
            self.stdout.write("=== sync_cylinder_current_single 함수 업데이트 ===\n")
            try:
                cursor.execute(sql_content)
                self.stdout.write("  함수 업데이트 완료\n")
            except Exception as e:
                self.stdout.write(f"  [오류] {e}\n")
                return
            
            # 함수 확인
            self.stdout.write("\n=== 함수 확인 ===\n")
            cursor.execute("""
                SELECT pg_get_functiondef(oid) 
                FROM pg_proc 
                WHERE proname = 'sync_cylinder_current_single'
            """)
            result = cursor.fetchone()
            if result:
                # ON CONFLICT 부분만 확인
                func_def = result[0]
                if 'ON CONFLICT (cylinder_no_trimmed)' in func_def:
                    self.stdout.write("  [OK] ON CONFLICT (cylinder_no_trimmed) 확인됨\n")
                else:
                    self.stdout.write("  [경고] ON CONFLICT 설정 확인 필요\n")
            
            self.stdout.write("\n[완료] 함수 업데이트 완료\n")










