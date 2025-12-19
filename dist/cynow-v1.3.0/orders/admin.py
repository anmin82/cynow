"""
PO 관리 Django Admin
"""
from django.contrib import admin
from .models import PO, POItem, POSchedule, ReservedDocNo, POFcmsMatch, OrphanFcmsDoc, POProgressSnapshot


class POItemInline(admin.TabularInline):
    """PO 라인 아이템 인라인"""
    model = POItem
    extra = 1
    fields = ['line_no', 'trade_condition_code', 'trade_condition_name', 'qty', 'unit_price', 'remarks']


class POScheduleInline(admin.TabularInline):
    """분할납품 일정 인라인"""
    model = POSchedule
    extra = 1
    fields = ['sequence', 'due_date', 'qty', 'remarks']


@admin.register(PO)
class POAdmin(admin.ModelAdmin):
    """PO 관리"""
    list_display = [
        'customer_order_no',
        'supplier_user_name',
        'status',
        'due_date',
        'is_backfilled',
        'needs_review',
        'created_at'
    ]
    list_filter = ['status', 'is_backfilled', 'needs_review', 'created_at']
    search_fields = ['customer_order_no', 'supplier_user_code', 'supplier_user_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('customer_order_no', 'supplier_user_code', 'supplier_user_name')
        }),
        ('날짜', {
            'fields': ('received_at', 'due_date')
        }),
        ('상태', {
            'fields': ('status', 'memo')
        }),
        ('역수입 관련', {
            'fields': ('is_backfilled', 'needs_review', 'review_note'),
            'classes': ('collapse',)
        }),
        ('관리 정보', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [POItemInline, POScheduleInline]


@admin.register(POItem)
class POItemAdmin(admin.ModelAdmin):
    """PO 라인"""
    list_display = ['po', 'line_no', 'trade_condition_code', 'trade_condition_name', 'qty', 'unit_price']
    list_filter = ['po__status']
    search_fields = ['po__customer_order_no', 'trade_condition_code', 'trade_condition_name']


@admin.register(ReservedDocNo)
class ReservedDocNoAdmin(admin.ModelAdmin):
    """예약번호"""
    list_display = ['reserved_no', 'po', 'doc_type', 'status', 'reserved_at', 'expires_at']
    list_filter = ['doc_type', 'status']
    search_fields = ['reserved_no', 'po__customer_order_no']
    readonly_fields = ['reserved_at', 'matched_at']


@admin.register(POFcmsMatch)
class POFcmsMatchAdmin(admin.ModelAdmin):
    """FCMS 매칭"""
    list_display = ['po', 'arrival_shipping_no', 'move_report_no', 'match_state', 'matched_at']
    list_filter = ['match_state', 'is_manual_match']
    search_fields = ['po__customer_order_no', 'arrival_shipping_no', 'move_report_no']


@admin.register(OrphanFcmsDoc)
class OrphanFcmsDocAdmin(admin.ModelAdmin):
    """고아 문서"""
    list_display = ['doc_type', 'doc_no', 'supplier_user_code', 'item_code', 'qty', 'is_resolved']
    list_filter = ['doc_type', 'is_resolved']
    search_fields = ['doc_no', 'supplier_user_code', 'item_code']


@admin.register(POProgressSnapshot)
class POProgressSnapshotAdmin(admin.ModelAdmin):
    """진행 현황 스냅샷"""
    list_display = [
        'po', 
        'snapshot_at', 
        'order_qty', 
        'instruction_qty', 
        'filling_qty', 
        'warehouse_in_qty', 
        'shipping_qty',
        'progress_rate'
    ]
    list_filter = ['snapshot_at']
    search_fields = ['po__customer_order_no']
    readonly_fields = ['snapshot_at']
