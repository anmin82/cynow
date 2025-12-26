"""
일간 재고 스냅샷 생성 명령

사용법:
    # 오늘 스냅샷 생성
    python manage.py create_inventory_snapshot

    # 특정 날짜 스냅샷 생성
    python manage.py create_inventory_snapshot --date 2025-12-25
    
    # 용기 재고 동기화 후 스냅샷 생성
    python manage.py create_inventory_snapshot --sync-cylinders

cron/스케줄러 설정 예시:
    # 매일 자정(00:00)에 스냅샷 생성
    0 0 * * * cd /path/to/cynow && python manage.py create_inventory_snapshot
"""

from datetime import date, datetime
from django.core.management.base import BaseCommand, CommandError
from inventory.services import InventoryService


class Command(BaseCommand):
    help = '일간 재고 스냅샷 생성'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='스냅샷 기준일 (YYYY-MM-DD, 기본: 오늘)'
        )
        parser.add_argument(
            '--sync-cylinders',
            action='store_true',
            help='cy_cylinder_current에서 용기 재고 동기화 후 스냅샷 생성'
        )
    
    def handle(self, *args, **options):
        # 날짜 파싱
        snapshot_date = None
        if options['date']:
            try:
                snapshot_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError(f"잘못된 날짜 형식: {options['date']} (YYYY-MM-DD 필요)")
        
        # 용기 재고 동기화
        if options['sync_cylinders']:
            self.stdout.write('용기 재고 동기화 중...')
            result = InventoryService.sync_cylinder_inventory_from_current()
            self.stdout.write(
                self.style.SUCCESS(
                    f"동기화 완료: {result.get('synced', 0)}건 생성, "
                    f"{result.get('deleted', 0)}건 삭제"
                )
            )
        
        # 스냅샷 생성
        self.stdout.write(f'스냅샷 생성 중... (날짜: {snapshot_date or "오늘"})')
        
        try:
            log = InventoryService.create_daily_snapshot(
                snapshot_date=snapshot_date,
                triggered_by='MANUAL'
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"스냅샷 생성 완료!\n"
                    f"  - 날짜: {log.snapshot_date}\n"
                    f"  - 용기 스냅샷: {log.cylinder_snapshots_created}건\n"
                    f"  - 제품 스냅샷: {log.product_snapshots_created}건\n"
                    f"  - 상태: {log.get_status_display()}"
                )
            )
        except Exception as e:
            raise CommandError(f"스냅샷 생성 실패: {e}")

