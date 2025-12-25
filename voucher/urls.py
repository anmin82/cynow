"""
견적서/전표 URL 설정
"""
from django.urls import path
from . import views

app_name = 'voucher'

urlpatterns = [
    # 견적서 목록/상세
    path('quotes/', views.quote_list, name='quote_list'),
    path('quote/create/', views.quote_create, name='quote_create'),
    path('quote/<int:pk>/', views.quote_detail, name='quote_detail'),
    path('quote/<int:pk>/edit/', views.quote_edit, name='quote_edit'),
    
    # 다운로드
    path('quote/<int:pk>/download/', views.quote_download, name='quote_download'),
    path('quote/<int:pk>/preview/', views.generate_quote_preview, name='quote_preview'),
    
    # 단가표
    path('price-list/', views.generate_price_list, name='price_list'),
    path('price-list/download/', views.price_list_download, name='price_list_download'),
    
    # 회사정보
    path('companies/', views.company_list, name='company_list'),
    path('company/create/', views.company_create, name='company_create'),
    path('company/<int:pk>/edit/', views.company_edit, name='company_edit'),
    
    # 템플릿 관리
    path('templates/', views.template_list, name='template_list'),
    path('template/<int:pk>/download/', views.template_download, name='template_download'),
    path('template/download/', views.template_download_file, name='template_download_file'),
    path('template/<int:pk>/set-default/', views.template_set_default, name='template_set_default'),
    path('template/<int:pk>/delete/', views.template_delete, name='template_delete'),
    path('template/guide/', views.template_guide, name='template_guide'),
    path('template/test-quote/', views.template_test_quote, name='template_test_quote'),
    
    # ONLYOFFICE 연동
    path('template/edit/<str:filename>/', views.template_editor, name='template_editor'),
    path('template/file/<str:filename>', views.template_file_serve, name='template_file_serve'),
    path('template/callback/<str:filename>', views.template_callback, name='template_callback'),
    
    # API
    path('api/generate/', views.api_generate_docx, name='api_generate'),
]

