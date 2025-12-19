"""
PO 데이터 조회 Repository

복잡한 PO 조회 로직을 캡슐화
"""

from django.db.models import Q, Count, Sum, Prefetch
from typing import List, Optional
from ..models import PO, POItem, ReservedDocNo, POFcmsMatch, POProgressSnapshot


class PORepository:
    """PO 조회 레이어"""
    
    @staticmethod
    def get_po_list(filters: dict = None, order_by: str = '-received_at', limit: int = None):
        """
        PO 리스트 조회
        
        Args:
            filters: 필터 조건 dict
            order_by: 정렬 기준
            limit: 최대 조회 건수
        
        Returns:
            PO QuerySet
        """
        queryset = PO.objects.all()
        
        if filters:
            # 상태 필터
            if 'status' in filters:
                queryset = queryset.filter(status=filters['status'])
            
            # 거래처 필터
            if 'supplier_user_code' in filters:
                queryset = queryset.filter(
                    supplier_user_code__icontains=filters['supplier_user_code']
                )
            
            # 고객 발주번호 필터
            if 'customer_order_no' in filters:
                queryset = queryset.filter(
                    customer_order_no__icontains=filters['customer_order_no']
                )
            
            # 역수입 데이터 필터
            if 'is_backfilled' in filters:
                queryset = queryset.filter(is_backfilled=filters['is_backfilled'])
            
            # 검토 필요 필터
            if 'needs_review' in filters:
                queryset = queryset.filter(needs_review=filters['needs_review'])
            
            # 날짜 범위 필터
            if 'received_from' in filters:
                queryset = queryset.filter(received_at__gte=filters['received_from'])
            
            if 'received_to' in filters:
                queryset = queryset.filter(received_at__lte=filters['received_to'])
            
            # 납기 범위 필터
            if 'due_from' in filters:
                queryset = queryset.filter(due_date__gte=filters['due_from'])
            
            if 'due_to' in filters:
                queryset = queryset.filter(due_date__lte=filters['due_to'])
        
        queryset = queryset.order_by(order_by)
        
        if limit:
            queryset = queryset[:limit]
        
        return queryset.prefetch_related('items', 'reserved_numbers', 'fcms_matches')
    
    @staticmethod
    def get_po_detail(po_no: str) -> Optional[PO]:
        """
        PO 상세 조회
        
        Args:
            po_no: PO 번호
        
        Returns:
            PO 객체 또는 None
        """
        try:
            return PO.objects.prefetch_related(
                'items',
                'reserved_numbers',
                'fcms_matches',
                'schedules',
                'progress_snapshots'
            ).get(po_no=po_no)
        except PO.DoesNotExist:
            return None
    
    @staticmethod
    def get_pos_needing_review():
        """
        검토가 필요한 PO 목록 조회
        
        Returns:
            PO QuerySet
        """
        return PO.objects.filter(
            needs_review=True,
            is_backfilled=True
        ).prefetch_related('items', 'fcms_matches').order_by('-received_at')
    
    @staticmethod
    def get_manufacturing_schedule(days_ahead: int = 30):
        """
        제조부용 납기/우선순위 목록 조회
        
        Args:
            days_ahead: 앞으로 N일 이내 납기
        
        Returns:
            PO QuerySet (납기순 정렬)
        """
        from django.utils import timezone
        from datetime import timedelta
        
        end_date = timezone.now().date() + timedelta(days=days_ahead)
        
        return PO.objects.filter(
            status__in=['RESERVED', 'MATCHED', 'IN_PROGRESS'],
            due_date__lte=end_date,
            due_date__isnull=False
        ).prefetch_related(
            'items',
            'progress_snapshots'
        ).annotate(
            total_qty=Sum('items__qty')
        ).order_by('due_date', '-received_at')
    
    @staticmethod
    def get_po_statistics():
        """
        PO 통계 요약
        
        Returns:
            통계 dict
        """
        from django.db.models import Count, Q
        
        total_count = PO.objects.count()
        
        status_counts = PO.objects.values('status').annotate(
            count=Count('id')
        )
        
        backfilled_count = PO.objects.filter(is_backfilled=True).count()
        needs_review_count = PO.objects.filter(needs_review=True).count()
        
        return {
            'total_count': total_count,
            'status_counts': {item['status']: item['count'] for item in status_counts},
            'backfilled_count': backfilled_count,
            'needs_review_count': needs_review_count,
        }

