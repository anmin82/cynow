"""월말 스냅샷 적재

- 운영에서는 보통 '매일 00:05' 같은 스케줄에 걸어두고, 이 커맨드가 '매월 1일'에만 동작하도록 사용합니다.
- 예: 매일 실행하되, 매월 1일 00:05에 전월 말(어제) 23:59:59 시각으로 스냅샷을 남김
"""

from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.repositories.view_repository import ViewRepository
from history.models import HistInventorySnapshot, HistSnapshotRequest, SnapshotRequestStatus, SnapshotType


class Command(BaseCommand):
    help = "월말 스냅샷 적재 (전월 말 23:59:59 기준, snapshot_type=DAILY)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="매월 1일이 아니어도 강제로 실행",
        )
        parser.add_argument(
            "--target-date",
            help="스냅샷 기준일(YYYY-MM-DD). 지정하면 해당 날짜 23:59:59로 저장",
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        force = bool(options.get("force"))
        target_date_str = options.get("target_date")

        if target_date_str:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        else:
            # 기본: 매월 1일에 실행되면 전월 말(=어제)을 타겟으로
            if today.day != 1 and not force:
                self.stdout.write("Not month start. Skipped. (Run on 1st day or use --force/--target-date)")
                return
            target_date = today - timedelta(days=1)

        snapshot_datetime = timezone.make_aware(
            datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)
        )

        self.stdout.write(f"Taking month-end snapshot at {snapshot_datetime} (target_date={target_date})")

        inventory_data = ViewRepository.get_inventory_view()
        if not inventory_data:
            raise RuntimeError("vw_cynow_inventory 결과가 비어있습니다. VIEW/동기화 상태를 확인하세요.")

        inserted_count = 0
        skipped_count = 0

        for row in inventory_data:
            try:
                HistInventorySnapshot.objects.create(
                    snapshot_datetime=snapshot_datetime,
                    snapshot_type=SnapshotType.DAILY,
                    cylinder_type_key=row.get("cylinder_type_key", "") or "",
                    gas_name=row.get("gas_name", "") or "",
                    capacity=row.get("capacity"),
                    valve_spec=row.get("valve_spec"),
                    cylinder_spec=row.get("cylinder_spec"),
                    usage_place=row.get("usage_place"),
                    status=row.get("status", "") or "",
                    location=row.get("location", "") or "",
                    qty=row.get("qty", 0) or 0,
                    source_view_updated_at=None,
                    created_by=None,
                )
                inserted_count += 1
            except Exception:
                skipped_count += 1

        HistSnapshotRequest.objects.create(
            requested_at=timezone.now(),
            requested_by=None,
            reason=f"월말 스냅샷 (target={target_date})",
            status=SnapshotRequestStatus.SUCCESS,
            message=f"inserted={inserted_count} skipped={skipped_count}",
        )

        self.stdout.write(self.style.SUCCESS(f"Done. inserted={inserted_count}, skipped={skipped_count}"))


