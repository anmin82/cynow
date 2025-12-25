"""
전표/견적서 모델

견적서(Quote)와 견적 품목(QuoteItem)을 관리합니다.
DOCX 생성 시 이 모델의 데이터를 사용합니다.
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import date


class Customer(models.Model):
    """
    거래처 마스터
    """
    code = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name='거래처코드'
    )
    name = models.CharField(
        max_length=200,
        verbose_name='거래처명'
    )
    name_en = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='영문명'
    )
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name='주소'
    )
    ceo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='대표자'
    )
    tel = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='전화번호'
    )
    fax = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='팩스번호'
    )
    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name='이메일'
    )
    manager_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='담당자명'
    )
    manager_tel = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='담당자 연락처'
    )
    manager_email = models.EmailField(
        blank=True,
        null=True,
        verbose_name='담당자 이메일'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성화'
    )
    note = models.TextField(
        blank=True,
        null=True,
        verbose_name='비고'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'voucher_customer'
        ordering = ['code']
        verbose_name = '거래처'
        verbose_name_plural = '거래처'
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class Quote(models.Model):
    """
    견적서
    """
    STATUS_CHOICES = [
        ('DRAFT', '작성중'),
        ('SENT', '발송완료'),
        ('ACCEPTED', '수락'),
        ('REJECTED', '거절'),
        ('EXPIRED', '만료'),
    ]
    
    CURRENCY_CHOICES = [
        ('KRW', '원 (₩)'),
        ('JPY', '엔 (¥)'),
        ('USD', '달러 ($)'),
        ('CNY', '위안 (¥)'),
    ]
    
    # 견적 기본 정보
    quote_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='견적번호',
        help_text='예: QT-2026-0001'
    )
    title = models.CharField(
        max_length=200,
        verbose_name='견적건명'
    )
    quote_date = models.DateField(
        default=date.today,
        verbose_name='견적일자'
    )
    valid_until = models.DateField(
        blank=True,
        null=True,
        verbose_name='유효기간'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name='상태'
    )
    
    # 거래처 정보
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quotes',
        verbose_name='거래처'
    )
    # 견적서에 직접 입력할 수 있는 수신처 정보
    customer_address = models.TextField(blank=True, null=True, verbose_name='수신처 주소')
    customer_ceo = models.CharField(max_length=100, blank=True, null=True, verbose_name='수신처 대표자')
    customer_tel = models.CharField(max_length=50, blank=True, null=True, verbose_name='수신처 연락처')
    customer_manager = models.CharField(max_length=100, blank=True, null=True, verbose_name='수신처 담당자')
    customer_manager_tel = models.CharField(max_length=50, blank=True, null=True, verbose_name='수신처 담당자 연락처')
    customer_manager_email = models.EmailField(blank=True, null=True, verbose_name='수신처 담당자 이메일')
    
    # 공급처 정보 (발행사 정보)
    supplier_name = models.CharField(max_length=200, blank=True, null=True, verbose_name='공급처명')
    supplier_address = models.TextField(blank=True, null=True, verbose_name='공급처 주소')
    supplier_ceo = models.CharField(max_length=100, blank=True, null=True, verbose_name='공급처 대표자')
    supplier_tel = models.CharField(max_length=50, blank=True, null=True, verbose_name='공급처 TEL')
    supplier_fax = models.CharField(max_length=50, blank=True, null=True, verbose_name='공급처 FAX')
    supplier_manager = models.CharField(max_length=100, blank=True, null=True, verbose_name='공급처 담당자')
    supplier_manager_tel = models.CharField(max_length=50, blank=True, null=True, verbose_name='공급처 담당자 연락처')
    supplier_manager_email = models.EmailField(blank=True, null=True, verbose_name='공급처 담당자 이메일')
    
    # 하단 공통 문구
    valid_period = models.CharField(max_length=200, blank=True, null=True, verbose_name='적용기간')
    trade_terms = models.TextField(blank=True, null=True, verbose_name='거래조건')
    bank_account = models.TextField(blank=True, null=True, verbose_name='결제계좌')
    
    # 통화
    default_currency = models.CharField(
        max_length=10,
        choices=CURRENCY_CHOICES,
        default='KRW',
        verbose_name='기본 통화'
    )
    
    # 금액 합계
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name='총 금액'
    )
    
    # 메타
    note = models.TextField(blank=True, null=True, verbose_name='비고')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_quotes',
        verbose_name='작성자'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'voucher_quote'
        ordering = ['-quote_date', '-created_at']
        verbose_name = '견적서'
        verbose_name_plural = '견적서'
    
    def __str__(self):
        return f"{self.quote_no} - {self.title}"
    
    def calculate_total(self):
        """품목 합계 계산"""
        total = sum(
            item.packing_price or Decimal('0') 
            for item in self.items.all()
        )
        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total
    
    def generate_quote_no(self):
        """견적번호 자동 생성"""
        from django.utils import timezone
        year = timezone.now().year
        prefix = f"QT-{year}-"
        
        last_quote = Quote.objects.filter(
            quote_no__startswith=prefix
        ).order_by('-quote_no').first()
        
        if last_quote:
            try:
                last_num = int(last_quote.quote_no.split('-')[-1])
                new_num = last_num + 1
            except ValueError:
                new_num = 1
        else:
            new_num = 1
        
        return f"{prefix}{new_num:04d}"


class QuoteItem(models.Model):
    """
    견적 품목
    """
    quote = models.ForeignKey(
        Quote,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='견적서'
    )
    product_code = models.ForeignKey(
        'products.ProductCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='제품코드'
    )
    
    # 품목 상세
    seq = models.PositiveIntegerField(
        default=1,
        verbose_name='순번'
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='구분'
    )
    gas_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='가스명',
        help_text='제품코드에서 자동 입력 또는 직접 입력'
    )
    product_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='품명'
    )
    material_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='자재코드'
    )
    end_user = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='End User'
    )
    packing = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='포장',
        help_text='예: 47L, Y-1'
    )
    filling_weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='충전중량 (kg)'
    )
    
    # 단가 정보
    CURRENCY_CHOICES = Quote.CURRENCY_CHOICES
    currency = models.CharField(
        max_length=10,
        choices=CURRENCY_CHOICES,
        default='KRW',
        verbose_name='통화'
    )
    price_per_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        blank=True,
        null=True,
        verbose_name='단가 (1kg)'
    )
    packing_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        blank=True,
        null=True,
        verbose_name='포장단가'
    )
    
    note = models.TextField(blank=True, null=True, verbose_name='비고')
    
    class Meta:
        db_table = 'voucher_quote_item'
        ordering = ['seq']
        verbose_name = '견적 품목'
        verbose_name_plural = '견적 품목'
    
    def __str__(self):
        return f"{self.quote.quote_no} - {self.seq}. {self.gas_name or self.product_name}"
    
    def save(self, *args, **kwargs):
        """제품코드가 있으면 자동 입력"""
        if self.product_code:
            pc = self.product_code
            if not self.gas_name:
                self.gas_name = pc.gas_name
            if not self.material_code:
                self.material_code = pc.trade_condition_no
            if not self.end_user:
                self.end_user = pc.customer_user_name
            if not self.filling_weight and pc.filling_weight:
                self.filling_weight = pc.filling_weight
            if not self.product_name:
                self.product_name = pc.display_name
        
        super().save(*args, **kwargs)


class DocumentTemplate(models.Model):
    """
    문서 템플릿 관리
    
    DOCX 템플릿 파일을 관리하고, 유형별로 분류합니다.
    """
    TEMPLATE_TYPE_CHOICES = [
        ('QUOTE', '견적서'),
        ('INVOICE', '청구서'),
        ('DELIVERY', '납품서'),
        ('PRICE_LIST', '단가표'),
        ('CONTRACT', '계약서'),
    ]
    
    name = models.CharField(
        max_length=100,
        verbose_name='템플릿명'
    )
    template_type = models.CharField(
        max_length=20,
        choices=TEMPLATE_TYPE_CHOICES,
        verbose_name='템플릿 유형'
    )
    filename = models.CharField(
        max_length=200,
        verbose_name='파일명',
        help_text='docx_templates/ 폴더 내 파일명'
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='설명'
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name='기본 템플릿',
        help_text='해당 유형의 기본 템플릿으로 사용'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성화'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'voucher_document_template'
        ordering = ['template_type', 'name']
        verbose_name = '문서 템플릿'
        verbose_name_plural = '문서 템플릿'
    
    def __str__(self):
        return f"[{self.get_template_type_display()}] {self.name}"
    
    @classmethod
    def get_default_template(cls, template_type: str) -> 'DocumentTemplate':
        """유형별 기본 템플릿 조회"""
        return cls.objects.filter(
            template_type=template_type,
            is_default=True,
            is_active=True
        ).first()

