"""SQL 파일 실행"""
from django.core.management.base import BaseCommand
from django.db import connection
import os
from pathlib import Path


class Command(BaseCommand):
    help = 'SQL 파일 실행'

    def add_arguments(self, parser):
        parser.add_argument('sql_file', type=str, help='실행할 SQL 파일 경로')

    def handle(self, *args, **options):
        sql_file = options['sql_file']
        
        # 상대 경로인 경우 프로젝트 루트 기준으로 변환
        if not os.path.isabs(sql_file):
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            sql_file = base_dir / sql_file
        
        if not os.path.exists(sql_file):
            self.stdout.write(self.style.ERROR(f"SQL 파일을 찾을 수 없습니다: {sql_file}"))
            return
        
        self.stdout.write(f"SQL 파일 실행 중: {sql_file}")
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # SQL 파일 전체를 한 번에 실행 (함수 정의 등 복잡한 구문 처리)
        with connection.cursor() as cursor:
            try:
                # 주석 제거 (단순화: --로 시작하는 줄만 제거)
                lines = []
                for line in sql_content.split('\n'):
                    stripped = line.strip()
                    if stripped and not stripped.startswith('--'):
                        lines.append(line)
                    elif not stripped:
                        lines.append('')  # 빈 줄은 유지
                
                cleaned_sql = '\n'.join(lines)
                
                # 전체 SQL 실행
                cursor.execute(cleaned_sql)
                self.stdout.write(self.style.SUCCESS("SQL 파일 실행 완료"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"오류: {str(e)}"))
                # 오류 발생 시에도 계속 진행 (일부만 실패할 수 있음)
                pass
        
        self.stdout.write(self.style.SUCCESS(f"\nSQL 파일 실행 완료: {sql_file}"))

