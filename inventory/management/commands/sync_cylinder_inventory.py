"""
cy_cylinder_current에서 용기 재고 동기화

사용법:
    python manage.py sync_cylinder_inventory

cy_cylinder_current 테이블의 현재 상태를 CylinderInventory에 동기화
"""

from django.core.management.base import BaseCommand, CommandError
from inventory.services import InventoryService


class Command(BaseCommand):
    help = 'cy_cylinder_current에서 용기 재고 동기화'
    
    def handle(self, *args, **options):
        self.stdout.write('용기 재고 동기화 중...')
        
        try:
            result = InventoryService.sync_cylinder_inventory_from_current()
            
            if 'error' in result:
                raise CommandError(f"동기화 실패: {result['error']}")
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"용기 재고 동기화 완료!\n"
                    f"  - 생성: {result.get('synced', 0)}건\n"
                    f"  - 삭제: {result.get('deleted', 0)}건"
                )
            )
        except Exception as e:
            raise CommandError(f"동기화 실패: {e}")

