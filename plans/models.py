from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from core.utils.cylinder_type import generate_cylinder_type_key


class PlanForecastMonthly(models.Model):
    """출하 계획 (FORECAST)"""
    month = models.DateField(help_text="YYYY-MM-01 형식")
    cylinder_type_key = models.CharField(max_length=32, db_index=True)
    
    # Denormalized fields for search convenience
    gas_name = models.CharField(max_length=100, db_index=True)
    capacity = models.CharField(max_length=50, null=True, blank=True)
    valve_spec = models.CharField(max_length=200, null=True, blank=True)
    cylinder_spec = models.CharField(max_length=200, null=True, blank=True)
    usage_place = models.CharField(max_length=100, null=True, blank=True)
    
    planned_ship_qty = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="월 출하 필요 병수"
    )
    note = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'plan_forecast_monthly'
        unique_together = [['month', 'cylinder_type_key']]
        indexes = [
            models.Index(fields=['month', 'cylinder_type_key']),
            models.Index(fields=['gas_name', 'capacity']),
        ]
        verbose_name = '출하 계획'
        verbose_name_plural = '출하 계획'
    
    def __str__(self):
        return f"{self.month} - {self.gas_name} ({self.planned_ship_qty}병)"


class PlanScheduledMonthly(models.Model):
    """투입 계획 (SCHEDULED)"""
    month = models.DateField(help_text="YYYY-MM-01 형식")
    cylinder_type_key = models.CharField(max_length=32, db_index=True)
    
    # Denormalized fields
    gas_name = models.CharField(max_length=100, db_index=True)
    capacity = models.CharField(max_length=50, null=True, blank=True)
    valve_spec = models.CharField(max_length=200, null=True, blank=True)
    cylinder_spec = models.CharField(max_length=200, null=True, blank=True)
    usage_place = models.CharField(max_length=100, null=True, blank=True)
    
    add_purchase_qty = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0,
        help_text="신규 구매 수량"
    )
    add_refurb_qty = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0,
        help_text="재생 수량"
    )
    recover_from_defect_qty = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0,
        help_text="이상에서 회수 수량"
    )
    convert_gas_qty = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0,
        help_text="가스 전환 수량"
    )
    note = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'plan_scheduled_monthly'
        unique_together = [['month', 'cylinder_type_key']]
        indexes = [
            models.Index(fields=['month', 'cylinder_type_key']),
            models.Index(fields=['gas_name', 'capacity']),
        ]
        verbose_name = '투입 계획'
        verbose_name_plural = '투입 계획'
    
    def __str__(self):
        return f"{self.month} - {self.gas_name}"


class PlanFillingMonthly(models.Model):
    """충전 계획 (FILLING) - 공용기를 제품으로 만드는 계획"""
    month = models.DateField(help_text="YYYY-MM-01 형식")
    cylinder_type_key = models.CharField(max_length=32, db_index=True)
    
    # Denormalized fields
    gas_name = models.CharField(max_length=100, db_index=True)
    capacity = models.CharField(max_length=50, null=True, blank=True)
    valve_spec = models.CharField(max_length=200, null=True, blank=True)
    cylinder_spec = models.CharField(max_length=200, null=True, blank=True)
    usage_place = models.CharField(max_length=100, null=True, blank=True)
    
    planned_fill_qty = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0,
        help_text="월 충전 계획 수량"
    )
    is_shutdown = models.BooleanField(
        default=False,
        help_text="오버홀/셧다운 여부 (True면 충전 불가)"
    )
    note = models.TextField(blank=True, null=True, help_text="예: 4월 전체 오버홀")
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'plan_filling_monthly'
        unique_together = [['month', 'cylinder_type_key']]
        indexes = [
            models.Index(fields=['month', 'cylinder_type_key']),
            models.Index(fields=['gas_name', 'capacity']),
        ]
        verbose_name = '충전 계획'
        verbose_name_plural = '충전 계획'
    
    def __str__(self):
        shutdown = " [오버홀]" if self.is_shutdown else ""
        return f"{self.month} - {self.gas_name} ({self.planned_fill_qty}병){shutdown}"