"""전체 용기 재동기화"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = '전체 용기 재동기화 (CDC 데이터 기준)'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 1. CDC 전체 용기 수 확인
            self.stdout.write("=== CDC 전체 용기 수 확인 ===\n")
            cursor.execute('SELECT COUNT(*) FROM "fcms_cdc"."ma_cylinders"')
            cdc_count = cursor.fetchone()[0]
            self.stdout.write(f"  CDC 용기 수: {cdc_count}개\n")
            
            # 2. 현재 스냅샷 테이블 비우기
            self.stdout.write("\n=== 스냅샷 테이블 초기화 ===\n")
            cursor.execute("DELETE FROM cy_cylinder_current")
            deleted = cursor.rowcount
            self.stdout.write(f"  삭제된 레코드: {deleted}개\n")
            
            # 3. 전체 용기 동기화
            self.stdout.write("\n=== 전체 용기 동기화 시작 ===\n")
            cursor.execute('SELECT RTRIM("CYLINDER_NO") FROM "fcms_cdc"."ma_cylinders"')
            cylinder_nos = [row[0] for row in cursor.fetchall()]
            
            success_count = 0
            error_count = 0
            
            for i, cylinder_no in enumerate(cylinder_nos, 1):
                try:
                    cursor.execute("SELECT sync_cylinder_current_single(%s)", [cylinder_no])
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    if error_count <= 5:
                        self.stdout.write(f"  [오류] {cylinder_no}: {str(e)[:50]}\n")
                
                if i % 500 == 0:
                    self.stdout.write(f"  진행 중: {i}/{len(cylinder_nos)} ({i*100//len(cylinder_nos)}%)...\n")
            
            self.stdout.write(f"\n  성공: {success_count}개\n")
            self.stdout.write(f"  실패: {error_count}개\n")
            
            # 4. 결과 확인
            self.stdout.write("\n=== 동기화 결과 ===\n")
            cursor.execute("SELECT COUNT(*) FROM cy_cylinder_current")
            snapshot_count = cursor.fetchone()[0]
            self.stdout.write(f"  스냅샷 용기 수: {snapshot_count}개\n")
            
            cursor.execute("SELECT COUNT(DISTINCT cylinder_no_trimmed) FROM cy_cylinder_current")
            unique_count = cursor.fetchone()[0]
            self.stdout.write(f"  고유 용기번호 수: {unique_count}개\n")
            
            # 5. CF4 YC 확인
            self.stdout.write("\n=== CF4 YC 440L 용기 확인 ===\n")
            cursor.execute("""
                SELECT 
                    COALESCE(dashboard_enduser::text, 'NULL') as enduser,
                    COUNT(*) as qty
                FROM cy_cylinder_current
                WHERE dashboard_gas_name = 'CF4'
                  AND dashboard_cylinder_spec_name LIKE '%YC%'
                  AND dashboard_capacity = 440
                GROUP BY dashboard_enduser
                ORDER BY dashboard_enduser NULLS LAST
            """)
            
            results = cursor.fetchall()
            total = 0
            for row in results:
                self.stdout.write(f"  EndUser={row[0]}: {row[1]}개\n")
                total += row[1]
            self.stdout.write(f"\n  CF4 YC 440L 총: {total}개\n")
            
            self.stdout.write("\n[완료] 전체 용기 재동기화 완료\n")










