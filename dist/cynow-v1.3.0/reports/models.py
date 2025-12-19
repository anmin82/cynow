from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json


class ReportType(models.TextChoices):
    WEEKLY = 'WEEKLY', '주간'
    MONTHLY = 'MONTHLY', '월간'
    HISTORY_EXPORT = 'HISTORY_EXPORT', '이력 내보내기'


class ReportExportLog(models.Model):
    """보고서 출력 이력"""
    report_type = models.CharField(
        max_length=20,
        choices=ReportType.choices,
        db_index=True
    )
    params_json = models.JSONField(
        default=dict,
        help_text="필터/기간 등 파라미터"
    )
    exported_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    exported_at = models.DateTimeField(auto_now_add=True)
    file_path = models.CharField(max_length=500, blank=True, null=True)
    
    class Meta:
        db_table = 'report_export_log'
        verbose_name = '보고서 출력 이력'
        verbose_name_plural = '보고서 출력 이력'
        ordering = ['-exported_at']
    
    def __str__(self):
        return f"{self.report_type} - {self.exported_at}"
