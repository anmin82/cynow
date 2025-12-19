"""
예약번호 생성 서비스

FCMS 문서번호 (FP+YY+6자리)를 예약하여 가이드 제공
"""

from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import re
from ..models import ReservedDocNo, PO
from ..repositories.fcms_repository import FcmsRepository


class ReservationService:
    """예약번호 생성 및 관리 서비스"""
    
    # 번호 형식: FP + YY(년도) + 6자리 연번
    # 예: FP240001, FP240002, ...
    DOC_NO_PATTERN = re.compile(r'^FP(\d{2})(\d{6})$')
    
    @classmethod
    def generate_doc_no(cls, doc_type: str, po: PO, max_retries=5):
        """
        예약 문서번호 생성
        
        Args:
            doc_type: 'ARRIVAL_SHIPPING' 또는 'MOVE_REPORT'
            po: PO 객체
            max_retries: 충돌 시 재시도 횟수
        
        Returns:
            ReservedDocNo 객체
        
        Raises:
            ValueError: 번호 생성 실패 시
        """
        
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    # 1. FCMS에서 현재 최대 번호 조회
                    latest_no = cls._get_latest_fcms_doc_no(doc_type)
                    
                    # 2. 다음 번호 계산
                    next_no = cls._calculate_next_no(latest_no)
                    
                    # 3. CYNOW 예약 테이블에서도 중복 확인
                    while cls._is_number_reserved(next_no):
                        next_no = cls._increment_doc_no(next_no)
                    
                    # 4. 예약 생성
                    reserved = ReservedDocNo.objects.create(
                        po=po,
                        doc_type=doc_type,
                        reserved_no=next_no,
                        expires_at=timezone.now() + timedelta(hours=48),  # 48시간 유효
                        status='RESERVED'
                    )
                    
                    return reserved
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    raise ValueError(f"예약번호 생성 실패 (최대 재시도 초과): {e}")
                # 충돌 시 재시도
                continue
        
        raise ValueError("예약번호 생성 실패")
    
    @classmethod
    def _get_latest_fcms_doc_no(cls, doc_type: str) -> str:
        """
        FCMS CDC 테이블에서 최신 문서번호 조회
        
        Args:
            doc_type: 'ARRIVAL_SHIPPING' 또는 'MOVE_REPORT'
        
        Returns:
            최신 문서번호 (예: FP240125)
        """
        if doc_type == 'ARRIVAL_SHIPPING':
            # TR_ORDERS 테이블에서 ARRIVAL_SHIPPING_NO 최대값
            latest = FcmsRepository.get_latest_arrival_shipping_no()
        elif doc_type == 'MOVE_REPORT':
            # TR_MOVE_REPORTS 테이블에서 MOVE_REPORT_NO 최대값
            latest = FcmsRepository.get_latest_move_report_no()
        else:
            raise ValueError(f"알 수 없는 문서 유형: {doc_type}")
        
        # 번호가 없으면 올해 첫 번호 반환
        if not latest:
            current_year = timezone.now().strftime('%y')
            return f"FP{current_year}000000"
        
        return latest
    
    @classmethod
    def _calculate_next_no(cls, current_no: str) -> str:
        """
        다음 번호 계산
        
        Args:
            current_no: 현재 번호 (예: FP240125)
        
        Returns:
            다음 번호 (예: FP240126)
        """
        if not current_no:
            current_year = timezone.now().strftime('%y')
            return f"FP{current_year}000001"
        
        match = cls.DOC_NO_PATTERN.match(current_no)
        if not match:
            # 형식이 맞지 않으면 새로 시작
            current_year = timezone.now().strftime('%y')
            return f"FP{current_year}000001"
        
        year = match.group(1)
        seq = int(match.group(2))
        
        current_year = timezone.now().strftime('%y')
        
        # 년도가 바뀌면 연번 초기화
        if year != current_year:
            return f"FP{current_year}000001"
        
        # 연번 +1
        next_seq = seq + 1
        return f"FP{year}{next_seq:06d}"
    
    @classmethod
    def _increment_doc_no(cls, doc_no: str) -> str:
        """
        문서번호 +1 증가
        
        Args:
            doc_no: 문서번호 (예: FP240125)
        
        Returns:
            증가된 번호 (예: FP240126)
        """
        match = cls.DOC_NO_PATTERN.match(doc_no)
        if not match:
            raise ValueError(f"잘못된 문서번호 형식: {doc_no}")
        
        year = match.group(1)
        seq = int(match.group(2)) + 1
        
        return f"FP{year}{seq:06d}"
    
    @classmethod
    def _is_number_reserved(cls, doc_no: str) -> bool:
        """
        번호가 이미 예약되었는지 확인
        
        Args:
            doc_no: 문서번호
        
        Returns:
            예약 여부
        """
        return ReservedDocNo.objects.filter(reserved_no=doc_no).exists()
    
    @classmethod
    def check_and_expire_reservations(cls):
        """
        만료된 예약번호 처리 (배치 작업용)
        
        Returns:
            만료 처리된 개수
        """
        expired_reservations = ReservedDocNo.objects.filter(
            status='RESERVED',
            expires_at__lt=timezone.now()
        )
        
        count = expired_reservations.update(status='EXPIRED')
        
        return count
    
    @classmethod
    def release_reservation(cls, reserved_doc: ReservedDocNo):
        """
        예약 해제 (수동)
        
        Args:
            reserved_doc: ReservedDocNo 객체
        """
        if reserved_doc.status == 'RESERVED':
            reserved_doc.status = 'EXPIRED'
            reserved_doc.save(update_fields=['status'])
    
    @classmethod
    def get_reserved_numbers_for_po(cls, po: PO):
        """
        PO에 할당된 예약번호 목록 조회
        
        Args:
            po: PO 객체
        
        Returns:
            ReservedDocNo QuerySet
        """
        return po.reserved_numbers.filter(
            status__in=['RESERVED', 'MATCHED']
        ).order_by('doc_type', 'reserved_at')

