from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.shortcuts import redirect
from core.models import Translation, EndUserMaster, EndUserDefault, EndUserException, ValveGroup, ValveGroupMapping, HiddenCylinderType


@admin.register(Translation)
class TranslationAdmin(admin.ModelAdmin):
    """다국어 번역 관리자 페이지"""
    list_display = ['field_type', 'source_text', 'display_ko', 'display_ja', 'display_en', 'is_active', 'updated_at']
    list_filter = ['field_type', 'is_active', 'created_at']
    search_fields = ['source_text', 'display_ko', 'display_ja', 'display_en', 'notes']
    list_editable = ['display_ko', 'display_ja', 'display_en', 'is_active']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('번역 정보', {
            'fields': ('field_type', 'source_text', 'is_active')
        }),
        ('다국어 표시명', {
            'fields': ('display_ko', 'display_ja', 'display_en'),
            'description': '한국어가 기본 언어입니다. 일본어/영어는 선택사항입니다.'
        }),
        ('추가 정보', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
    
    actions = ['activate_translations', 'deactivate_translations']
    
    def activate_translations(self, request, queryset):
        """선택한 번역들을 활성화"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count}개의 번역이 활성화되었습니다.')
    activate_translations.short_description = '선택한 번역 활성화'
    
    def deactivate_translations(self, request, queryset):
        """선택한 번역들을 비활성화"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count}개의 번역이 비활성화되었습니다.')
    deactivate_translations.short_description = '선택한 번역 비활성화'


@admin.register(EndUserMaster)
class EndUserMasterAdmin(admin.ModelAdmin):
    """EndUser 마스터 관리 - 정책 관리 페이지로 이동"""
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def changelist_view(self, request, extra_context=None):
        """목록 페이지 접근 시 정책 관리 페이지로 리다이렉트"""
        from django.shortcuts import redirect
        return redirect('core:enduser_master_list')
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """상세 페이지 접근 시 정책 관리 페이지로 리다이렉트"""
        from django.shortcuts import redirect
        return redirect('core:enduser_master_list')


# 정책 관련 모델들은 정책 관리 페이지에서만 관리
# Django admin에서는 읽기 전용으로 표시하고 정책 관리 페이지로 안내

@admin.register(EndUserDefault)
class EndUserDefaultAdmin(admin.ModelAdmin):
    """EndUser 기본값 관리 - 정책 관리 페이지로 이동"""
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def changelist_view(self, request, extra_context=None):
        """목록 페이지 접근 시 정책 관리 페이지로 리다이렉트"""
        from django.shortcuts import redirect
        return redirect('core:enduser_default_list')
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """상세 페이지 접근 시 정책 관리 페이지로 리다이렉트"""
        from django.shortcuts import redirect
        return redirect('core:enduser_default_list')


@admin.register(EndUserException)
class EndUserExceptionAdmin(admin.ModelAdmin):
    """EndUser 예외 관리 - 정책 관리 페이지로 이동"""
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def changelist_view(self, request, extra_context=None):
        """목록 페이지 접근 시 정책 관리 페이지로 리다이렉트"""
        from django.shortcuts import redirect
        return redirect('core:enduser_exception_list')
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """상세 페이지 접근 시 정책 관리 페이지로 리다이렉트"""
        from django.shortcuts import redirect
        return redirect('core:enduser_exception_list')


@admin.register(ValveGroup)
class ValveGroupAdmin(admin.ModelAdmin):
    """밸브 그룹 관리 - 정책 관리 페이지로 이동"""
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def changelist_view(self, request, extra_context=None):
        """목록 페이지 접근 시 정책 관리 페이지로 리다이렉트"""
        from django.shortcuts import redirect
        return redirect('core:valve_group_list')
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """상세 페이지 접근 시 정책 관리 페이지로 리다이렉트"""
        from django.shortcuts import redirect
        return redirect('core:valve_group_list')


@admin.register(ValveGroupMapping)
class ValveGroupMappingAdmin(admin.ModelAdmin):
    """밸브 그룹 매핑 관리 - 정책 관리 페이지로 이동"""
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def changelist_view(self, request, extra_context=None):
        """목록 페이지 접근 시 정책 관리 페이지로 리다이렉트"""
        from django.shortcuts import redirect
        return redirect('core:valve_group_list')
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """상세 페이지 접근 시 정책 관리 페이지로 리다이렉트"""
        from django.shortcuts import redirect
        return redirect('core:valve_group_list')


@admin.register(HiddenCylinderType)
class HiddenCylinderTypeAdmin(admin.ModelAdmin):
    """숨김 용기종류 관리"""
    list_display = ['gas_name', 'capacity', 'valve_type', 'enduser', 'hidden_by', 'created_at']
    list_filter = ['gas_name', 'created_at']
    search_fields = ['gas_name', 'capacity', 'valve_type', 'cylinder_spec', 'enduser', 'reason']
    readonly_fields = ['cylinder_type_key', 'created_at']
    
    fieldsets = (
        ('용기종류 정보', {
            'fields': ('cylinder_type_key', 'gas_name', 'capacity', 'valve_type', 'cylinder_spec', 'enduser')
        }),
        ('숨김 정보', {
            'fields': ('hidden_by', 'reason', 'created_at')
        }),
    )
    
    actions = ['unhide_cylinder_types']
    
    def unhide_cylinder_types(self, request, queryset):
        """선택한 용기종류 숨김 해제"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count}개의 용기종류가 다시 표시됩니다.')
    unhide_cylinder_types.short_description = '선택한 용기종류 숨김 해제'
