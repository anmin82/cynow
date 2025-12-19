from django.contrib import admin
from .models import ReportExportLog


@admin.register(ReportExportLog)
class ReportExportLogAdmin(admin.ModelAdmin):
    list_display = ['report_type', 'exported_at', 'exported_by', 'file_path']
    list_filter = ['report_type', 'exported_at']
    search_fields = ['file_path']
    date_hierarchy = 'exported_at'
    readonly_fields = ['exported_at']
