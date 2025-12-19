"""
PO 진행 현황 모니터링 서비스

FCMS 데이터를 기반으로 수주별 진행 현황 집계
"""

from django.utils import timezone
from decimal import Decimal
from typing import Dict
from ..models import PO, POProgressSnapshot
from ..repositories.fcms_repository import FcmsRepository


class MonitoringService:
    """PO 진행 현황 모니터링"""
    
    @classmethod
    def update_po_progress(cls, po: PO) -> POProgressSnapshot:
        """
        PO의 진행 현황 갱신
        
        Args:
            po: PO 객체
        
        Returns:
            POProgressSnapshot 객체
        """
        # 1. 수주 수량
        order_qty = po.total_qty
        
        # 2. FCMS 매칭된 문서번호 조회
        matched_docs = po.fcms_matches.filter(match_state='MATCHED')
        
        instruction_qty = 0
        filling_qty = 0
        warehouse_in_qty = 0
        shipping_qty = 0
        
        # 3. 각 매칭된 문서별로 진행 현황 집계
        for match in matched_docs:
            if match.arrival_shipping_no:
                progress = FcmsRepository.get_filling_progress_by_arrival_shipping_no(
                    match.arrival_shipping_no
                )
                
                instruction_qty += progress.get('instruction_count', 0)
                filling_qty += progress.get('filled_count', 0)
        
        # 4. 진행률 계산
        if order_qty > 0:
            progress_rate = Decimal(shipping_qty) / Decimal(order_qty) * Decimal('100.0')
        else:
            progress_rate = Decimal('0.00')
        
        # 5. 스냅샷 생성
        snapshot = POProgressSnapshot.objects.create(
            po=po,
            order_qty=order_qty,
            instruction_qty=instruction_qty,
            filling_qty=filling_qty,
            warehouse_in_qty=warehouse_in_qty,
            shipping_qty=shipping_qty,
            progress_rate=progress_rate
        )
        
        return snapshot
    
    @classmethod
    def get_latest_progress(cls, po: PO) -> Dict:
        """
        PO의 최신 진행 현황 조회
        
        Args:
            po: PO 객체
        
        Returns:
            진행 현황 dict
        """
        snapshot = po.progress_snapshots.order_by('-snapshot_at').first()
        
        if not snapshot:
            # 스냅샷이 없으면 새로 생성
            snapshot = cls.update_po_progress(po)
        
        return {
            'order_qty': snapshot.order_qty,
            'instruction_qty': snapshot.instruction_qty,
            'filling_qty': snapshot.filling_qty,
            'warehouse_in_qty': snapshot.warehouse_in_qty,
            'shipping_qty': snapshot.shipping_qty,
            'progress_rate': float(snapshot.progress_rate),
            'snapshot_at': snapshot.snapshot_at,
        }
    
    @classmethod
    def batch_update_all_progress(cls, limit: int = 100) -> int:
        """
        모든 진행 중인 PO의 현황 일괄 갱신
        
        Args:
            limit: 최대 갱신 건수
        
        Returns:
            갱신 건수
        """
        pos = PO.objects.filter(
            status__in=['MATCHED', 'IN_PROGRESS']
        )[:limit]
        
        count = 0
        for po in pos:
            try:
                cls.update_po_progress(po)
                count += 1
            except Exception:
                continue
        
        return count

