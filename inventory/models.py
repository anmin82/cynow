"""
재고 관리 모델

CYNOW 재고 관리 시스템:
1. 용기 재고 (CylinderInventory) - 물리적 용기 개수 관리
2. 제품 재고 (ProductInventory) - 가스/제품 중량 관리
3. 재고 트랜잭션 (InventoryTransaction) - 모든 입출고 기록
4. 일간 스냅샷 (DailySnapshot) - 마감 시점 재고 현황 저장

스냅샷 전략:
- 실시간 트랜잭션 기록 + 일간 마감 스냅샷
- 마감 시간 설정 가능 (기본: 18:00)
- 자동 스냅샷 생성 (cron/celery)
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


# ============================================
# 1. 재고 설정
# ============================================
class InventorySettings(models.Model):
    """
    재고 관리 설정
    
    마감 시간, 알림 임계값 등 전역 설정
    """
    
    # 마감 시간 (HH:MM 형식으로 저장)
    cutoff_hour = models.IntegerField(
        default=0,
        verbose_name='마감 시간 (시)',
        help_text='일간 스냅샷 기준 시간 (0-23), 0 = 자정'
    )
    cutoff_minute = models.IntegerField(
        default=0,
        verbose_name='마감 시간 (분)',
        help_text='일간 스냅샷 기준 분 (0-59)'
    )
    
    # 저재고 알림 임계값
    low_stock_threshold_cylinder = models.IntegerField(
        default=5,
        verbose_name='용기 저재고 임계값',
        help_text='용기 종류별 최소 재고 수량'
    )
    low_stock_threshold_product_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('100.00'),
        verbose_name='제품 저재고 임계값 (kg)',
        help_text='제품별 최소 재고량'
    )
    
    # 활성화 여부
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성화'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_settings'
        verbose_name = '재고 설정'
        verbose_name_plural = '재고 설정'
    
    def __str__(self):
        return f"재고 설정 (마감: {self.cutoff_hour:02d}:{self.cutoff_minute:02d})"
    
    @classmethod
    def get_active(cls):
        """활성화된 설정 가져오기 (없으면 생성)"""
        settings, _ = cls.objects.get_or_create(
            is_active=True,
            defaults={
                'cutoff_hour': 0,
                'cutoff_minute': 0
            }
        )
        return settings


# ============================================
# 2. 재고 트랜잭션 (원장)
# ============================================
class InventoryTransaction(models.Model):
    """
    재고 트랜잭션 (원장)
    
    모든 재고 이동을 기록하는 불변 원장
    - 입고: 용기 반입, 가스 원료 입고
    - 출고: 출하, 반출
    - 충전: 가스 소비, 용기 상태 변경
    - 조정: 실사 조정, 오류 정정
    """
    
    # 트랜잭션 유형
    TXN_TYPE_CHOICES = [
        # 용기 관련 (물리적 용기 추적)
        ('CYL_IN', '용기 입고'),           # 빈 용기 반입, 신규 용기
        ('CYL_OUT', '용기 출고'),          # 충전 용기 출하 (물리적)
        ('CYL_RETURN', '용기 회수'),       # 고객으로부터 빈 용기 회수
        ('CYL_FILL', '용기 충전'),         # 빈 용기 → 충전 용기
        ('CYL_TRANSFER', '용기 이동'),     # 위치/상태 변경
        ('CYL_ADJ', '용기 조정'),          # 실사 조정
        
        # 제품 관련 (제품코드별 창고 재고)
        ('PROD_IN', '제품 입고'),          # 충전 완료 용기 창고 입고
        ('PROD_OUT', '제품 출하'),         # 고객 출하
        ('PROD_ADJ', '제품 조정'),         # 실사 조정
        
        # 기타
        ('SNAPSHOT', '스냅샷'),            # 일간 스냅샷 생성 마커
    ]
    
    # 기본 정보
    txn_no = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='트랜잭션번호',
        help_text='자동 생성: INV-YYYYMMDD-NNNN'
    )
    
    txn_type = models.CharField(
        max_length=20,
        choices=TXN_TYPE_CHOICES,
        verbose_name='트랜잭션 유형'
    )
    
    txn_date = models.DateField(
        default=timezone.localdate,
        db_index=True,
        verbose_name='거래일',
        help_text='재고 반영 기준일'
    )
    
    txn_datetime = models.DateTimeField(
        default=timezone.now,
        verbose_name='거래일시',
        help_text='정확한 거래 시점'
    )
    
    # 용기 정보 (용기 관련 트랜잭션)
    cylinder_no = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        verbose_name='용기번호'
    )
    
    cylinder_type_key = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        verbose_name='용기종류키',
        help_text='cy_cylinder_current.dashboard_cylinder_type_key'
    )
    
    # 제품/가스 정보
    product_code = models.ForeignKey(
        'products.ProductCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_transactions',
        verbose_name='제품코드'
    )
    
    gas_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='가스명'
    )
    
    # 수량 (용기: 개수, 가스: kg)
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        verbose_name='수량',
        help_text='용기: 개수, 가스: kg'
    )
    
    # 수량 부호 (재고 증감)
    is_inbound = models.BooleanField(
        default=True,
        verbose_name='입고여부',
        help_text='True: 재고 증가, False: 재고 감소'
    )
    
    # 상태 변경 (용기)
    from_status = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='이전 상태'
    )
    
    to_status = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='이후 상태'
    )
    
    # 위치 정보
    from_location = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='이전 위치'
    )
    
    to_location = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='이후 위치'
    )
    
    # 연관 문서
    reference_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='참조문서유형',
        help_text='PO, MOVE_REPORT, ARRIVAL_SHIPPING 등'
    )
    
    reference_no = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name='참조문서번호'
    )
    
    # 메모
    remarks = models.TextField(
        blank=True,
        verbose_name='비고'
    )
    
    # 메타
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_transactions',
        verbose_name='작성자'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )
    
    class Meta:
        db_table = 'inventory_transaction'
        verbose_name = '재고 트랜잭션'
        verbose_name_plural = '재고 트랜잭션'
        ordering = ['-txn_datetime', '-id']
        indexes = [
            models.Index(fields=['txn_date', 'txn_type']),
            models.Index(fields=['cylinder_no', '-txn_datetime']),
            models.Index(fields=['gas_name', '-txn_datetime']),
            models.Index(fields=['reference_type', 'reference_no']),
        ]
    
    def __str__(self):
        return f"{self.txn_no} - {self.get_txn_type_display()}"
    
    def save(self, *args, **kwargs):
        if not self.txn_no:
            self.txn_no = self.generate_txn_no()
        super().save(*args, **kwargs)
    
    @classmethod
    def generate_txn_no(cls):
        """트랜잭션 번호 생성: INV-YYYYMMDD-NNNN"""
        today = timezone.localdate()
        prefix = f"INV-{today.strftime('%Y%m%d')}-"
        
        last_txn = cls.objects.filter(
            txn_no__startswith=prefix
        ).order_by('-txn_no').first()
        
        if last_txn:
            try:
                last_num = int(last_txn.txn_no.split('-')[-1])
                new_num = last_num + 1
            except ValueError:
                new_num = 1
        else:
            new_num = 1
        
        return f"{prefix}{new_num:04d}"


# ============================================
# 3. 용기 재고 현황 (실시간)
# ============================================
class CylinderInventory(models.Model):
    """
    용기 재고 현황 (실시간)
    
    용기종류 × 상태별 현재 재고량
    트랜잭션 발생 시 자동 갱신
    """
    
    # 용기 구분
    cylinder_type_key = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name='용기종류키',
        help_text='cy_cylinder_current.dashboard_cylinder_type_key 또는 직접 정의'
    )
    
    # 용기 종류 표시 정보 (조회 편의)
    gas_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='가스명'
    )
    
    capacity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='용량'
    )
    
    valve_spec = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='밸브 스펙'
    )
    
    cylinder_spec = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='용기 스펙'
    )
    
    enduser_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='엔드유저 코드'
    )
    
    # 상태별 재고
    STATUS_CHOICES = [
        ('EMPTY', '빈 용기'),
        ('FILLED', '충전 용기'),
        ('FILLING', '충전 중'),
        ('ANALYZING', '분석 중'),
        ('REPAIRING', '수리 중'),
        ('AT_CUSTOMER', '고객 보유'),
        ('IN_TRANSIT', '운송 중'),
        ('SCRAPPED', '폐기'),
        ('OTHER', '기타'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        db_index=True,
        verbose_name='상태'
    )
    
    # 위치
    location = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name='위치'
    )
    
    # 현재 수량
    quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='수량 (병)'
    )
    
    # 갱신 시각
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='갱신일시'
    )
    
    class Meta:
        db_table = 'cylinder_inventory'
        verbose_name = '용기 재고'
        verbose_name_plural = '용기 재고'
        unique_together = ['cylinder_type_key', 'status', 'location']
        indexes = [
            models.Index(fields=['gas_name', 'status']),
            models.Index(fields=['status', 'location']),
        ]
    
    def __str__(self):
        return f"{self.gas_name} ({self.get_status_display()}) - {self.quantity}병"


# ============================================
# 4. 제품 재고 현황 (실시간)
# ============================================
class ProductInventory(models.Model):
    """
    제품 재고 현황 (실시간)
    
    제품코드 기준 창고 재고 (충전된 용기 수량)
    - 입고: 충전 완료 용기가 창고에 입고
    - 출하: 고객에게 출하
    """
    
    # 제품 정보
    product_code = models.ForeignKey(
        'products.ProductCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory',
        verbose_name='제품코드'
    )
    
    # 제품코드 텍스트 (FK 없어도 조회 가능)
    trade_condition_code = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name='제품코드',
        help_text='예: KF001, KF013'
    )
    
    gas_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='가스명'
    )
    
    # 창고 위치
    warehouse = models.CharField(
        max_length=100,
        default='MAIN',
        db_index=True,
        verbose_name='창고',
        help_text='창고 위치 (기본: MAIN)'
    )
    
    # 현재 재고량 (충전 용기 수)
    quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='재고수량 (병)',
        help_text='창고 내 충전 용기 수'
    )
    
    # 갱신 시각
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='갱신일시'
    )
    
    class Meta:
        db_table = 'product_inventory'
        verbose_name = '제품 재고'
        verbose_name_plural = '제품 재고'
        unique_together = ['trade_condition_code', 'warehouse']
        indexes = [
            models.Index(fields=['trade_condition_code']),
            models.Index(fields=['gas_name']),
        ]
    
    def __str__(self):
        return f"{self.trade_condition_code} ({self.warehouse}) - {self.quantity}병"


# ============================================
# 5. 용기 재고 일간 스냅샷
# ============================================
class CylinderInventorySnapshot(models.Model):
    """
    용기 재고 일간 스냅샷
    
    마감 시점 용기 재고 상태 저장
    추세 분석, 이력 조회용
    """
    
    # 스냅샷 기준일
    snapshot_date = models.DateField(
        db_index=True,
        verbose_name='스냅샷 일자'
    )
    
    snapshot_datetime = models.DateTimeField(
        verbose_name='스냅샷 시각',
        help_text='실제 스냅샷 생성 시점'
    )
    
    # 용기 구분
    cylinder_type_key = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name='용기종류키'
    )
    
    gas_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='가스명'
    )
    
    capacity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='용량'
    )
    
    valve_spec = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='밸브 스펙'
    )
    
    cylinder_spec = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='용기 스펙'
    )
    
    enduser_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='엔드유저 코드'
    )
    
    # 상태
    status = models.CharField(
        max_length=20,
        db_index=True,
        verbose_name='상태'
    )
    
    location = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='위치'
    )
    
    # 스냅샷 시점 수량
    quantity = models.IntegerField(
        default=0,
        verbose_name='수량 (병)'
    )
    
    # 당일 변동
    day_in = models.IntegerField(
        default=0,
        verbose_name='당일 입고'
    )
    
    day_out = models.IntegerField(
        default=0,
        verbose_name='당일 출고'
    )
    
    # 메타
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )
    
    class Meta:
        db_table = 'cylinder_inventory_snapshot'
        verbose_name = '용기 재고 스냅샷'
        verbose_name_plural = '용기 재고 스냅샷'
        unique_together = ['snapshot_date', 'cylinder_type_key', 'status', 'location']
        ordering = ['-snapshot_date', 'cylinder_type_key']
        indexes = [
            models.Index(fields=['snapshot_date', 'gas_name']),
            models.Index(fields=['snapshot_date', 'status']),
        ]
    
    def __str__(self):
        return f"{self.snapshot_date} - {self.gas_name} ({self.status}): {self.quantity}병"


# ============================================
# 6. 제품 재고 일간 스냅샷
# ============================================
class ProductInventorySnapshot(models.Model):
    """
    제품 재고 일간 스냅샷
    
    마감 시점 제품코드별 창고 재고 저장
    """
    
    # 스냅샷 기준일
    snapshot_date = models.DateField(
        db_index=True,
        verbose_name='스냅샷 일자'
    )
    
    snapshot_datetime = models.DateTimeField(
        verbose_name='스냅샷 시각'
    )
    
    # 제품 정보
    product_code = models.ForeignKey(
        'products.ProductCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_snapshots',
        verbose_name='제품코드'
    )
    
    trade_condition_code = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name='제품코드'
    )
    
    gas_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='가스명'
    )
    
    warehouse = models.CharField(
        max_length=100,
        default='MAIN',
        verbose_name='창고'
    )
    
    # 스냅샷 시점 재고
    quantity = models.IntegerField(
        default=0,
        verbose_name='재고수량 (병)'
    )
    
    # 당일 변동
    day_in = models.IntegerField(
        default=0,
        verbose_name='당일 입고 (병)'
    )
    
    day_out = models.IntegerField(
        default=0,
        verbose_name='당일 출하 (병)'
    )
    
    # 메타
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )
    
    class Meta:
        db_table = 'product_inventory_snapshot'
        verbose_name = '제품 재고 스냅샷'
        verbose_name_plural = '제품 재고 스냅샷'
        unique_together = ['snapshot_date', 'trade_condition_code', 'warehouse']
        ordering = ['-snapshot_date', 'trade_condition_code']
        indexes = [
            models.Index(fields=['snapshot_date', 'trade_condition_code']),
        ]
    
    def __str__(self):
        return f"{self.snapshot_date} - {self.trade_condition_code}: {self.quantity}병"


# ============================================
# 7. 스냅샷 생성 로그
# ============================================
class SnapshotLog(models.Model):
    """
    스냅샷 생성 로그
    
    일간 스냅샷 생성 이력 기록
    """
    
    STATUS_CHOICES = [
        ('RUNNING', '진행중'),
        ('SUCCESS', '성공'),
        ('FAILED', '실패'),
        ('PARTIAL', '일부성공'),
    ]
    
    snapshot_date = models.DateField(
        db_index=True,
        verbose_name='스냅샷 일자'
    )
    
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='시작 시각'
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='완료 시각'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='RUNNING',
        verbose_name='상태'
    )
    
    # 결과 요약
    cylinder_snapshots_created = models.IntegerField(
        default=0,
        verbose_name='용기 스냅샷 수'
    )
    
    product_snapshots_created = models.IntegerField(
        default=0,
        verbose_name='제품 스냅샷 수'
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name='오류 메시지'
    )
    
    # 트리거 정보
    triggered_by = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='트리거',
        help_text='AUTO: 자동, MANUAL: 수동'
    )
    
    triggered_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='실행자'
    )
    
    class Meta:
        db_table = 'inventory_snapshot_log'
        verbose_name = '스냅샷 로그'
        verbose_name_plural = '스냅샷 로그'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['snapshot_date', 'status']),
        ]
    
    def __str__(self):
        return f"{self.snapshot_date} - {self.get_status_display()}"


# ============================================
# 8. 정비 입출고(FCMS 외) 로그
# ============================================
class CylinderMaintenanceLog(models.Model):
    """
    정비 입출고 로그 (FCMS 밖에서 관리되는 정비 출고/입고)

    - 한 레코드 = 용기 1본의 이벤트(OUT/IN)
    - 최신 이벤트가 OUT이고 이후 IN이 없으면 '정비중'으로 간주
    """

    EVENT_CHOICES = [
        ("OUT", "정비출고"),
        ("IN", "정비입고"),
    ]

    cylinder_no = models.CharField(
        max_length=20,
        db_index=True,
        verbose_name="용기번호",
    )

    event_type = models.CharField(
        max_length=10,
        choices=EVENT_CHOICES,
        db_index=True,
        verbose_name="구분",
    )

    event_date = models.DateField(
        default=timezone.localdate,
        db_index=True,
        verbose_name="일자",
    )

    vendor_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="정비처",
        help_text="외주처/정비업체명",
    )

    reference_no = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name="참조번호",
        help_text="내부 문서번호/전표번호 등",
    )

    remarks = models.TextField(
        blank=True,
        verbose_name="비고",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cylinder_maintenance_logs",
        verbose_name="작성자",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="등록일시")

    class Meta:
        db_table = "cylinder_maintenance_log"
        verbose_name = "정비 입출고 로그"
        verbose_name_plural = "정비 입출고 로그"
        ordering = ["-event_date", "-id"]
        indexes = [
            models.Index(fields=["cylinder_no", "-event_date"]),
            models.Index(fields=["event_type", "-event_date"]),
        ]

    def __str__(self):
        return f"{self.cylinder_no} - {self.get_event_type_display()} ({self.event_date})"
