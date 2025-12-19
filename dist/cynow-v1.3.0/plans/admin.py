from django.contrib import admin
from .models import PlanForecastMonthly, PlanScheduledMonthly


@admin.register(PlanForecastMonthly)
class PlanForecastMonthlyAdmin(admin.ModelAdmin):
    list_display = ['month', 'gas_name', 'capacity', 'planned_ship_qty', 'created_by', 'created_at']
    list_filter = ['month', 'gas_name', 'created_at']
    search_fields = ['gas_name', 'cylinder_type_key', 'note']
    date_hierarchy = 'month'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PlanScheduledMonthly)
class PlanScheduledMonthlyAdmin(admin.ModelAdmin):
    list_display = ['month', 'gas_name', 'capacity', 'add_purchase_qty', 'add_refurb_qty', 'created_by', 'created_at']
    list_filter = ['month', 'gas_name', 'created_at']
    search_fields = ['gas_name', 'cylinder_type_key', 'note']
    date_hierarchy = 'month'
    readonly_fields = ['created_at', 'updated_at']
