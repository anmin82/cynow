from django.contrib import admin
from .models import CylinderMemo


@admin.register(CylinderMemo)
class CylinderMemoAdmin(admin.ModelAdmin):
    list_display = ['id', 'cylinder_no', 'author_name', 'short_content', 'password', 'parent_info', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['cylinder_no', 'author_name', 'content']
    list_editable = ['is_active']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('cylinder_no', 'author_name', 'password', 'content')
        }),
        ('답글 정보', {
            'fields': ('parent',),
            'classes': ('collapse',)
        }),
        ('관리', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    actions = ['activate_memos', 'deactivate_memos']
    
    def short_content(self, obj):
        """내용 요약"""
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    short_content.short_description = '내용'
    
    def parent_info(self, obj):
        """답글 여부"""
        if obj.parent:
            return f"↳ #{obj.parent.id}"
        return "-"
    parent_info.short_description = '답글'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent')
    
    @admin.action(description='선택한 메모 활성화')
    def activate_memos(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count}개 메모가 활성화되었습니다.')
    
    @admin.action(description='선택한 메모 비활성화 (삭제)')
    def deactivate_memos(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count}개 메모가 비활성화되었습니다.')
