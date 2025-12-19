"""cy_cylinder_current에 cylinder_no_trimmed 컬럼 추가"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'cy_cylinder_current에 cylinder_no_trimmed 컬럼 추가 및 설정'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 1. 현재 상태 확인
            self.stdout.write("=== 현재 상태 확인 ===\n")
            cursor.execute("SELECT COUNT(*) FROM cy_cylinder_current")
            before_count = cursor.fetchone()[0]
            self.stdout.write(f"  현재 레코드: {before_count}개\n")
            
            # 2. 기존 제약조건 제거
            self.stdout.write("\n=== 기존 제약조건 제거 ===\n")
            try:
                cursor.execute("ALTER TABLE cy_cylinder_current DROP CONSTRAINT IF EXISTS cy_cylinder_current_pkey")
                self.stdout.write("  pkey 제거 완료\n")
            except Exception as e:
                self.stdout.write(f"  pkey 제거 실패: {e}\n")
            
            try:
                cursor.execute("ALTER TABLE cy_cylinder_current DROP CONSTRAINT IF EXISTS cy_cylinder_current_cylinder_no_key")
                self.stdout.write("  cylinder_no_key 제거 완료\n")
            except Exception as e:
                self.stdout.write(f"  cylinder_no_key 제거 실패: {e}\n")
            
            # 3. cylinder_no_trimmed 컬럼 추가
            self.stdout.write("\n=== cylinder_no_trimmed 컬럼 추가 ===\n")
            try:
                cursor.execute("ALTER TABLE cy_cylinder_current ADD COLUMN IF NOT EXISTS cylinder_no_trimmed VARCHAR(20)")
                self.stdout.write("  컬럼 추가 완료\n")
            except Exception as e:
                self.stdout.write(f"  컬럼 추가 실패: {e}\n")
            
            # 4. 기존 데이터에 RTRIM 값 채우기
            self.stdout.write("\n=== RTRIM 값 채우기 ===\n")
            cursor.execute("""
                UPDATE cy_cylinder_current 
                SET cylinder_no_trimmed = RTRIM(cylinder_no)
                WHERE cylinder_no_trimmed IS NULL OR cylinder_no_trimmed = ''
            """)
            updated = cursor.rowcount
            self.stdout.write(f"  업데이트된 레코드: {updated}개\n")
            
            # 5. 중복 확인
            self.stdout.write("\n=== 중복 확인 ===\n")
            cursor.execute("""
                SELECT cylinder_no_trimmed, COUNT(*) as cnt
                FROM cy_cylinder_current
                GROUP BY cylinder_no_trimmed
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            self.stdout.write(f"  중복 용기번호: {len(duplicates)}개\n")
            
            # 6. 중복 제거 (최신 것만 유지)
            if duplicates:
                self.stdout.write("\n=== 중복 제거 ===\n")
                cursor.execute("""
                    DELETE FROM cy_cylinder_current c1
                    USING cy_cylinder_current c2
                    WHERE c1.cylinder_no_trimmed = c2.cylinder_no_trimmed
                      AND c1.ctid < c2.ctid
                """)
                deleted = cursor.rowcount
                self.stdout.write(f"  삭제된 레코드: {deleted}개\n")
            
            # 7. NOT NULL 설정
            self.stdout.write("\n=== NOT NULL 설정 ===\n")
            try:
                cursor.execute("ALTER TABLE cy_cylinder_current ALTER COLUMN cylinder_no_trimmed SET NOT NULL")
                self.stdout.write("  NOT NULL 설정 완료\n")
            except Exception as e:
                self.stdout.write(f"  NOT NULL 설정 실패: {e}\n")
            
            # 8. UNIQUE 제약조건 추가
            self.stdout.write("\n=== UNIQUE 제약조건 추가 ===\n")
            try:
                cursor.execute("""
                    ALTER TABLE cy_cylinder_current 
                    ADD CONSTRAINT cy_cylinder_current_cylinder_no_trimmed_key 
                    UNIQUE (cylinder_no_trimmed)
                """)
                self.stdout.write("  UNIQUE 제약조건 추가 완료\n")
            except Exception as e:
                self.stdout.write(f"  UNIQUE 제약조건 추가 실패: {e}\n")
            
            # 9. 인덱스 추가
            self.stdout.write("\n=== 인덱스 추가 ===\n")
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_cy_cylinder_current_no_trimmed 
                    ON cy_cylinder_current(cylinder_no_trimmed)
                """)
                self.stdout.write("  인덱스 추가 완료\n")
            except Exception as e:
                self.stdout.write(f"  인덱스 추가 실패: {e}\n")
            
            # 10. 최종 확인
            self.stdout.write("\n=== 최종 상태 확인 ===\n")
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT cylinder_no) as unique_cylinder_no,
                    COUNT(DISTINCT cylinder_no_trimmed) as unique_trimmed
                FROM cy_cylinder_current
            """)
            result = cursor.fetchone()
            self.stdout.write(f"  전체 레코드: {result[0]}개\n")
            self.stdout.write(f"  고유 cylinder_no: {result[1]}개\n")
            self.stdout.write(f"  고유 cylinder_no_trimmed: {result[2]}개\n")
            
            self.stdout.write("\n[완료] cylinder_no_trimmed 컬럼 추가 및 설정 완료\n")










