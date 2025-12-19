"""PostgreSQL 데이터베이스 삭제"""
from django.core.management.base import BaseCommand
from django.conf import settings
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


class Command(BaseCommand):
    help = 'PostgreSQL 데이터베이스 삭제'

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
            self.stdout.write(self.style.ERROR("PostgreSQL이 아닙니다."))
            return
        
        db_name = db_config['NAME']
        db_user = db_config['USER']
        db_password = db_config['PASSWORD']
        db_host = db_config['HOST']
        db_port = db_config['PORT']
        
        if not options['noinput']:
            confirm = input(f"데이터베이스 '{db_name}'를 완전히 삭제하시겠습니까? (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING("취소되었습니다."))
                return
        
        self.stdout.write(f"데이터베이스 '{db_name}' 삭제 중...")
        
        try:
            # postgres 데이터베이스에 연결하여 데이터베이스 삭제
            conn = psycopg2.connect(
                dbname='postgres',  # 기본 데이터베이스
                user=db_user,
                password=db_password,
                host=db_host,
                port=db_port
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            cursor = conn.cursor()
            
            # 다른 세션 연결 종료 (데이터베이스가 사용 중일 경우)
            cursor.execute("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = %s
                AND pid <> pg_backend_pid();
            """, (db_name,))
            
            # 데이터베이스 존재 여부 확인
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (db_name,)
            )
            exists = cursor.fetchone()
            
            if exists:
                # 데이터베이스 삭제
                cursor.execute(f'DROP DATABASE "{db_name}";')
                self.stdout.write(self.style.SUCCESS(f"데이터베이스 '{db_name}' 삭제 완료!"))
            else:
                self.stdout.write(self.style.WARNING(f"데이터베이스 '{db_name}'가 존재하지 않습니다."))
            
            cursor.close()
            conn.close()
            
        except psycopg2.OperationalError as e:
            self.stdout.write(self.style.ERROR(f"연결 실패: {str(e)}"))
            self.stdout.write("\n연결 정보를 확인하세요:")
            self.stdout.write(f"  HOST: {db_host}")
            self.stdout.write(f"  PORT: {db_port}")
            self.stdout.write(f"  USER: {db_user}")
            raise
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"오류 발생: {str(e)}"))
            raise




