"""
FCMS 기존 데이터로부터 PO 역수입(Backfill)

FCMS에는 이미 많은 주문/이동서 데이터가 있으나 CYNOW PO가 없는 상태
이 Command는 FCMS 데이터를 분석하여 PO를 자동 생성(복원)
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import logging

from orders.models import PO, POItem, OrphanFcmsDoc, ReservedDocNo, POFcmsMatch
from orders.repositories.fcms_repository import FcmsRepository


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'FCMS 기존 데이터로부터 PO 역수입'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='최근 N일간의 데이터만 처리 (기본 90일)'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            default=1000,
            help='최대 처리 건수 (기본 1000건)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 저장 없이 시뮬레이션만 수행'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='이미 처리된 문서도 재처리'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        limit = options['limit']
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(self.style.SUCCESS(
            f"=== FCMS 데이터 역수입 시작 ==="
        ))
        self.stdout.write(f"- 기간: 최근 {days}일")
        self.stdout.write(f"- 최대 처리: {limit}건")
        self.stdout.write(f"- Dry Run: {'예' if dry_run else '아니오'}")
        self.stdout.write("")
        
        stats = {
            'total_checked': 0,
            'created': 0,
            'skipped': 0,
            'needs_review': 0,
            'orphaned': 0,
            'errors': 0,
        }
        
        try:
            # 1. FCMS 주문 데이터 조회
            self.stdout.write("1️⃣ FCMS 주문 데이터 조회 중...")
            fcms_orders = FcmsRepository.get_all_recent_orders(days=days, limit=limit)
            self.stdout.write(self.style.SUCCESS(f"   ✓ {len(fcms_orders)}건 조회"))
            
            # 2. 각 주문 처리
            self.stdout.write("\n2️⃣ PO 생성/매칭 처리 중...")
            for order in fcms_orders:
                stats['total_checked'] += 1
                
                try:
                    result = self._process_fcms_order(order, dry_run, force)
                    stats[result] += 1
                    
                    if result == 'created':
                        self.stdout.write(self.style.SUCCESS(
                            f"   [생성] {order['arrival_shipping_no']}"
                        ))
                    elif result == 'needs_review':
                        self.stdout.write(self.style.WARNING(
                            f"   [검토필요] {order['arrival_shipping_no']}"
                        ))
                    elif result == 'orphaned':
                        self.stdout.write(self.style.ERROR(
                            f"   [고아문서] {order['arrival_shipping_no']}"
                        ))
                    
                except Exception as e:
                    stats['errors'] += 1
                    self.stdout.write(self.style.ERROR(
                        f"   [오류] {order.get('arrival_shipping_no', 'N/A')}: {e}"
                    ))
                    logger.exception(f"주문 처리 실패: {order}")
            
            # 3. 결과 요약
            self.stdout.write("\n" + "="*60)
            self.stdout.write(self.style.SUCCESS("✅ 처리 완료"))
            self.stdout.write("")
            self.stdout.write(f"총 확인: {stats['total_checked']}건")
            self.stdout.write(self.style.SUCCESS(f"  ✓ 생성: {stats['created']}건"))
            self.stdout.write(f"  - 건너뜀: {stats['skipped']}건")
            self.stdout.write(self.style.WARNING(f"  ⚠ 검토필요: {stats['needs_review']}건"))
            self.stdout.write(self.style.ERROR(f"  ✗ 고아문서: {stats['orphaned']}건"))
            self.stdout.write(self.style.ERROR(f"  ✗ 오류: {stats['errors']}건"))
            
            if dry_run:
                self.stdout.write("\n" + self.style.WARNING("⚠️ Dry Run 모드: 실제 저장되지 않음"))
            
        except Exception as e:
            raise CommandError(f"역수입 실패: {e}")
    
    def _process_fcms_order(self, order: dict, dry_run: bool, force: bool) -> str:
        """
        개별 FCMS 주문 처리
        
        Returns:
            'created', 'skipped', 'needs_review', 'orphaned', 'errors'
        """
        arrival_shipping_no = order['arrival_shipping_no']
        
        # 이미 매칭된 문서인지 확인
        if not force and POFcmsMatch.objects.filter(
            arrival_shipping_no=arrival_shipping_no
        ).exists():
            return 'skipped'
        
        # PO 데이터 구성
        try:
            po_data = self._build_po_from_fcms_order(order)
        except ValueError as e:
            # 필수 데이터 누락 → 고아 문서
            if not dry_run:
                self._create_orphan_doc(order, str(e))
            return 'orphaned'
        
        # 정합성 검증
        needs_review = self._validate_po_data(po_data, order)
        
        # PO 생성
        if not dry_run:
            with transaction.atomic():
                po = self._create_po(po_data, needs_review)
                self._create_po_match(po, order)
        
        return 'needs_review' if needs_review else 'created'
    
    def _build_po_from_fcms_order(self, order: dict) -> dict:
        """
        FCMS 주문 데이터로부터 PO 데이터 구성
        
        Raises:
            ValueError: 필수 데이터 누락 시
        """
        arrival_shipping_no = order.get('arrival_shipping_no')
        if not arrival_shipping_no:
            raise ValueError("도착출하번호 없음")
        
        supplier_user_code = order.get('supplier_user_code', '')
        if not supplier_user_code:
            # 거래처 코드 없으면 UNKNOWN 처리
            supplier_user_code = 'UNKNOWN'
        
        # 고객 발주번호: FCMS에 없으면 arrival_shipping_no를 임시로 사용
        customer_order_no = order.get('customer_order_no') or f"FCMS-{arrival_shipping_no}"
        
        # PO 번호: 고유한 값 생성
        po_no = f"BACKFILL-{arrival_shipping_no}"
        
        return {
            'po_no': po_no,
            'supplier_user_code': supplier_user_code,
            'supplier_user_name': order.get('supplier_user_name', ''),
            'customer_order_no': customer_order_no,
            'received_at': order.get('order_date') or timezone.now(),
            'due_date': None,  # FCMS에 납기 정보가 있으면 추가
            'status': 'MATCHED',  # 이미 FCMS에 존재하므로 MATCHED
            'memo': 'FCMS 데이터로부터 자동 생성',
            'is_backfilled': True,
            'items': [
                {
                    'line_no': 1,
                    'trade_condition_code': order.get('trade_condition_code', 'UNKNOWN'),
                    'trade_condition_name': '',
                    'qty': order.get('total_qty', 0),
                }
            ]
        }
    
    def _validate_po_data(self, po_data: dict, order: dict) -> bool:
        """
        PO 데이터 정합성 검증
        
        Returns:
            검토 필요 여부 (True: 검토 필요)
        """
        needs_review = False
        
        # (A) 필수 키 누락
        if po_data['supplier_user_code'] == 'UNKNOWN':
            needs_review = True
        
        if po_data['customer_order_no'].startswith('FCMS-'):
            needs_review = True
        
        # (B) 수량 검증
        if po_data['items']:
            total_qty = sum(item['qty'] for item in po_data['items'])
            instruction_qty = order.get('total_qty', 0)
            
            if total_qty != instruction_qty:
                needs_review = True
        
        # (C) 날짜 검증
        if not po_data['received_at']:
            needs_review = True
        
        return needs_review
    
    def _create_po(self, po_data: dict, needs_review: bool) -> PO:
        """
        PO 및 POItem 생성
        """
        # PO 생성
        po = PO.objects.create(
            po_no=po_data['po_no'],
            supplier_user_code=po_data['supplier_user_code'],
            supplier_user_name=po_data['supplier_user_name'],
            customer_order_no=po_data['customer_order_no'],
            received_at=po_data['received_at'],
            due_date=po_data.get('due_date'),
            status=po_data['status'],
            memo=po_data['memo'],
            is_backfilled=True,
            needs_review=needs_review,
        )
        
        # POItem 생성
        for item_data in po_data.get('items', []):
            POItem.objects.create(
                po=po,
                line_no=item_data['line_no'],
                trade_condition_code=item_data['trade_condition_code'],
                trade_condition_name=item_data['trade_condition_name'],
                qty=item_data['qty'],
            )
        
        return po
    
    def _create_po_match(self, po: PO, order: dict):
        """
        POFcmsMatch 생성
        """
        POFcmsMatch.objects.create(
            po=po,
            arrival_shipping_no=order['arrival_shipping_no'],
            match_state='MATCHED',
            note='Backfill 자동 매칭'
        )
    
    def _create_orphan_doc(self, order: dict, reason: str):
        """
        고아 문서 등록
        """
        OrphanFcmsDoc.objects.get_or_create(
            doc_type='TR_ORDER',
            doc_no=order['arrival_shipping_no'],
            defaults={
                'doc_date': order.get('order_date'),
                'supplier_user_code': order.get('supplier_user_code', ''),
                'item_code': order.get('trade_condition_code', ''),
                'qty': order.get('total_qty'),
            }
        )

