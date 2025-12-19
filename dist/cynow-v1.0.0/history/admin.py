from django.contrib import admin
from .models import HistInventorySnapshot, HistSnapshotRequest


@admin.register(HistInventorySnapshot)
class HistInventorySnapshotAdmin(admin.ModelAdmin):
    list_display = ['snapshot_datetime', 'snapshot_type', 'gas_name', 'status', 'location', 'qty', 'created_by']
    list_filter = ['snapshot_type', 'status', 'location', 'snapshot_datetime', 'gas_name']
    search_fields = ['gas_name', 'cylinder_type_key', 'status', 'location']
    date_hierarchy = 'snapshot_datetime'
    readonly_fields = ['created_at']


@admin.register(HistSnapshotRequest)
class HistSnapshotRequestAdmin(admin.ModelAdmin):
    list_display = ['requested_at', 'requested_by', 'status', 'message']
    list_filter = ['status', 'requested_at']
    search_fields = ['reason', 'message']
    date_hierarchy = 'requested_at'
    readonly_fields = ['requested_at']
