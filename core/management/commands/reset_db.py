"""PostgreSQL 데이터베이스 초기화 (모든 테이블 삭제 및 재생성)"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = 'PostgreSQL 데이터베이스 초기화 (모든 테이블 삭제 후 마이그레이션 재실행)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='사용자 확인 없이 실행',
        )

    def handle(self, *args, **options):
        db_config = settings.DATABASES['default']
        
        # PostgreSQL인지 확인
        if 'postgresql' not in db_config['ENGINE']:
            self.stdout.write(self.style.ERROR("PostgreSQL이 아닙니다. DB_ENGINE=postgresql로 설정하세요."))
            return
        
        if not options['noinput']:
            confirm = input("모든 테이블과 데이터가 삭제됩니다. 계속하시겠습니까? (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING("취소되었습니다."))
                return
        
        try:
            with connection.cursor() as cursor:
                self.stdout.write("기존 테이블 삭제 중...")
                
                # 모든 테이블 목록 가져오기
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE';
                """)
                tables = cursor.fetchall()
                
                if tables:
                    # CASCADE로 외래키 제약조건과 함께 삭제
                    table_names = [f'"{table[0]}"' for table in tables]
                    drop_query = f"DROP TABLE IF EXISTS {', '.join(table_names)} CASCADE;"
                    cursor.execute(drop_query)
                    self.stdout.write(self.style.SUCCESS(f"  {len(tables)}개 테이블 삭제 완료"))
                else:
                    self.stdout.write("  삭제할 테이블이 없습니다.")
                
                # 모든 VIEW 삭제
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.views 
                    WHERE table_schema = 'public';
                """)
                views = cursor.fetchall()
                
                if views:
                    for view in views:
                        cursor.execute(f'DROP VIEW IF EXISTS "{view[0]}" CASCADE;')
                    self.stdout.write(self.style.SUCCESS(f"  {len(views)}개 VIEW 삭제 완료"))
                
                # 모든 시퀀스 재설정 (있을 경우)
                cursor.execute("""
                    SELECT sequence_name 
                    FROM information_schema.sequences 
                    WHERE sequence_schema = 'public';
                """)
                sequences = cursor.fetchall()
                
                if sequences:
                    for seq in sequences:
                        cursor.execute(f'DROP SEQUENCE IF EXISTS "{seq[0]}" CASCADE;')
                    self.stdout.write(self.style.SUCCESS(f"  {len(sequences)}개 시퀀스 삭제 완료"))
                
                self.stdout.write("\n마이그레이션 재실행 중...")
            
            # 마이그레이션 재실행
            call_command('migrate', verbosity=1, interactive=False)
            self.stdout.write(self.style.SUCCESS("\n데이터베이스 초기화 완료!"))
            self.stdout.write("\n다음 단계:")
            self.stdout.write("  1. 동기화 테이블 확인: python manage.py list_db_tables")
            self.stdout.write("  2. VIEW 생성: python manage.py create_postgresql_views")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"오류 발생: {str(e)}"))
            import traceback
            self.stdout.write(traceback.format_exc())
            raise













