"""
견적서/전표 Admin 설정
"""
from django.contrib import admin
from .models import Customer, Quote, QuoteItem, DocumentTemplate


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'manager_name', 'tel', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name', 'manager_name']
    ordering = ['code']


class QuoteItemInline(admin.TabularInline):
    model = QuoteItem
    extra = 1
    fields = ['seq', 'product_code', 'gas_name', 'material_code', 'filling_weight', 
              'currency', 'price_per_kg', 'packing_price']


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ['quote_no', 'title', 'customer', 'quote_date', 'status', 'total_amount']
    list_filter = ['status', 'quote_date', 'default_currency']
    search_fields = ['quote_no', 'title', 'customer__name']
    date_hierarchy = 'quote_date'
    inlines = [QuoteItemInline]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('quote_no', 'title', 'quote_date', 'valid_until', 'status')
        }),
        ('거래처', {
            'fields': ('customer', 'customer_address', 'customer_ceo', 'customer_tel',
                      'customer_manager', 'customer_manager_tel', 'customer_manager_email')
        }),
        ('공급처', {
            'fields': ('supplier_name', 'supplier_address', 'supplier_ceo', 
                      'supplier_tel', 'supplier_fax', 
                      'supplier_manager', 'supplier_manager_tel', 'supplier_manager_email'),
            'classes': ('collapse',)
        }),
        ('하단 문구', {
            'fields': ('valid_period', 'trade_terms', 'bank_account'),
            'classes': ('collapse',)
        }),
        ('금액', {
            'fields': ('default_currency', 'total_amount')
        }),
        ('기타', {
            'fields': ('note', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'filename', 'is_default', 'is_active']
    list_filter = ['template_type', 'is_active', 'is_default']
    search_fields = ['name', 'filename']

