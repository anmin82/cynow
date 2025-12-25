"""
제품코드 관리 모델

제품코드 = 가스 + 용기스펙 + 밸브스펙 조합
예: KF013 = COS / 25kg / CGA330
    KF015 = COS / 25kg / CGA722

FCMS CDC 테이블:
- MA_SELECTION_PATTERNS: 제품코드 마스터
- MA_SELECTION_PATTERN_DETAILS: 용기/밸브 스펙 상세

CYNOW 추가 데이터:
- 단가 (kg당)
- 단가 이력
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class ProductCode(models.Model):
    """
    제품코드 마스터
    
    FCMS CDC (MA_SELECTION_PATTERNS)에서 동기화 + CYNOW 추가 정보
    """
    # FCMS CDC 필드
    selection_pattern_code = models.CharField(
        max_length=50, 
        primary_key=True,
        verbose_name='Selection Pattern Code',
        help_text='FCMS PK (MA_SELECTION_PATTERNS.SELECTION_PATTERN_CODE)'
    )
    trade_condition_no = models.CharField(
        max_length=50, 
        db_index=True,
        verbose_name='제품코드',
        help_text='TRADE_CONDITION_NO (예: KF001, KF013)'
    )
    primary_store_user_code = models.CharField(
        max_length=50, 
        default='KDKK',
        verbose_name='고객코드',
        help_text='PRIMARY_STORE_USER_CODE (우리 고객, 현재 KDKK만)'
    )
    customer_user_code = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name='엔드유저코드',
        help_text='CUSTOMER_USER_CODE'
    )
    customer_user_name = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        verbose_name='엔드유저명'
    )
    
    # FCMS CDC (MA_SELECTION_PATTERN_DETAILS)에서 가져올 정보
    cylinder_spec_code = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name='용기스펙코드'
    )
    valve_spec_code = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name='밸브스펙코드'
    )
    
    # 조인해서 가져올 표시용 정보
    gas_name = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name='가스명'
    )
    capacity = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name='용량 (L 또는 kg)'
    )
    cylinder_spec_name = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        verbose_name='용기스펙명'
    )
    valve_spec_name = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        verbose_name='밸브스펙명'
    )
    filling_weight = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name='충전량 (kg)'
    )
    
    # CYNOW 용기종류 매핑
    cylinder_type_key = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        db_index=True,
        verbose_name='용기종류키',
        help_text='CYNOW 대시보드 용기종류 그룹 키'
    )
    
    # CYNOW 추가 정보
    display_name = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        verbose_name='표시명',
        help_text='사용자 친화적 이름 (예: COS 25kg CGA330)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성화',
        help_text='비활성화된 제품코드는 목록에서 숨김'
    )
    
    # 통화 설정
    CURRENCY_CHOICES = [
        ('KRW', '원 (₩)'),
        ('JPY', '엔 (¥)'),
        ('CNY', '위안 (¥)'),
    ]
    default_currency = models.CharField(
        max_length=10,
        choices=CURRENCY_CHOICES,
        default='KRW',
        verbose_name='기본 통화',
        help_text='이 제품코드의 거래 통화'
    )
    
    note = models.TextField(
        blank=True, 
        null=True,
        verbose_name='메모'
    )
    
    # 메타
    fcms_synced_at = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name='FCMS 동기화 시각'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_code'
        ordering = ['trade_condition_no']
        verbose_name = '제품코드'
        verbose_name_plural = '제품코드'
        indexes = [
            models.Index(fields=['trade_condition_no']),
            models.Index(fields=['primary_store_user_code']),
            models.Index(fields=['cylinder_type_key']),
        ]
    
    def __str__(self):
        return f"{self.trade_condition_no} - {self.display_name or self.gas_name or ''}"
    
    def get_current_price(self):
        """현재 적용 중인 단가 조회"""
        from django.utils import timezone
        today = timezone.now().date()
        price = self.price_history.filter(
            effective_date__lte=today
        ).order_by('-effective_date').first()
        return price
    
    @property
    def current_price_per_kg(self):
        """현재 kg당 단가"""
        price = self.get_current_price()
        return price.price_per_kg if price else None


class ProductPriceHistory(models.Model):
    """
    제품코드별 단가 이력
    
    해마다 단가하락이 발생하므로 이력 관리 필요
    """
    product_code = models.ForeignKey(
        ProductCode, 
        on_delete=models.CASCADE,
        related_name='price_history',
        verbose_name='제품코드'
    )
    effective_date = models.DateField(
        verbose_name='적용 시작일',
        help_text='이 날짜부터 이 단가가 적용됨'
    )
    price_per_kg = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='kg당 단가',
        help_text='원/kg'
    )
    CURRENCY_CHOICES = [
        ('KRW', '원 (₩)'),
        ('JPY', '엔 (¥)'),
        ('CNY', '위안 (¥)'),
    ]
    currency = models.CharField(
        max_length=10, 
        choices=CURRENCY_CHOICES,
        default='KRW',
        verbose_name='통화'
    )
    note = models.TextField(
        blank=True, 
        null=True,
        verbose_name='메모',
        help_text='예: 2025년 연간 계약 단가'
    )
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name='등록자'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_price_history'
        ordering = ['-effective_date']
        verbose_name = '단가 이력'
        verbose_name_plural = '단가 이력'
        unique_together = [['product_code', 'effective_date']]
        indexes = [
            models.Index(fields=['product_code', 'effective_date']),
        ]
    
    def __str__(self):
        return f"{self.product_code.trade_condition_no} - {self.effective_date} - {self.price_per_kg}원/kg"


class ProductCodeSync(models.Model):
    """
    FCMS CDC → CYNOW 동기화 로그
    """
    sync_type = models.CharField(
        max_length=20,
        choices=[
            ('FULL', '전체 동기화'),
            ('INCREMENTAL', '증분 동기화'),
        ],
        verbose_name='동기화 유형'
    )
    started_at = models.DateTimeField(verbose_name='시작 시각')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='완료 시각')
    records_processed = models.IntegerField(default=0, verbose_name='처리 건수')
    records_created = models.IntegerField(default=0, verbose_name='생성 건수')
    records_updated = models.IntegerField(default=0, verbose_name='수정 건수')
    status = models.CharField(
        max_length=20,
        choices=[
            ('RUNNING', '진행중'),
            ('SUCCESS', '성공'),
            ('FAILED', '실패'),
        ],
        default='RUNNING',
        verbose_name='상태'
    )
    error_message = models.TextField(blank=True, null=True, verbose_name='오류 메시지')
    
    class Meta:
        db_table = 'product_code_sync_log'
        ordering = ['-started_at']
        verbose_name = '동기화 로그'
        verbose_name_plural = '동기화 로그'
