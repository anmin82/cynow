"""
devices 앱 관리자

Scale Gateway API - 저울 데이터 로그 관리
"""
from django.contrib import admin
from .models import ScaleWeightLog


@admin.register(ScaleWeightLog)
class ScaleWeightLogAdmin(admin.ModelAdmin):
    """저울 무게 로그 관리자"""
    
    list_display = [
        'id',
        'cylinder_no',
        'event_type',
        'gross_kg',
        'scale_id',
        'committed_at',
        'arrival_shipping_no',
    ]
    
    list_filter = [
        'event_type',
        'scale_id',
        'committed_at',
    ]
    
    search_fields = [
        'cylinder_no',
        'arrival_shipping_no',
        'move_report_no',
    ]
    
    readonly_fields = [
        'committed_at',
    ]
    
    ordering = ['-committed_at']
    
    fieldsets = [
        ('기본 정보', {
            'fields': ['scale_id', 'cylinder_no', 'event_type']
        }),
        ('무게 정보', {
            'fields': ['gross_kg', 'raw_line']
        }),
        ('시간 정보', {
            'fields': ['received_at', 'committed_at']
        }),
        ('연결 정보', {
            'fields': ['arrival_shipping_no', 'move_report_no'],
            'classes': ['collapse']
        }),
    ]
