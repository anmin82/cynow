"""매일 00:05 정기 스냅샷 적재"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
from history.models import HistInventorySnapshot, HistSnapshotRequest, SnapshotType, SnapshotRequestStatus
from core.repositories.view_repository import ViewRepository
from core.utils.cylinder_type import generate_cylinder_type_key


class Command(BaseCommand):
    help = '매일 00:05 정기 스냅샷 적재 (DAILY)'

    def handle(self, *args, **options):
        snapshot_datetime = timezone.now()
        self.stdout.write(f'Taking daily snapshot at {snapshot_datetime}')
        
        try:
            # VIEW에서 현재 인벤토리 데이터 조회
            inventory_data = ViewRepository.get_inventory_view()
            
            inserted_count = 0
            skipped_count = 0
            
            for row in inventory_data:
                try:
                    # source_view_updated_at을 timezone aware로 변환
                    source_updated_at = row.get('updated_at')
                    if source_updated_at and isinstance(source_updated_at, str):
                        try:
                            # 문자열을 datetime으로 파싱 후 timezone aware로 변환
                            dt = datetime.strptime(source_updated_at, '%Y-%m-%d %H:%M:%S')
                            source_updated_at = timezone.make_aware(dt)
                        except:
                            source_updated_at = None
                    elif source_updated_at and not timezone.is_aware(source_updated_at):
                        source_updated_at = timezone.make_aware(source_updated_at)
                    
                    HistInventorySnapshot.objects.create(
                        snapshot_datetime=snapshot_datetime,
                        snapshot_type=SnapshotType.DAILY,
                        cylinder_type_key=row.get('cylinder_type_key', ''),
                        gas_name=row.get('gas_name', ''),
                        capacity=row.get('capacity'),
                        valve_spec=row.get('valve_spec'),
                        cylinder_spec=row.get('cylinder_spec'),
                        usage_place=row.get('usage_place'),
                        status=row.get('status', ''),
                        location=row.get('location', ''),
                        qty=row.get('qty', 0),
                        source_view_updated_at=source_updated_at,
                        created_by=None,  # DAILY는 null
                    )
                    inserted_count += 1
                except Exception as e:
                    # UNIQUE 제약 위반 등은 스킵
                    skipped_count += 1
                    if inserted_count + skipped_count <= 5:
                        self.stdout.write(self.style.WARNING(f'Skipped: {e}'))
            
            # 성공 기록
            HistSnapshotRequest.objects.create(
                requested_at=snapshot_datetime,
                requested_by=None,
                reason='정기 스냅샷 (DAILY)',
                status=SnapshotRequestStatus.SUCCESS,
                message=f'{inserted_count} records inserted, {skipped_count} skipped'
            )
            
            self.stdout.write(self.style.SUCCESS(
                f'Successfully created daily snapshot: {inserted_count} records inserted, {skipped_count} skipped'
            ))
            
        except Exception as e:
            # 실패 기록
            HistSnapshotRequest.objects.create(
                requested_at=snapshot_datetime,
                requested_by=None,
                reason='정기 스냅샷 (DAILY)',
                status=SnapshotRequestStatus.FAILED,
                message=str(e)
            )
            self.stdout.write(self.style.ERROR(f'Error creating snapshot: {e}'))
            raise

