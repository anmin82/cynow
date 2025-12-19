from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SnapshotType(models.TextChoices):
    DAILY = 'DAILY', '정기'
    MANUAL = 'MANUAL', '수동'


class HistInventorySnapshot(models.Model):
    """변화 이력 스냅샷 - 특정 시각의 VIEW 집계 결과"""
    snapshot_datetime = models.DateTimeField(db_index=True, help_text="KST 기준")
    snapshot_type = models.CharField(
        max_length=10,
        choices=SnapshotType.choices,
        db_index=True
    )
    cylinder_type_key = models.CharField(max_length=32, db_index=True)
    
    # Denormalized fields
    gas_name = models.CharField(max_length=100, db_index=True)
    capacity = models.CharField(max_length=50, null=True, blank=True)
    valve_spec = models.CharField(max_length=200, null=True, blank=True)
    cylinder_spec = models.CharField(max_length=200, null=True, blank=True)
    usage_place = models.CharField(max_length=100, null=True, blank=True)
    
    status = models.CharField(max_length=20, db_index=True)
    location = models.CharField(max_length=100, db_index=True)
    qty = models.IntegerField(help_text="수량")
    
    source_view_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="VIEW의 updated_at 저장"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="DAILY는 null, MANUAL은 user"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'hist_inventory_snapshot'
        unique_together = [
            ['snapshot_datetime', 'snapshot_type', 'cylinder_type_key', 'status', 'location']
        ]
        indexes = [
            models.Index(fields=['snapshot_datetime']),
            models.Index(fields=['cylinder_type_key', 'status']),
            models.Index(fields=['gas_name', 'capacity']),
        ]
        verbose_name = '인벤토리 스냅샷'
        verbose_name_plural = '인벤토리 스냅샷'
    
    def __str__(self):
        return f"{self.snapshot_datetime} - {self.gas_name} ({self.status}) - {self.qty}"


class SnapshotRequestStatus(models.TextChoices):
    SUCCESS = 'SUCCESS', '성공'
    FAILED = 'FAILED', '실패'


class HistSnapshotRequest(models.Model):
    """수동 스냅샷 기록 (감사 로그)"""
    requested_at = models.DateTimeField(auto_now_add=True)
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=SnapshotRequestStatus.choices,
        default=SnapshotRequestStatus.SUCCESS
    )
    message = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'hist_snapshot_request'
        verbose_name = '스냅샷 요청 기록'
        verbose_name_plural = '스냅샷 요청 기록'
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"{self.requested_at} - {self.status}"
