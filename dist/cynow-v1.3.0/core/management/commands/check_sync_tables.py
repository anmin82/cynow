"""동기화 테이블 확인 (Debezium/Kafka를 통해 동기화된 테이블)"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'PostgreSQL에서 FCMS 동기화 테이블 확인'

    def handle(self, *args, **options):
        try:
            with connection.cursor() as cursor:
                # Debezium이 생성할 수 있는 패턴의 테이블 찾기
                # 일반적인 패턴: fcms.*, FCMS.*, MA_*, TR_* 등
                patterns = [
                    '%CYLINDER%',
                    '%FCMS%',
                    'MA_%',
                    'TR_%',
                    '%ITEMS%',
                    '%SPEC%',
                    '%STATUS%',
                    '%PARAMETER%'
                ]
                
                self.stdout.write("동기화 테이블 검색 중...\n")
                
                # 스키마 목록 확인 (fcms_cdc 우선, public도 확인)
                schemas_to_check = ['fcms_cdc', 'public']
                
                all_tables = []
                for schema in schemas_to_check:
                    for pattern in patterns:
                        cursor.execute("""
                            SELECT table_schema, table_name, table_type
                            FROM information_schema.tables 
                            WHERE table_schema = %s
                            AND table_name ILIKE %s
                            ORDER BY table_name;
                        """, (schema, pattern))
                        tables = cursor.fetchall()
                        all_tables.extend(tables)
                
                # 중복 제거 (스키마 포함)
                unique_tables = {}
                for schema, table_name, table_type in all_tables:
                    full_name = f"{schema}.{table_name}"
                    if full_name not in unique_tables:
                        unique_tables[full_name] = {'schema': schema, 'table': table_name, 'type': table_type}
                
                if unique_tables:
                    self.stdout.write(self.style.SUCCESS(f"발견된 테이블 ({len(unique_tables)}개):\n"))
                    
                    # BASE TABLE과 VIEW 분리
                    base_tables = {k: v for k, v in unique_tables.items() if v == 'BASE TABLE'}
                    views = {k: v for k, v in unique_tables.items() if v == 'VIEW'}
                    
                    if base_tables:
                        self.stdout.write("=== 동기화 테이블 (BASE TABLE) ===\n")
                        for full_name in sorted(base_tables.keys()):
                            table_info = base_tables[full_name]
                            schema = table_info['schema']
                            table_name = table_info['table']
                            
                            # 컬럼 정보 표시
                            cursor.execute("""
                                SELECT column_name, data_type, character_maximum_length
                                FROM information_schema.columns
                                WHERE table_schema = %s
                                AND table_name = %s
                                ORDER BY ordinal_position
                                LIMIT 15;
                            """, (schema, table_name))
                            columns = cursor.fetchall()
                            
                            # 데이터 개수 확인
                            try:
                                cursor.execute(f'SELECT COUNT(*) FROM "{schema}"."{table_name}";')
                                count = cursor.fetchone()[0]
                                self.stdout.write(f"  [{full_name}] ({count}행)")
                            except:
                                self.stdout.write(f"  [{full_name}]")
                            
                            for col in columns[:10]:
                                col_name, col_type, max_len = col
                                type_str = f"{col_type}({max_len})" if max_len else col_type
                                self.stdout.write(f"    - {col_name}: {type_str}")
                            if len(columns) > 10:
                                self.stdout.write(f"    ... (총 {len(columns)}개 컬럼)")
                            self.stdout.write("")
                    
                    if views:
                        self.stdout.write("\n=== VIEW ===\n")
                        for view_name in sorted(views.keys()):
                            self.stdout.write(f"  - {view_name}")
                else:
                    self.stdout.write(self.style.WARNING("동기화 테이블을 찾을 수 없습니다."))
                    self.stdout.write("\n확인 사항:")
                    self.stdout.write("  1. Debezium 커넥터가 정상 작동 중인지 확인")
                    self.stdout.write("  2. Kafka Sink Connector가 PostgreSQL에 데이터를 쓰는지 확인")
                    self.stdout.write("  3. 테이블명이 예상과 다른 패턴일 수 있음")
                
                # 모든 테이블 목록 (참고용)
                self.stdout.write("\n=== 모든 테이블 목록 (참고) ===\n")
                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                """)
                all_db_tables = cursor.fetchall()
                for table in all_db_tables:
                    self.stdout.write(f"  - {table[0]}")
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"오류 발생: {str(e)}"))
            import traceback
            self.stdout.write(traceback.format_exc())
            raise


