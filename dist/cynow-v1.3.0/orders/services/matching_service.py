"""
FCMS 매칭 검증 서비스

예약번호가 FCMS에 실제로 입력되었는지 확인하고 매칭 상태 업데이트
"""

from django.utils import timezone
from typing import Dict, Optional
from ..models import PO, ReservedDocNo, POFcmsMatch
from ..repositories.fcms_repository import FcmsRepository


class MatchingService:
    """PO와 FCMS 문서 매칭 서비스"""
    
    @classmethod
    def check_reservation_match(cls, reserved_doc: ReservedDocNo) -> str:
        """
        예약번호가 FCMS에 입력되었는지 확인
        
        Args:
            reserved_doc: ReservedDocNo 객체
        
        Returns:
            매칭 상태 ('MATCHED', 'NOT_ENTERED', 'MISMATCH')
        """
        if reserved_doc.doc_type == 'ARRIVAL_SHIPPING':
            fcms_doc = FcmsRepository.find_order_by_arrival_shipping_no(
                reserved_doc.reserved_no
            )
        elif reserved_doc.doc_type == 'MOVE_REPORT':
            fcms_doc = FcmsRepository.find_move_report_by_no(
                reserved_doc.reserved_no
            )
        else:
            return 'NOT_ENTERED'
        
        if fcms_doc:
            # 정확히 매칭됨
            reserved_doc.status = 'MATCHED'
            reserved_doc.matched_fcms_doc_key = str(fcms_doc['id'])
            reserved_doc.matched_at = timezone.now()
            reserved_doc.save()
            
            # POFcmsMatch 레코드 생성/업데이트
            cls._create_or_update_match(reserved_doc, fcms_doc, 'MATCHED')
            
            return 'MATCHED'
        else:
            # FCMS에 아직 입력되지 않음
            return 'NOT_ENTERED'
    
    @classmethod
    def check_po_match(cls, po: PO) -> Dict[str, any]:
        """
        PO 전체에 대한 FCMS 매칭 상태 확인
        
        Args:
            po: PO 객체
        
        Returns:
            매칭 결과 요약 dict
        """
        result = {
            'po': po,
            'reservations': [],
            'matched_count': 0,
            'not_entered_count': 0,
            'mismatch_count': 0,
        }
        
        for reserved in po.reserved_numbers.filter(status__in=['RESERVED', 'MATCHED']):
            status = cls.check_reservation_match(reserved)
            
            result['reservations'].append({
                'reserved_no': reserved.reserved_no,
                'doc_type': reserved.doc_type,
                'status': status,
            })
            
            if status == 'MATCHED':
                result['matched_count'] += 1
            elif status == 'NOT_ENTERED':
                result['not_entered_count'] += 1
            elif status == 'MISMATCH':
                result['mismatch_count'] += 1
        
        # PO 상태 업데이트
        if result['matched_count'] > 0 and result['not_entered_count'] == 0:
            po.status = 'IN_PROGRESS'
            po.save(update_fields=['status'])
        
        return result
    
    @classmethod
    def _create_or_update_match(cls, reserved_doc: ReservedDocNo, fcms_doc: Dict, match_state: str):
        """
        POFcmsMatch 레코드 생성 또는 업데이트
        
        Args:
            reserved_doc: ReservedDocNo 객체
            fcms_doc: FCMS 문서 정보
            match_state: 매칭 상태
        """
        arrival_shipping_no = ''
        move_report_no = ''
        
        if reserved_doc.doc_type == 'ARRIVAL_SHIPPING':
            arrival_shipping_no = fcms_doc.get('arrival_shipping_no', '')
        elif reserved_doc.doc_type == 'MOVE_REPORT':
            move_report_no = fcms_doc.get('move_report_no', '')
        
        POFcmsMatch.objects.update_or_create(
            po=reserved_doc.po,
            reserved_doc=reserved_doc,
            defaults={
                'arrival_shipping_no': arrival_shipping_no,
                'move_report_no': move_report_no,
                'match_state': match_state,
                'last_checked_at': timezone.now(),
            }
        )
    
    @classmethod
    def suggest_mismatch_candidates(cls, po: PO) -> list:
        """
        예약번호와 다르지만 같은 PO로 추정되는 FCMS 문서 찾기
        
        Args:
            po: PO 객체
        
        Returns:
            후보 문서 리스트
        """
        candidates = []
        
        # 같은 거래처의 최근 주문 조회
        if po.supplier_user_code:
            recent_orders = FcmsRepository.search_orders_by_supplier(
                po.supplier_user_code,
                limit=50
            )
            
            # 예약번호와 매칭되지 않은 것만 필터
            reserved_nos = set(
                po.reserved_numbers.values_list('reserved_no', flat=True)
            )
            
            for order in recent_orders:
                if order['arrival_shipping_no'] not in reserved_nos:
                    # 수량, 날짜 등으로 유사도 판단 가능
                    candidates.append({
                        'fcms_doc': order,
                        'similarity_score': cls._calculate_similarity(po, order),
                        'reason': '같은 거래처의 미매칭 주문',
                    })
        
        # 유사도 순으로 정렬
        candidates.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return candidates[:10]  # 상위 10개만
    
    @classmethod
    def _calculate_similarity(cls, po: PO, fcms_doc: Dict) -> float:
        """
        PO와 FCMS 문서 간 유사도 계산 (0~1)
        
        Args:
            po: PO 객체
            fcms_doc: FCMS 문서 정보
        
        Returns:
            유사도 점수
        """
        score = 0.0
        
        # 거래처 일치 (40점)
        if po.supplier_user_code == fcms_doc.get('supplier_user_code'):
            score += 0.4
        
        # 수량 근사 (30점)
        po_qty = po.total_qty
        fcms_qty = fcms_doc.get('total_qty', 0)
        if po_qty > 0 and fcms_qty > 0:
            qty_ratio = min(po_qty, fcms_qty) / max(po_qty, fcms_qty)
            score += 0.3 * qty_ratio
        
        # 날짜 근접성 (30점)
        # TODO: 날짜 비교 로직 추가
        
        return score
    
    @classmethod
    def manual_match(cls, po: PO, fcms_doc_no: str, doc_type: str, user, note: str = '') -> POFcmsMatch:
        """
        수동 매칭 (관리자가 직접 연결)
        
        Args:
            po: PO 객체
            fcms_doc_no: FCMS 문서번호
            doc_type: 문서 유형
            user: 매칭 수행자
            note: 메모
        
        Returns:
            POFcmsMatch 객체
        """
        arrival_shipping_no = ''
        move_report_no = ''
        
        if doc_type == 'ARRIVAL_SHIPPING':
            arrival_shipping_no = fcms_doc_no
        elif doc_type == 'MOVE_REPORT':
            move_report_no = fcms_doc_no
        
        match = POFcmsMatch.objects.create(
            po=po,
            reserved_doc=None,  # 수동 매칭이므로 예약 없음
            arrival_shipping_no=arrival_shipping_no,
            move_report_no=move_report_no,
            match_state='MATCHED',
            is_manual_match=True,
            manual_matched_by=user,
            note=note
        )
        
        # PO 상태 업데이트
        po.status = 'MATCHED'
        po.save(update_fields=['status'])
        
        return match
    
    @classmethod
    def batch_check_all_reservations(cls, limit: int = 100) -> Dict[str, int]:
        """
        모든 예약번호에 대한 배치 매칭 확인
        
        Args:
            limit: 최대 확인 건수
        
        Returns:
            실행 결과 요약
        """
        reservations = ReservedDocNo.objects.filter(
            status='RESERVED'
        )[:limit]
        
        result = {
            'checked': 0,
            'matched': 0,
            'not_entered': 0,
            'expired': 0,
        }
        
        for reserved in reservations:
            # 만료 확인
            if reserved.is_expired():
                reserved.status = 'EXPIRED'
                reserved.save()
                result['expired'] += 1
                continue
            
            # 매칭 확인
            status = cls.check_reservation_match(reserved)
            result['checked'] += 1
            
            if status == 'MATCHED':
                result['matched'] += 1
            elif status == 'NOT_ENTERED':
                result['not_entered'] += 1
        
        return result

