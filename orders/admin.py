"""
수주 관리 Admin
"""
from django.contrib import admin
from .models import PO, POItem, MoveNoGuide, FCMSMatchStatus


class POItemInline(admin.TabularInline):
    model = POItem
    extra = 1
    fields = ['line_no', 'trade_condition_code', 'trade_condition_name', 'qty', 'remarks']


@admin.register(PO)
class POAdmin(admin.ModelAdmin):
    list_display = [
        'customer_order_no',
        'supplier_user_name',
        'received_at',
        'status',
        'created_by',
        'created_at',
    ]
    list_filter = ['status', 'received_at']
    search_fields = ['customer_order_no', 'supplier_user_code', 'supplier_user_name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [POItemInline]
    
    fieldsets = (
        ('PO 정보', {
            'fields': ('customer_order_no', 'supplier_user_code', 'supplier_user_name')
        }),
        ('날짜 정보', {
            'fields': ('received_at', 'status')
        }),
        ('기타', {
            'fields': ('memo', 'created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(POItem)
class POItemAdmin(admin.ModelAdmin):
    list_display = [
        'po',
        'line_no',
        'trade_condition_code',
        'trade_condition_name',
        'qty',
    ]
    list_filter = ['po']
    search_fields = ['po__customer_order_no', 'trade_condition_code', 'trade_condition_name']


@admin.register(MoveNoGuide)
class MoveNoGuideAdmin(admin.ModelAdmin):
    list_display = [
        'po',
        'suggested_move_no',
        'state',
        'fcms_actual_move_no',
        'created_at',
    ]
    list_filter = ['state', 'created_at']
    search_fields = ['po__customer_order_no', 'suggested_move_no', 'fcms_actual_move_no']
    readonly_fields = ['created_at']


@admin.register(FCMSMatchStatus)
class FCMSMatchStatusAdmin(admin.ModelAdmin):
    list_display = [
        'po',
        'match_state',
        'fcms_arrival_shipping_no',
        'fcms_move_report_no',
        'last_checked_at',
    ]
    list_filter = ['match_state', 'last_checked_at']
    search_fields = [
        'po__customer_order_no',
        'fcms_arrival_shipping_no',
        'fcms_move_report_no',
    ]
    readonly_fields = ['last_checked_at']


