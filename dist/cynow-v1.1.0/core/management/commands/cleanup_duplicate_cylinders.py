"""cy_cylinder_current 중복 레코드 정리"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'cy_cylinder_current 중복 레코드 정리 (공백으로 인한 중복 제거)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 삭제 없이 시뮬레이션만 수행'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        with connection.cursor() as cursor:
            # 1. 중복 현황 확인
            self.stdout.write("=== 중복 현황 확인 ===\n")
            cursor.execute("""
                SELECT COUNT(*) FROM cy_cylinder_current
            """)
            before_count = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(DISTINCT RTRIM(cylinder_no)) FROM cy_cylinder_current
            """)
            unique_count = cursor.fetchone()[0]
            
            duplicate_count = before_count - unique_count
            self.stdout.write(f"  전체 레코드: {before_count}개\n")
            self.stdout.write(f"  고유 용기번호: {unique_count}개\n")
            self.stdout.write(f"  중복 레코드: {duplicate_count}개\n")
            
            if duplicate_count == 0:
                self.stdout.write("\n[완료] 중복 레코드가 없습니다.\n")
                return
            
            # 2. 중복 삭제 (공백이 있는 버전 유지, 없는 버전 삭제)
            # 또는 더 최신인 것을 유지
            if dry_run:
                self.stdout.write("\n=== DRY RUN: 삭제될 레코드 ===\n")
                cursor.execute("""
                    SELECT 
                        c.cylinder_no,
                        LENGTH(c.cylinder_no) as len,
                        c.dashboard_enduser,
                        c.snapshot_updated_at
                    FROM cy_cylinder_current c
                    WHERE EXISTS (
                        SELECT 1 FROM cy_cylinder_current c2
                        WHERE RTRIM(c2.cylinder_no) = RTRIM(c.cylinder_no)
                          AND c2.cylinder_no != c.cylinder_no
                          AND LENGTH(c2.cylinder_no) > LENGTH(c.cylinder_no)
                    )
                    ORDER BY cylinder_no
                    LIMIT 20
                """)
                
                to_delete = cursor.fetchall()
                self.stdout.write(f"  삭제 대상 (짧은 버전): {len(to_delete)}개 (샘플)\n")
                for row in to_delete[:10]:
                    self.stdout.write(f"    '{row[0]}' (len={row[1]}), EndUser={row[2]}\n")
            else:
                self.stdout.write("\n=== 중복 레코드 삭제 시작 ===\n")
                
                # 3. 중복 중 짧은 버전(공백 없는 것) 삭제
                # 공백이 있는 버전(12자)은 CDC와 일치하므로 유지
                cursor.execute("""
                    DELETE FROM cy_cylinder_current c
                    WHERE EXISTS (
                        SELECT 1 FROM cy_cylinder_current c2
                        WHERE RTRIM(c2.cylinder_no) = RTRIM(c.cylinder_no)
                          AND c2.cylinder_no != c.cylinder_no
                          AND LENGTH(c2.cylinder_no) > LENGTH(c.cylinder_no)
                    )
                """)
                
                deleted_count = cursor.rowcount
                self.stdout.write(f"  삭제된 레코드: {deleted_count}개\n")
                
                # 4. 삭제 후 확인
                cursor.execute("""
                    SELECT COUNT(*) FROM cy_cylinder_current
                """)
                after_count = cursor.fetchone()[0]
                
                self.stdout.write(f"\n=== 정리 결과 ===\n")
                self.stdout.write(f"  정리 전: {before_count}개\n")
                self.stdout.write(f"  정리 후: {after_count}개\n")
                self.stdout.write(f"  삭제됨: {before_count - after_count}개\n")
                
                # 5. 남은 중복 확인
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM (
                        SELECT RTRIM(cylinder_no)
                        FROM cy_cylinder_current
                        GROUP BY RTRIM(cylinder_no)
                        HAVING COUNT(*) > 1
                    ) as dups
                """)
                remaining_dups = cursor.fetchone()[0]
                
                if remaining_dups > 0:
                    self.stdout.write(f"\n[경고] 남은 중복: {remaining_dups}개\n")
                else:
                    self.stdout.write(f"\n[완료] 모든 중복이 제거되었습니다.\n")

