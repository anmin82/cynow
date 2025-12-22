"""스냅샷이 없을 때(또는 과거 데이터가 필요할 때) 현재 VIEW 값을 '추정치'로 과거 월말 스냅샷에 채우는 커맨드

주의:
- 과거 시점의 실제 재고/상태를 복원하는 것이 아니라, '현재 값으로 추정'하여 스냅샷을 채웁니다.
- 그래프가 "데이터 없음"으로 비는 문제를 해결하고, 조회 성능(504)을 안정화하기 위한 목적입니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.repositories.view_repository import ViewRepository
from history.models import (
    HistInventorySnapshot,
    HistSnapshotRequest,
    SnapshotRequestStatus,
    SnapshotType,
)


@dataclass
class MonthEnd:
    year: int
    month: int


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _month_end_dates(start: date, end: date) -> List[date]:
    """start~end 범위의 각 '월말 날짜' 리스트"""
    # start 월의 1일로 정규화
    cur = date(start.year, start.month, 1)
    last_month = date(end.year, end.month, 1)
    out: List[date] = []

    while cur <= last_month:
        # 다음달 1일 - 1일 = 월말
        if cur.month == 12:
            next_month = date(cur.year + 1, 1, 1)
        else:
            next_month = date(cur.year, cur.month + 1, 1)
        month_end = next_month - timedelta(days=1)
        out.append(month_end)
        cur = next_month

    # end가 월 중간이면, end 월말도 포함(요청자가 월말 기준을 원하므로 유지)
    return out


class Command(BaseCommand):
    help = "현재 VIEW 값으로 월말 스냅샷을 수동(MANUAL)으로 백필(추정치)합니다."

    def add_arguments(self, parser):
        parser.add_argument("--start", required=True, help="시작일 (YYYY-MM-DD), 해당 월말부터 생성")
        parser.add_argument("--end", required=True, help="종료일 (YYYY-MM-DD), 해당 월말까지 생성")
        parser.add_argument(
            "--type",
            default="MANUAL",
            choices=["MANUAL", "DAILY"],
            help="snapshot_type (기본: MANUAL)",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="동일 snapshot_datetime/snapshot_type 데이터가 있으면 삭제 후 재적재",
        )
        parser.add_argument(
            "--reason",
            default="스냅샷 누락 보정(현재값 추정) 월말 백필",
            help="HistSnapshotRequest 기록용 사유",
        )

    def handle(self, *args, **options):
        start = _parse_date(options["start"])
        end = _parse_date(options["end"])
        snapshot_type = SnapshotType.MANUAL if options["type"] == "MANUAL" else SnapshotType.DAILY
        overwrite = bool(options["overwrite"])
        reason = options["reason"]

        month_ends = _month_end_dates(start, end)
        if not month_ends:
            self.stdout.write(self.style.WARNING("생성할 월말이 없습니다."))
            return

        # VIEW는 현재 값이므로 한 번만 읽고 재사용
        inventory_data = ViewRepository.get_inventory_view()
        if not inventory_data:
            raise RuntimeError("vw_cynow_inventory 결과가 비어있습니다. VIEW/동기화 상태를 확인하세요.")

        total_inserted = 0
        total_deleted = 0
        total_skipped = 0

        for d in month_ends:
            # KST 기준 월말 23:59:59로 저장
            snap_dt = timezone.make_aware(datetime(d.year, d.month, d.day, 23, 59, 59))

            if overwrite:
                deleted, _ = HistInventorySnapshot.objects.filter(
                    snapshot_datetime=snap_dt,
                    snapshot_type=snapshot_type,
                ).delete()
                total_deleted += deleted

            inserted = 0
            skipped = 0

            for row in inventory_data:
                try:
                    HistInventorySnapshot.objects.create(
                        snapshot_datetime=snap_dt,
                        snapshot_type=snapshot_type,
                        cylinder_type_key=row.get("cylinder_type_key", "") or "",
                        gas_name=row.get("gas_name", "") or "",
                        capacity=row.get("capacity"),
                        valve_spec=row.get("valve_spec"),
                        cylinder_spec=row.get("cylinder_spec"),
                        usage_place=row.get("usage_place"),
                        status=row.get("status", "") or "",
                        location=row.get("location", "") or "",
                        qty=row.get("qty", 0) or 0,
                        source_view_updated_at=None,  # 추정치이므로 null
                        created_by=None,
                    )
                    inserted += 1
                except Exception:
                    # UNIQUE 충돌 등은 스킵
                    skipped += 1

            total_inserted += inserted
            total_skipped += skipped
            self.stdout.write(f"{snap_dt.date()} ({snapshot_type}) inserted={inserted}, skipped={skipped}")

        HistSnapshotRequest.objects.create(
            requested_at=timezone.now(),
            requested_by=None,
            reason=reason,
            status=SnapshotRequestStatus.SUCCESS,
            message=f"backfill month-ends={len(month_ends)} type={snapshot_type} overwrite={overwrite} deleted={total_deleted} inserted={total_inserted} skipped={total_skipped}",
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill done. month_ends={len(month_ends)} deleted={total_deleted} inserted={total_inserted} skipped={total_skipped}"
            )
        )


