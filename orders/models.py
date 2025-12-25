"""
수주 페이지 전용 모델

목적:
A) 고객 이메일로 받은 수주 정보를 정확히 기록
B) FCMS 수기 입력을 돕기 위해 "이동서번호 가이드(추천값)" 제공
C) 수주가 현재 어느 단계인지 모니터링

⚠️ 중요:
- PO 번호는 customer_order_no 단 하나
- 내부 PO 번호 없음
- 시스템 생성 PO 번호 없음
- FCMS 데이터 역수입(backfill) 없음
- ERP 기능 없음
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class PO(models.Model):
    """
    수주 (Purchase Order)
    
    고객으로부터 받은 수주 정보 관리
    """
    
    STATUS_CHOICES = [
        ('DRAFT', '임시저장'),
        ('GUIDED', '번호가이드생성'),
        ('MATCHED', 'FCMS매칭완료'),
        ('IN_PROGRESS', '진행중'),
        ('COMPLETED', '완료'),
    ]
    
    DELIVERY_TYPE_CHOICES = [
        ('PARTIAL', '분납 (익월말까지)'),
        ('FIXED', '지정일'),
    ]
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ⚠️ PO 번호는 customer_order_no 단 하나
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    customer_order_no = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='PO번호(고객발주번호)',
        help_text='유일한 PO 식별자 - 고객이 발행한 발주서 번호'
    )
    
    # 고객 정보 (CompanyInfo 연동)
    customer = models.ForeignKey(
        'voucher.CompanyInfo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='고객사',
        help_text='고객사 선택 (CompanyInfo)'
    )
    
    # 텍스트 백업 (고객 선택 안 할 경우 또는 직접 입력)
    supplier_user_code = models.CharField(
        max_length=50,
        verbose_name='고객코드',
        help_text='FCMS 거래처 코드',
        blank=True
    )
    
    supplier_user_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='고객명'
    )
    
    received_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='수주일시'
    )
    
    # 납기 정보
    delivery_type = models.CharField(
        max_length=20,
        choices=DELIVERY_TYPE_CHOICES,
        default='PARTIAL',
        verbose_name='납기유형',
        help_text='분납: 익월말까지 / 지정일: 특정일 지정'
    )
    
    delivery_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='납기일',
        help_text='지정일 납기일 때만 입력'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name='상태'
    )
    
    memo = models.TextField(
        blank=True,
        verbose_name='메모'
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='pos_created',
        verbose_name='작성자'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )
    
    class Meta:
        db_table = 'po_simple'
        verbose_name = '수주'
        verbose_name_plural = '수주'
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['customer_order_no']),
            models.Index(fields=['status']),
            models.Index(fields=['supplier_user_code']),
        ]
    
    def __str__(self):
        return f"{self.customer_order_no}"
    
    def sync_from_customer(self):
        """고객 정보(CompanyInfo)에서 코드/이름 동기화"""
        if self.customer:
            self.supplier_user_code = self.customer.code
            self.supplier_user_name = self.customer.name
    
    @property
    def delivery_display(self):
        """납기 표시용 문자열"""
        if self.delivery_type == 'PARTIAL':
            return '분납 (익월말)'
        elif self.delivery_type == 'FIXED' and self.delivery_date:
            return f'{self.delivery_date.strftime("%Y-%m-%d")} 까지'
        return '-'
    
    @property
    def total_qty(self):
        """총 수주 수량"""
        return sum(item.qty for item in self.items.all())
    
    @property
    def total_weight(self):
        """총 중량(kg)"""
        total = Decimal('0')
        for item in self.items.all():
            if item.total_weight:
                total += item.total_weight
        return total if total > 0 else None
    
    @property
    def total_amount(self):
        """총 금액 (통화별 딕셔너리)"""
        amounts = {}
        for item in self.items.all():
            if item.amount:
                currency = item.currency
                if currency not in amounts:
                    amounts[currency] = Decimal('0')
                amounts[currency] += item.amount
        return amounts if amounts else None
    
    @property
    def total_amount_display(self):
        """총 금액 표시용 문자열"""
        amounts = self.total_amount
        if not amounts:
            return None
        currency_symbols = {'KRW': '₩', 'JPY': '¥', 'USD': '$', 'CNY': '¥'}
        parts = []
        for currency, amount in amounts.items():
            symbol = currency_symbols.get(currency, '')
            parts.append(f"{symbol}{amount:,.0f} {currency}")
        return ' / '.join(parts)


class POItem(models.Model):
    """
    수주 품목
    
    하나의 PO에 여러 품목이 포함될 수 있음
    ProductCode와 연동하여 단가, 스펙 정보 자동 로딩
    """
    
    CURRENCY_CHOICES = [
        ('KRW', '원 (₩)'),
        ('JPY', '엔 (¥)'),
        ('USD', '달러 ($)'),
        ('CNY', '위안 (¥)'),
    ]
    
    po = models.ForeignKey(
        PO,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='수주'
    )
    
    line_no = models.IntegerField(
        verbose_name='라인번호'
    )
    
    # ProductCode 연동 (개선)
    product_code = models.ForeignKey(
        'products.ProductCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='po_items',
        verbose_name='제품코드 참조',
        help_text='ProductCode 테이블 FK'
    )
    
    # 텍스트 백업 (ProductCode가 없거나 삭제될 경우 대비)
    trade_condition_code = models.CharField(
        max_length=100,
        verbose_name='제품코드',
        help_text='FCMS 품목 코드 (예: KF001)'
    )
    
    trade_condition_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='제품명'
    )
    
    # 스펙 정보 (ProductCode에서 가져옴, 스냅샷 저장)
    gas_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='가스명'
    )
    
    cylinder_spec = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='용기스펙'
    )
    
    valve_spec = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='밸브스펙'
    )
    
    filling_weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='충전량(kg)'
    )
    
    # 수량
    qty = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='수주수량'
    )
    
    # 단가 정보 (개선)
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='단가(/kg)',
        help_text='kg당 단가'
    )
    
    currency = models.CharField(
        max_length=10,
        choices=CURRENCY_CHOICES,
        default='KRW',
        verbose_name='통화'
    )
    
    remarks = models.TextField(
        blank=True,
        verbose_name='비고'
    )
    
    class Meta:
        db_table = 'po_item_simple'
        verbose_name = '수주품목'
        verbose_name_plural = '수주품목'
        ordering = ['po', 'line_no']
        unique_together = [['po', 'line_no']]
        indexes = [
            models.Index(fields=['trade_condition_code']),
        ]
    
    def __str__(self):
        return f"{self.po.customer_order_no}-{self.line_no}"
    
    @property
    def packing_price(self):
        """용기 단가 = 단가(/kg) × 충전량(kg)"""
        if self.unit_price and self.filling_weight:
            return self.unit_price * self.filling_weight
        return None
    
    @property
    def amount(self):
        """금액 = 용기단가 × 수량"""
        packing = self.packing_price
        if packing:
            return packing * self.qty
        return None
    
    @property
    def total_weight(self):
        """총 중량 = 충전량 × 수량"""
        if self.filling_weight:
            return self.filling_weight * self.qty
        return None
    
    def sync_from_product_code(self):
        """ProductCode에서 스펙/단가 정보 동기화"""
        if self.product_code:
            pc = self.product_code
            self.trade_condition_code = pc.trade_condition_no
            self.trade_condition_name = pc.display_name or pc.gas_name or ''
            self.gas_name = pc.gas_name or ''
            self.cylinder_spec = pc.cylinder_spec_name or ''
            self.valve_spec = pc.valve_spec_name or ''
            self.filling_weight = pc.filling_weight
            self.currency = pc.default_currency
            
            # 현재 단가 가져오기
            current_price = pc.get_current_price()
            if current_price:
                self.unit_price = current_price.price_per_kg


class MoveNoGuide(models.Model):
    """
    이동서번호 가이드 (예약 아님, 추천값만 제공)
    
    ⚠️ 중요:
    - CYNOW는 번호를 발급하지 않음
    - FCMS 최신 번호 기준 +1 계산하여 참고용으로만 표시
    - 실제 기준은 FCMS에 생성된 문서
    """
    
    STATE_CHOICES = [
        ('SHOWN', '표시됨'),
        ('MATCHED', 'FCMS매칭'),
        ('IGNORED', '사용안함'),
    ]
    
    po = models.ForeignKey(
        PO,
        on_delete=models.CASCADE,
        related_name='move_guides',
        verbose_name='수주'
    )
    
    suggested_move_no = models.CharField(
        max_length=50,
        verbose_name='추천이동서번호',
        help_text='FP+YY+6자리 (예: FP250001) - 참고용'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )
    
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default='SHOWN',
        verbose_name='상태'
    )
    
    # FCMS 실제 입력 확인
    fcms_actual_move_no = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='FCMS실제번호',
        help_text='TR_MOVE_REPORTS.MOVE_REPORT_NO'
    )
    
    fcms_matched_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='FCMS매칭일시'
    )
    
    class Meta:
        db_table = 'move_no_guide'
        verbose_name = '이동서번호가이드'
        verbose_name_plural = '이동서번호가이드'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['po', 'state']),
            models.Index(fields=['suggested_move_no']),
        ]
    
    def __str__(self):
        return f"{self.po.customer_order_no}: {self.suggested_move_no}"


class FCMSMatchStatus(models.Model):
    """
    FCMS 매칭 검증 상태
    
    CDC로 확인한 FCMS 실제 데이터와 수주 비교
    """
    
    MATCH_STATE_CHOICES = [
        ('MATCHED', 'FCMS매칭완료'),
        ('NOT_ENTERED', '미입력'),
        ('MISMATCH', '번호불일치'),
    ]
    
    po = models.OneToOneField(
        PO,
        on_delete=models.CASCADE,
        related_name='fcms_match_status',
        verbose_name='수주'
    )
    
    # FCMS 실제 문서 정보
    fcms_arrival_shipping_no = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='FCMS도착출하번호',
        help_text='TR_ORDERS.ARRIVAL_SHIPPING_NO'
    )
    
    fcms_move_report_no = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='FCMS이동서번호',
        help_text='TR_MOVE_REPORTS.MOVE_REPORT_NO'
    )
    
    match_state = models.CharField(
        max_length=20,
        choices=MATCH_STATE_CHOICES,
        default='NOT_ENTERED',
        verbose_name='매칭상태'
    )
    
    last_checked_at = models.DateTimeField(
        auto_now=True,
        verbose_name='최종확인일시'
    )
    
    note = models.TextField(
        blank=True,
        verbose_name='메모'
    )
    
    class Meta:
        db_table = 'fcms_match_status'
        verbose_name = 'FCMS매칭상태'
        verbose_name_plural = 'FCMS매칭상태'
    
    def __str__(self):
        return f"{self.po.customer_order_no}: {self.get_match_state_display()}"


