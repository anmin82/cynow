"""cy_cylinder_current에 있지만 fcms_cdc.ma_cylinders에 없는 고아 용기 정리"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'cy_cylinder_current에 있지만 fcms_cdc.ma_cylinders에 없는 고아 용기 정리'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 삭제하지 않고 확인만 수행',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        with connection.cursor() as cursor:
            self.stdout.write("\n=== 고아 용기 확인 ===\n")
            
            # 고아 용기 확인
            cursor.execute("""
                SELECT 
                    c.cylinder_no,
                    c.dashboard_gas_name,
                    c.dashboard_status,
                    c.snapshot_updated_at
                FROM cy_cylinder_current c
                LEFT JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE mc."CYLINDER_NO" IS NULL
                ORDER BY c.cylinder_no
            """)
            
            columns = [col[0] for col in cursor.description]
            orphaned = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            if not orphaned:
                self.stdout.write(self.style.SUCCESS("[OK] 고아 용기가 없습니다.\n"))
                return
            
            self.stdout.write(f"[경고] {len(orphaned)}개의 고아 용기를 발견했습니다:\n")
            for cyl in orphaned[:20]:  # 최대 20개만 표시
                self.stdout.write(f"   - {cyl['cylinder_no']}: {cyl['dashboard_gas_name']} ({cyl['dashboard_status']})")
            
            if len(orphaned) > 20:
                self.stdout.write(f"   ... 외 {len(orphaned) - 20}개")
            
            # 용기종류별 집계
            cursor.execute("""
                SELECT 
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    COUNT(*) as count
                FROM cy_cylinder_current c
                LEFT JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE mc."CYLINDER_NO" IS NULL
                GROUP BY c.dashboard_gas_name, c.dashboard_capacity
                ORDER BY count DESC
            """)
            
            columns = [col[0] for col in cursor.description]
            summary = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            self.stdout.write("\n용기종류별 고아 용기 수:\n")
            for row in summary:
                self.stdout.write(f"   - {row['dashboard_gas_name']} ({row['dashboard_capacity']}): {row['count']}개")
            
            # 삭제 실행
            if dry_run:
                self.stdout.write(self.style.WARNING("\n[DRY-RUN] 모드: 실제 삭제하지 않습니다."))
                self.stdout.write("실제 삭제하려면 --dry-run 옵션 없이 실행하세요.")
            else:
                self.stdout.write(f"\n고아 용기 {len(orphaned)}개를 삭제합니다...")
                cursor.execute("""
                    DELETE FROM cy_cylinder_current
                    WHERE cylinder_no IN (
                        SELECT c.cylinder_no
                        FROM cy_cylinder_current c
                        LEFT JOIN "fcms_cdc"."ma_cylinders" mc 
                            ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                        WHERE mc."CYLINDER_NO" IS NULL
                    )
                """)
                deleted_count = cursor.rowcount
                self.stdout.write(self.style.SUCCESS(f"[완료] {deleted_count}개의 고아 용기를 삭제했습니다."))
                self.stdout.write("\n대시보드를 새로고침하면 카드가 사라집니다.")

