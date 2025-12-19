"""cy_cylinder_current 스냅샷 테이블 검증"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'cy_cylinder_current 스냅샷 테이블 검증'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 1. 총 용기 수 비교
            cursor.execute('SELECT COUNT(*) FROM "fcms_cdc"."ma_cylinders"')
            fcms_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM cy_cylinder_current')
            snapshot_count = cursor.fetchone()[0]
            
            self.stdout.write(f"FCMS 용기 수: {fcms_count:,}개")
            self.stdout.write(f"스냅샷 용기 수: {snapshot_count:,}개")
            
            if fcms_count != snapshot_count:
                self.stdout.write(self.style.WARNING(f"차이: {abs(fcms_count - snapshot_count):,}개"))
            else:
                self.stdout.write(self.style.SUCCESS("용기 수 일치"))
            
            # 2. EndUser 적용 현황
            cursor.execute("""
                SELECT 
                    dashboard_enduser,
                    COUNT(*) as qty,
                    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as pct
                FROM cy_cylinder_current
                GROUP BY dashboard_enduser
                ORDER BY qty DESC
            """)
            self.stdout.write("\nEndUser 분포:")
            for row in cursor.fetchall():
                self.stdout.write(f"  {row[0]}: {row[1]:,}개 ({row[2]}%)")
            
            # 3. 밸브 그룹 적용 현황
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN dashboard_valve_group_name IS NOT NULL THEN dashboard_valve_group_name
                        ELSE '그룹 없음'
                    END as valve_group,
                    COUNT(*) as qty
                FROM cy_cylinder_current
                GROUP BY valve_group
                ORDER BY qty DESC
                LIMIT 10
            """)
            self.stdout.write("\n밸브 그룹 분포 (Top 10):")
            for row in cursor.fetchall():
                self.stdout.write(f"  {row[0]}: {row[1]:,}개")
            
            # 4. 최근 갱신 상태
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN snapshot_updated_at > NOW() - INTERVAL '1 hour' THEN 1 END) as last_hour,
                    COUNT(CASE WHEN snapshot_updated_at > NOW() - INTERVAL '1 day' THEN 1 END) as last_day,
                    MAX(snapshot_updated_at) as last_update
                FROM cy_cylinder_current
            """)
            stats = cursor.fetchone()
            self.stdout.write(f"\n갱신 상태:")
            self.stdout.write(f"  최근 1시간: {stats[0]:,}개")
            self.stdout.write(f"  최근 1일: {stats[1]:,}개")
            self.stdout.write(f"  마지막 갱신: {stats[2]}")
            
            # 5. 데이터 정합성 검증
            cursor.execute("""
                SELECT COUNT(*) 
                FROM cy_cylinder_current 
                WHERE dashboard_gas_name IS NULL 
                   OR cylinder_type_key IS NULL
            """)
            null_count = cursor.fetchone()[0]
            
            if null_count > 0:
                self.stdout.write(self.style.WARNING(f"NULL 값 발견: {null_count}개"))
            else:
                self.stdout.write(self.style.SUCCESS("데이터 정합성 확인 완료"))

