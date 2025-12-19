"""PostgreSQL 데이터베이스의 모든 테이블 목록 확인"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'PostgreSQL 데이터베이스의 모든 테이블 및 VIEW 목록 확인'

    def handle(self, *args, **options):
        try:
            with connection.cursor() as cursor:
                # 모든 테이블 목록
                cursor.execute("""
                    SELECT 
                        table_name,
                        table_type
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_type, table_name;
                """)
                tables = cursor.fetchall()
                
                if tables:
                    self.stdout.write(f"\n테이블 및 VIEW 목록 ({len(tables)}개):\n")
                    
                    base_tables = [t for t in tables if t[1] == 'BASE TABLE']
                    views = [t for t in tables if t[1] == 'VIEW']
                    
                    if base_tables:
                        self.stdout.write("=== BASE TABLE ===")
                        for table in base_tables:
                            # 테이블의 컬럼 정보도 표시
                            cursor.execute(f"""
                                SELECT column_name, data_type
                                FROM information_schema.columns
                                WHERE table_schema = 'public'
                                AND table_name = '{table[0]}'
                                ORDER BY ordinal_position
                                LIMIT 10;
                            """)
                            columns = cursor.fetchall()
                            
                            self.stdout.write(f"\n  [{table[0]}]")
                            for col in columns:
                                self.stdout.write(f"    - {col[0]} ({col[1]})")
                            if len(columns) == 10:
                                self.stdout.write(f"    ... (더 많은 컬럼 있음)")
                    
                    if views:
                        self.stdout.write("\n=== VIEW ===")
                        for view in views:
                            self.stdout.write(f"  - {view[0]}")
                else:
                    self.stdout.write("테이블이 없습니다.")
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"오류 발생: {str(e)}"))
            import traceback
            self.stdout.write(traceback.format_exc())
            raise













