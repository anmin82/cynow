"""cy_cylinder_current 스냅샷 테이블 동기화"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'cy_cylinder_current 스냅샷 테이블 동기화'

    def add_arguments(self, parser):
        parser.add_argument(
            '--incremental',
            action='store_true',
            help='증분 갱신 (최근 1시간 내 변경된 용기만)'
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=1,
            help='증분 갱신 시간 범위 (기본값: 1시간)'
        )

    def handle(self, *args, **options):
        incremental = options['incremental']
        hours = options['hours']
        
        with connection.cursor() as cursor:
            if incremental:
                # 증분 갱신: 최근 N시간 내 변경된 용기만
                cutoff_time = timezone.now() - timedelta(hours=hours)
                self.stdout.write(f"증분 갱신 모드: {cutoff_time} 이후 변경된 용기만 갱신")
                
                cursor.execute("""
                    WITH updated_cylinders AS (
                        SELECT DISTINCT c."CYLINDER_NO"
                        FROM "fcms_cdc"."ma_cylinders" c
                        LEFT JOIN "fcms_cdc"."tr_latest_cylinder_statuses" ls 
                            ON c."CYLINDER_NO" = ls."CYLINDER_NO"
                        WHERE c."UPDATE_DATETIME" >= %s
                           OR c."ADD_DATETIME" >= %s
                           OR ls."MOVE_DATE" >= %s
                    )
                    SELECT "CYLINDER_NO" FROM updated_cylinders
                """, [cutoff_time, cutoff_time, cutoff_time])
            else:
                # 전체 갱신
                self.stdout.write("전체 갱신 모드: 모든 용기 갱신")
                cursor.execute('SELECT "CYLINDER_NO" FROM "fcms_cdc"."ma_cylinders"')
            
            cylinder_nos = [row[0] for row in cursor.fetchall()]
            total = len(cylinder_nos)
            
            if total == 0:
                self.stdout.write(self.style.WARNING("갱신할 용기가 없습니다."))
                return
            
            self.stdout.write(f"총 {total:,}개 용기 갱신 시작...")
            
            # 각 용기에 대해 sync_cylinder_current_single 함수 호출
            updated = 0
            errors = 0
            
            for i, cylinder_no in enumerate(cylinder_nos, 1):
                try:
                    cursor.execute("SELECT sync_cylinder_current_single(%s)", [cylinder_no])
                    updated += 1
                    
                    if i % 100 == 0:
                        self.stdout.write(f"진행: {i:,}/{total:,} ({i*100//total}%)")
                except Exception as e:
                    errors += 1
                    self.stdout.write(self.style.ERROR(f"오류 (용기번호: {cylinder_no}): {str(e)}"))
            
            self.stdout.write(self.style.SUCCESS(f"\n갱신 완료: {updated:,}개 성공, {errors}개 실패"))
            
            # 통계 확인
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN snapshot_updated_at > NOW() - INTERVAL '1 minute' THEN 1 END) as just_updated
                FROM cy_cylinder_current
            """)
            stats = cursor.fetchone()
            self.stdout.write(f"현재 스냅샷: 총 {stats[0]:,}개, 방금 갱신: {stats[1]:,}개")










