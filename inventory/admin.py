from django.contrib import admin
from .models import (
    InventorySettings,
    InventoryTransaction,
    CylinderInventory,
    ProductInventory,
    CylinderInventorySnapshot,
    ProductInventorySnapshot,
    SnapshotLog,
    CylinderMaintenanceLog,
)


@admin.register(InventorySettings)
class InventorySettingsAdmin(admin.ModelAdmin):
    list_display = ['id', 'cutoff_hour', 'cutoff_minute', 'is_active', 'updated_at']
    list_filter = ['is_active']


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ['txn_no', 'txn_type', 'txn_date', 'cylinder_no', 'gas_name', 'quantity', 'is_inbound', 'created_at']
    list_filter = ['txn_type', 'txn_date', 'is_inbound']
    search_fields = ['txn_no', 'cylinder_no', 'gas_name', 'reference_no']
    date_hierarchy = 'txn_date'
    ordering = ['-txn_datetime']


@admin.register(CylinderInventory)
class CylinderInventoryAdmin(admin.ModelAdmin):
    list_display = ['cylinder_type_key', 'gas_name', 'status', 'location', 'quantity', 'updated_at']
    list_filter = ['status', 'gas_name', 'location']
    search_fields = ['cylinder_type_key', 'gas_name']


@admin.register(ProductInventory)
class ProductInventoryAdmin(admin.ModelAdmin):
    list_display = ['trade_condition_code', 'gas_name', 'warehouse', 'quantity', 'updated_at']
    list_filter = ['warehouse', 'gas_name']
    search_fields = ['trade_condition_code', 'gas_name']


@admin.register(CylinderInventorySnapshot)
class CylinderInventorySnapshotAdmin(admin.ModelAdmin):
    list_display = ['snapshot_date', 'cylinder_type_key', 'gas_name', 'status', 'quantity', 'day_in', 'day_out']
    list_filter = ['snapshot_date', 'status', 'gas_name']
    search_fields = ['cylinder_type_key', 'gas_name']
    date_hierarchy = 'snapshot_date'


@admin.register(ProductInventorySnapshot)
class ProductInventorySnapshotAdmin(admin.ModelAdmin):
    list_display = ['snapshot_date', 'trade_condition_code', 'gas_name', 'warehouse', 'quantity', 'day_in', 'day_out']
    list_filter = ['snapshot_date', 'warehouse', 'gas_name']
    search_fields = ['trade_condition_code', 'gas_name']
    date_hierarchy = 'snapshot_date'


@admin.register(SnapshotLog)
class SnapshotLogAdmin(admin.ModelAdmin):
    list_display = ['snapshot_date', 'status', 'cylinder_snapshots_created', 'product_snapshots_created', 'started_at', 'completed_at']
    list_filter = ['status', 'snapshot_date']
    date_hierarchy = 'snapshot_date'


@admin.register(CylinderMaintenanceLog)
class CylinderMaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ['event_date', 'event_type', 'cylinder_no', 'vendor_name', 'reference_no', 'created_at']
    list_filter = ['event_type', 'event_date']
    search_fields = ['cylinder_no', 'vendor_name', 'reference_no']
    date_hierarchy = 'event_date'
