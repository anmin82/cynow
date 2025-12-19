"""
devices 앱 모델

Scale Gateway API - 저울 데이터 로그
"""
from django.db import models
from decimal import Decimal


class ScaleWeightLog(models.Model):
    """
    저울 무게 측정 로그
    
    출하/회수 확정(Commit) 시점의 저울 측정값을 기록.
    현장에서는 보호캡을 분리한 후 계측하므로,
    실측값이 곧 표준 GROSS(보호캡 제외)로 간주.
    """
    
    EVENT_TYPE_CHOICES = [
        ('SHIP', '출하'),
        ('RETURN', '회수'),
    ]
    
    # 저울 식별
    scale_id = models.CharField(
        max_length=50,
        default='default',
        verbose_name='저울 ID',
        help_text='저울 식별자 (다중 저울 지원 대비)'
    )
    
    # 용기 정보
    cylinder_no = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name='용기번호',
        help_text='계측 대상 용기번호'
    )
    
    # 이벤트 유형
    event_type = models.CharField(
        max_length=10,
        choices=EVENT_TYPE_CHOICES,
        verbose_name='이벤트 유형',
        help_text='SHIP: 출하, RETURN: 회수'
    )
    
    # 무게 (보호캡 분리 후 계측값 = 표준 GROSS)
    gross_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='총무게 (kg)',
        help_text='보호캡 분리 후 계측값 (표준 GROSS)'
    )
    
    # 원본 데이터
    raw_line = models.TextField(
        verbose_name='원본 라인',
        help_text='저울에서 수신한 원본 데이터 (예: "ST , +000053.26 _kg")'
    )
    
    # 시간 정보
    received_at = models.DateTimeField(
        verbose_name='수신 시각',
        help_text='리스너가 최신값을 받은 시각'
    )
    committed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='확정 시각',
        help_text='출하/회수 확정(Commit) 시각'
    )
    
    # 연결 정보 (확장 대비)
    arrival_shipping_no = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='입출고번호',
        help_text='TR_ORDERS 연결 대비 (arrival_shipping_no)'
    )
    move_report_no = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='이동보고서번호',
        help_text='TR_MOVE_REPORTS 연결 대비 (move_report_no)'
    )
    
    class Meta:
        db_table = 'scale_weight_log'
        verbose_name = '저울 무게 로그'
        verbose_name_plural = '저울 무게 로그'
        ordering = ['-committed_at']
        indexes = [
            models.Index(fields=['cylinder_no', '-committed_at']),
            models.Index(fields=['event_type', '-committed_at']),
        ]
    
    def __str__(self):
        return f"{self.cylinder_no} - {self.get_event_type_display()} - {self.gross_kg}kg"
