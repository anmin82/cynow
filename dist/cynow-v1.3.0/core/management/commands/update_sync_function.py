"""sync_cylinder_current_single 함수 업데이트"""
from django.core.management.base import BaseCommand
from django.db import connection
from pathlib import Path


class Command(BaseCommand):
    help = 'sync_cylinder_current_single 함수 업데이트 (정책이 없으면 NULL 사용)'

    def handle(self, *args, **options):
        sql_file = Path(__file__).parent.parent.parent.parent / 'sql' / 'create_sync_triggers.sql'
        
        if not sql_file.exists():
            self.stdout.write(self.style.ERROR(f"SQL 파일을 찾을 수 없습니다: {sql_file}"))
            return
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 함수 부분만 추출 (CREATE OR REPLACE FUNCTION부터 END; $$까지)
        # 또는 전체 파일 실행
        with connection.cursor() as cursor:
            try:
                # SQL 파일을 세미콜론으로 분리하여 실행
                # 하지만 함수 정의는 여러 줄이므로 전체를 실행
                cursor.execute(sql_content)
                self.stdout.write(self.style.SUCCESS("함수 업데이트 완료"))
                
                # COS 용기 재동기화
                self.stdout.write("\nCOS 용기 재동기화 중...")
                cursor.execute("""
                    SELECT "CYLINDER_NO" 
                    FROM "fcms_cdc"."ma_cylinders" 
                    WHERE RTRIM("CYLINDER_NO") IN (
                        SELECT RTRIM(cylinder_no) 
                        FROM cy_cylinder_current 
                        WHERE dashboard_gas_name = 'COS'
                    )
                """)
                
                cos_cylinders = [row[0] for row in cursor.fetchall()]
                updated = 0
                for cylinder_no in cos_cylinders:
                    try:
                        cursor.execute("SELECT sync_cylinder_current_single(%s)", [cylinder_no])
                        updated += 1
                        if updated % 100 == 0:
                            self.stdout.write(f"  진행: {updated}/{len(cos_cylinders)}")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"  오류 ({cylinder_no}): {str(e)}"))
                
                self.stdout.write(self.style.SUCCESS(f"\nCOS 용기 재동기화 완료: {updated}개"))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"오류 발생: {str(e)}"))










