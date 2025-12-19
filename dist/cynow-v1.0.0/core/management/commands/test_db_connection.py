"""PostgreSQL 연결 테스트"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = 'PostgreSQL 데이터베이스 연결 테스트'

    def handle(self, *args, **options):
        db_config = settings.DATABASES['default']
        
        # PostgreSQL인지 확인
        if 'postgresql' not in db_config['ENGINE']:
            self.stdout.write(self.style.WARNING("현재 SQLite로 설정되어 있습니다."))
            self.stdout.write("PostgreSQL로 전환하려면 .env 파일에 다음을 설정하세요:")
            self.stdout.write("  DB_ENGINE=postgresql")
            self.stdout.write("  DB_NAME=cynow")
            self.stdout.write("  DB_USER=your_user")
            self.stdout.write("  DB_PASSWORD=your_password")
            self.stdout.write("  DB_HOST=10.78.30.98")
            self.stdout.write("  DB_PORT=5434")
            return
            
        try:
            self.stdout.write("데이터베이스 연결 정보:")
            self.stdout.write(f"  ENGINE: {db_config['ENGINE']}")
            self.stdout.write(f"  NAME: {db_config['NAME']}")
            self.stdout.write(f"  USER: {db_config['USER']}")
            self.stdout.write(f"  HOST: {db_config['HOST']}")
            self.stdout.write(f"  PORT: {db_config['PORT']}")
            self.stdout.write("")
            
            # 연결 테스트
            self.stdout.write("연결 테스트 중...")
            with connection.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()
                self.stdout.write(self.style.SUCCESS("연결 성공!"))
                self.stdout.write(f"PostgreSQL 버전: {version[0]}")
                self.stdout.write("")
                
                # 현재 데이터베이스 정보
                cursor.execute("SELECT current_database();")
                db_name = cursor.fetchone()[0]
                self.stdout.write(f"현재 데이터베이스: {db_name}")
                
                # 기존 테이블 목록 확인
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                """)
                tables = cursor.fetchall()
                if tables:
                    self.stdout.write(f"\n기존 테이블 ({len(tables)}개):")
                    for table in tables[:20]:  # 최대 20개만 표시
                        self.stdout.write(f"  - {table[0]}")
                    if len(tables) > 20:
                        self.stdout.write(f"  ... 외 {len(tables) - 20}개")
                else:
                    self.stdout.write("\n기존 테이블 없음")
                
                # 기존 VIEW 목록 확인
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.views 
                    WHERE table_schema = 'public'
                    ORDER BY table_name;
                """)
                views = cursor.fetchall()
                if views:
                    self.stdout.write(f"\n기존 VIEW ({len(views)}개):")
                    for view in views:
                        self.stdout.write(f"  - {view[0]}")
                else:
                    self.stdout.write("\n기존 VIEW 없음")
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"연결 실패: {str(e)}"))
            self.stdout.write("\n.env 파일을 확인하고 다음 정보를 설정하세요:")
            self.stdout.write("  DB_ENGINE=postgresql")
            self.stdout.write("  DB_NAME=cynow")
            self.stdout.write("  DB_USER=your_user")
            self.stdout.write("  DB_PASSWORD=your_password")
            self.stdout.write("  DB_HOST=10.78.30.98")
            self.stdout.write("  DB_PORT=5434")
            raise

