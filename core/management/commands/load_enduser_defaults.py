"""EndUser 기본값 설정"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'EndUser 기본값 설정'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 저장하지 않고 미리보기만'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN 모드: 실제 저장하지 않습니다."))
        
        with connection.cursor() as cursor:
            # CF4 YC 440L 기본값: SDC
            # (용량, 밸브, 용기 스펙은 NULL로 설정하여 와일드카드로 사용)
            sql = """
                INSERT INTO cy_enduser_default 
                (gas_name, capacity, valve_spec_code, cylinder_spec_code, default_enduser, is_active)
                VALUES 
                ('CF4', 440, NULL, NULL, 'SDC', TRUE),
                ('CF4', NULL, NULL, NULL, 'SDC', TRUE)  -- CF4 전체 기본값
                ON CONFLICT (gas_name, capacity, valve_spec_code, cylinder_spec_code) 
                DO UPDATE SET 
                    default_enduser = EXCLUDED.default_enduser,
                    is_active = EXCLUDED.is_active,
                    updated_at = NOW()
            """
            
            if dry_run:
                self.stdout.write("다음 데이터가 추가/업데이트됩니다:")
                self.stdout.write("  - CF4, 440L → SDC")
                self.stdout.write("  - CF4 (전체) → SDC")
            else:
                cursor.execute(sql)
                self.stdout.write(self.style.SUCCESS("EndUser 기본값 설정 완료"))
                
                # 확인
                cursor.execute("SELECT gas_name, capacity, default_enduser FROM cy_enduser_default WHERE is_active = TRUE")
                for row in cursor.fetchall():
                    self.stdout.write(f"  {row[0]} | {row[1] or '전체'} | {row[2]}")










