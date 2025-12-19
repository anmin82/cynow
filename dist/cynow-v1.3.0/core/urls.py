"""Core 앱 URL 설정"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # 정책 관리 메인
    path('policy/', views.policy_management, name='policy_management'),
    
    # EndUser 마스터 관리
    path('policy/enduser-master/', views.enduser_master_list, name='enduser_master_list'),
    path('policy/enduser-master/add/', views.enduser_master_add, name='enduser_master_add'),
    path('policy/enduser-master/<int:enduser_id>/edit/', views.enduser_master_edit, name='enduser_master_edit'),
    path('policy/enduser-master/<int:enduser_id>/delete/', views.enduser_master_delete, name='enduser_master_delete'),
    
    # EndUser 기본값 관리
    path('policy/enduser-default/', views.enduser_default_list, name='enduser_default_list'),
    path('policy/enduser-default/add/', views.enduser_default_add, name='enduser_default_add'),
    path('policy/enduser-default/<int:default_id>/edit/', views.enduser_default_edit, name='enduser_default_edit'),
    path('policy/enduser-default/<int:default_id>/toggle/', views.enduser_default_toggle, name='enduser_default_toggle'),
    path('policy/enduser-default/<int:default_id>/delete/', views.enduser_default_delete, name='enduser_default_delete'),
    
    # EndUser 예외 관리
    path('policy/enduser-exception/', views.enduser_exception_list, name='enduser_exception_list'),
    path('policy/enduser-exception/add/', views.enduser_exception_add, name='enduser_exception_add'),
    path('policy/enduser-exception/upload/', views.enduser_exception_upload, name='enduser_exception_upload'),
    path('policy/enduser-exception/template/', views.enduser_exception_template, name='enduser_exception_template'),
    path('policy/enduser-exception/<int:exception_id>/toggle/', views.enduser_exception_toggle, name='enduser_exception_toggle'),
    
    # 밸브 그룹 관리
    path('policy/valve-group/', views.valve_group_list, name='valve_group_list'),
    path('policy/valve-group/add/', views.valve_group_add, name='valve_group_add'),
    path('policy/valve-group/<int:group_id>/', views.valve_group_detail, name='valve_group_detail'),
    path('policy/valve-group/<int:group_id>/mapping/add/', views.valve_group_mapping_add, name='valve_group_mapping_add'),
    path('policy/valve-group/mapping/<int:mapping_id>/toggle-primary/', views.valve_group_mapping_toggle_primary, name='valve_group_mapping_toggle_primary'),
    path('policy/valve-group/mapping/<int:mapping_id>/toggle-active/', views.valve_group_mapping_toggle_active, name='valve_group_mapping_toggle_active'),
    
    # 밸브 스펙 검색 (AJAX)
    path('api/valve-spec-search/', views.valve_spec_search, name='valve_spec_search'),
    
    # 용기 스펙 검색 (AJAX)
    path('api/cylinder-spec-search/', views.cylinder_spec_search, name='cylinder_spec_search'),
]
