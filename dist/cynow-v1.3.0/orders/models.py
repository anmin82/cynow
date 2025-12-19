"""
수주(PO) 관리 모델

FCMS와의 연계를 위한 수주 입력, 예약번호 관리, 매칭 검증 모델
기존 시스템에 영향을 주지 않도록 독립된 테이블로 설계
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class PO(models.Model):
    """
    수주(Purchase Order) 헤더
    
    FCMS에 실제 입력할 주문 정보를 CYNOW에서 먼저 입력하고 관리
    """
    
    STATUS_CHOICES = [
        ('DRAFT', '임시저장'),
        ('GUIDED', '번호가이드'),
        ('MATCHED', '매칭완료'),
        ('IN_PROGRESS', '진행중'),
        ('COMPLETED', '완료'),
        ('CANCELED', '취소'),
    ]
    
    # 기본 정보
    # ⚠️ PO 번호는 customer_order_no 하나만 존재
    customer_order_no = models.CharField(
        max_length=100,
        unique=True,  # ✅ 고객발주번호가 유일한 PO 식별자
        verbose_name='PO번호(고객발주번호)',
        help_text='고객이 발행한 발주서 번호'
    )
    
    supplier_user_code = models.CharField(
        max_length=50,
        verbose_name='고객코드',
        help_text='FCMS 거래처 코드'
    )
    
    supplier_user_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='고객명'
    )
    
    # 날짜 정보
    received_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='수주일시'
    )
    
    due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='납기일',
        help_text='단일 납기 (분할납품은 POSchedule 사용)'
    )
    
    # 상태
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name='상태'
    )
    
    # 메모
    memo = models.TextField(
        blank=True,
        verbose_name='메모'
    )
    
    # 관리 정보
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_pos',
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
    
    # Backfill 관련
    is_backfilled = models.BooleanField(
        default=False,
        verbose_name='역수입 데이터',
        help_text='FCMS 기존 데이터로부터 자동 생성된 경우 True'
    )
    
    needs_review = models.BooleanField(
        default=False,
        verbose_name='검토 필요',
        help_text='역수입 시 정합성 이슈가 있어 수동 검토가 필요한 경우'
    )
    
    review_note = models.TextField(
        blank=True,
        verbose_name='검토 메모'
    )
    
    class Meta:
        db_table = 'po_header'
        verbose_name = '수주'
        verbose_name_plural = '수주'
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['supplier_user_code', 'customer_order_no']),
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['is_backfilled', 'needs_review']),
        ]
    
    def __str__(self):
        return f"{self.customer_order_no} ({self.supplier_user_name})"
    
    @property
    def total_qty(self):
        """총 수주 수량"""
        return sum(item.qty for item in self.items.all())
    
    @property
    def total_amount(self):
        """총 수주 금액"""
        return sum(item.total_price or 0 for item in self.items.all())
    
    @property
    def days_until_due(self):
        """납기까지 남은 일수"""
        if not self.due_date:
            return None
        from datetime import date
        delta = self.due_date - date.today()
        return delta.days
    
    @property
    def is_split_delivery(self):
        """분할납품 여부"""
        return self.schedules.count() > 1


class POItem(models.Model):
    """
    수주 라인 (품목별)
    
    하나의 PO에 여러 품목이 포함될 수 있음
    """
    
    po = models.ForeignKey(
        PO,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='수주'
    )
    
    line_no = models.IntegerField(
        verbose_name='라인번호',
        help_text='수주 내 순서'
    )
    
    trade_condition_code = models.CharField(
        max_length=100,
        verbose_name='제품코드',
        help_text='FCMS 품목 코드 (ITEM_CODE 등)'
    )
    
    trade_condition_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='제품명'
    )
    
    qty = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='수량'
    )
    
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='단가'
    )
    
    remarks = models.TextField(
        blank=True,
        verbose_name='비고'
    )
    
    class Meta:
        db_table = 'po_item'
        verbose_name = '수주 라인'
        verbose_name_plural = '수주 라인'
        ordering = ['po', 'line_no']
        unique_together = [['po', 'line_no']]
        indexes = [
            models.Index(fields=['trade_condition_code']),
        ]
    
    def __str__(self):
        return f"{self.po.customer_order_no}-{self.line_no}: {self.trade_condition_name} x {self.qty}"
    
    @property
    def total_price(self):
        """품목별 총 금액"""
        if self.unit_price:
            return self.unit_price * self.qty
        return None


class POSchedule(models.Model):
    """
    분할납품 일정
    
    하나의 PO를 여러 회차로 나누어 납품하는 경우 사용
    """
    
    po = models.ForeignKey(
        PO,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='수주'
    )
    
    sequence = models.IntegerField(
        verbose_name='회차',
        help_text='1회, 2회, ...'
    )
    
    due_date = models.DateField(
        verbose_name='납기일'
    )
    
    qty = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='수량'
    )
    
    remarks = models.TextField(
        blank=True,
        verbose_name='비고'
    )
    
    class Meta:
        db_table = 'po_schedule'
        verbose_name = '분할납품 일정'
        verbose_name_plural = '분할납품 일정'
        ordering = ['po', 'sequence']
        unique_together = [['po', 'sequence']]
    
    def __str__(self):
        return f"{self.po.po_no} {self.sequence}회차 ({self.due_date})"


class ReservedDocNo(models.Model):
    """
    예약/추천 문서번호
    
    FCMS 입력 전에 CYNOW에서 번호를 예약하여 가이드
    실제 FCMS 입력 후 매칭 검증
    """
    
    STATUS_CHOICES = [
        ('RESERVED', '예약'),
        ('EXPIRED', '만료'),
        ('MATCHED', '매칭완료'),
        ('MISMATCH', '불일치'),
    ]
    
    DOC_TYPE_CHOICES = [
        ('ARRIVAL_SHIPPING', '도착출하번호'),
        ('MOVE_REPORT', '이동서번호'),
    ]
    
    po = models.ForeignKey(
        PO,
        on_delete=models.CASCADE,
        related_name='reserved_numbers',
        verbose_name='수주'
    )
    
    doc_type = models.CharField(
        max_length=20,
        choices=DOC_TYPE_CHOICES,
        verbose_name='문서 유형'
    )
    
    reserved_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='예약 번호',
        help_text='FP+YY+6자리 형식 (예: FP240001)'
    )
    
    reserved_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='예약 일시'
    )
    
    expires_at = models.DateTimeField(
        verbose_name='만료 일시',
        help_text='예약 후 48시간 등'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='RESERVED',
        verbose_name='상태'
    )
    
    # 매칭 정보
    matched_fcms_doc_key = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='매칭된 FCMS 문서 키',
        help_text='TR_ORDERS.id, TR_MOVE_REPORTS.id 등'
    )
    
    matched_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='매칭 일시'
    )
    
    class Meta:
        db_table = 'po_reserved_doc_no'
        verbose_name = '예약 문서번호'
        verbose_name_plural = '예약 문서번호'
        ordering = ['-reserved_at']
        indexes = [
            models.Index(fields=['reserved_no']),
            models.Index(fields=['po', 'status']),
            models.Index(fields=['status', 'expires_at']),
        ]
    
    def __str__(self):
        return f"{self.reserved_no} ({self.get_status_display()})"
    
    def is_expired(self):
        """만료 여부 확인"""
        return timezone.now() > self.expires_at and self.status == 'RESERVED'
    
    def check_expiration(self):
        """만료 확인 및 상태 업데이트"""
        if self.is_expired():
            self.status = 'EXPIRED'
            self.save(update_fields=['status'])


class POFcmsMatch(models.Model):
    """
    PO와 FCMS 실제 문서 간 매칭 결과
    
    예약번호가 FCMS에 정확히 입력되었는지, 오입력이 있는지 추적
    """
    
    MATCH_STATE_CHOICES = [
        ('MATCHED', '정확 매칭'),
        ('NOT_ENTERED', '미입력'),
        ('MISMATCH', '번호 불일치'),
        ('PARTIAL', '부분 매칭'),
    ]
    
    po = models.ForeignKey(
        PO,
        on_delete=models.CASCADE,
        related_name='fcms_matches',
        verbose_name='수주'
    )
    
    reserved_doc = models.ForeignKey(
        ReservedDocNo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='matches',
        verbose_name='예약 문서'
    )
    
    # FCMS 실제 문서 정보
    arrival_shipping_no = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='실제 도착출하번호',
        help_text='FCMS TR_ORDERS.ARRIVAL_SHIPPING_NO'
    )
    
    move_report_no = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='실제 이동서번호',
        help_text='FCMS TR_MOVE_REPORTS.MOVE_REPORT_NO'
    )
    
    # 매칭 결과
    match_state = models.CharField(
        max_length=20,
        choices=MATCH_STATE_CHOICES,
        default='NOT_ENTERED',
        verbose_name='매칭 상태'
    )
    
    matched_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='매칭 확인 일시'
    )
    
    last_checked_at = models.DateTimeField(
        auto_now=True,
        verbose_name='최종 확인 일시'
    )
    
    note = models.TextField(
        blank=True,
        verbose_name='메모',
        help_text='불일치 사유, 수동 매칭 근거 등'
    )
    
    # 수동 매칭
    is_manual_match = models.BooleanField(
        default=False,
        verbose_name='수동 매칭',
        help_text='자동 매칭 실패 시 관리자가 수동으로 연결'
    )
    
    manual_matched_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='수동 매칭 담당자'
    )
    
    class Meta:
        db_table = 'po_fcms_match'
        verbose_name = 'PO-FCMS 매칭'
        verbose_name_plural = 'PO-FCMS 매칭'
        ordering = ['-matched_at']
        indexes = [
            models.Index(fields=['po', 'match_state']),
            models.Index(fields=['arrival_shipping_no']),
            models.Index(fields=['move_report_no']),
        ]
    
    def __str__(self):
        return f"{self.po.po_no} - {self.get_match_state_display()}"


class OrphanFcmsDoc(models.Model):
    """
    고아 FCMS 문서 (PO 매칭 불가)
    
    FCMS에는 존재하지만 CYNOW PO와 연결되지 않는 문서들
    역수입(backfill) 시 매칭 실패한 케이스
    """
    
    doc_type = models.CharField(
        max_length=20,
        choices=[
            ('TR_ORDER', '주문'),
            ('TR_MOVE_REPORT', '이동서'),
        ],
        verbose_name='문서 유형'
    )
    
    doc_no = models.CharField(
        max_length=50,
        verbose_name='문서 번호',
        help_text='ARRIVAL_SHIPPING_NO 또는 MOVE_REPORT_NO'
    )
    
    doc_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='문서 일자'
    )
    
    supplier_user_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='거래처 코드'
    )
    
    item_code = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='품목 코드'
    )
    
    qty = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='수량'
    )
    
    # 매칭 시도
    suggested_po = models.ForeignKey(
        PO,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orphan_suggestions',
        verbose_name='추정 PO'
    )
    
    is_resolved = models.BooleanField(
        default=False,
        verbose_name='해결 완료'
    )
    
    resolved_note = models.TextField(
        blank=True,
        verbose_name='해결 메모'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='발견 일시'
    )
    
    class Meta:
        db_table = 'po_orphan_fcms_doc'
        verbose_name = '고아 FCMS 문서'
        verbose_name_plural = '고아 FCMS 문서'
        ordering = ['-created_at']
        unique_together = [['doc_type', 'doc_no']]
        indexes = [
            models.Index(fields=['doc_type', 'doc_no']),
            models.Index(fields=['is_resolved']),
        ]
    
    def __str__(self):
        return f"[고아] {self.doc_type}: {self.doc_no}"


class POProgressSnapshot(models.Model):
    """
    PO 진행 현황 스냅샷 (집계 캐시)
    
    무거운 집계 쿼리를 매번 실행하지 않고 주기적으로 갱신된 결과 저장
    """
    
    po = models.ForeignKey(
        PO,
        on_delete=models.CASCADE,
        related_name='progress_snapshots',
        verbose_name='수주'
    )
    
    snapshot_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='스냅샷 일시'
    )
    
    # 수량 집계
    order_qty = models.IntegerField(
        default=0,
        verbose_name='수주 수량'
    )
    
    instruction_qty = models.IntegerField(
        default=0,
        verbose_name='충전 지시 수량',
        help_text='TR_ORDERS_INFORMATIONS.INSTRUCTION_COUNT 합계'
    )
    
    filling_qty = models.IntegerField(
        default=0,
        verbose_name='충전 진행 수량',
        help_text='TR_MOVE_REPORT_DETAILS 실린더 수'
    )
    
    warehouse_in_qty = models.IntegerField(
        default=0,
        verbose_name='창고 입고 수량'
    )
    
    shipping_qty = models.IntegerField(
        default=0,
        verbose_name='출하 완료 수량'
    )
    
    # 진행률
    progress_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='진행률 (%)'
    )
    
    class Meta:
        db_table = 'po_progress_snapshot'
        verbose_name = 'PO 진행 현황'
        verbose_name_plural = 'PO 진행 현황'
        ordering = ['-snapshot_at']
        indexes = [
            models.Index(fields=['po', '-snapshot_at']),
        ]
    
    def __str__(self):
        return f"{self.po.po_no} 진행률: {self.progress_rate}%"

