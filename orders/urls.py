"""
수주 페이지 URL 라우팅
"""

from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # 수주 목록 및 생성
    path('', views.po_list, name='list'),
    path('new/', views.po_create, name='new'),
    
    # 수주관리표 (생산 진척 현황)
    path('management/', views.order_management_list, name='management'),
    path('management/<str:customer_order_no>/', views.order_management_detail, name='management_detail'),
    path('management/<str:customer_order_no>/sync/', views.sync_fcms_progress, name='sync_progress'),
    
    # 가발행 이동서 관리
    path('planned-moves/<str:customer_order_no>/', views.planned_move_list, name='planned_moves'),
    path('planned-moves/<str:customer_order_no>/create/', views.planned_move_create, name='planned_move_create'),
    path('planned-moves/<str:customer_order_no>/match-all/', views.planned_move_match_all, name='planned_move_match_all'),
    path('planned-move/<int:pk>/delete/', views.planned_move_delete, name='planned_move_delete'),
    path('planned-move/<int:pk>/match/', views.planned_move_match, name='planned_move_match'),
    
    # API 엔드포인트
    path('api/customers/<int:customer_id>/', views.api_get_customer, name='api_get_customer'),
    path('api/products/', views.api_list_products, name='api_list_products'),
    path('api/products/search/', views.api_search_products, name='api_search_products'),
    path('api/products/<str:product_code>/', views.api_get_product, name='api_get_product'),
    path('api/fcms-progress/<str:customer_order_no>/', views.api_fcms_progress, name='api_fcms_progress'),
    path('api/next-move-no/', views.api_next_move_no, name='api_next_move_no'),
    path('api/check-move-no/', views.api_check_move_no, name='api_check_move_no'),
    
    # ⚠️ customer_order_no 기반 경로는 맨 아래 배치
    path('<str:customer_order_no>/', views.po_detail, name='detail'),
    path('<str:customer_order_no>/edit/', views.po_edit, name='edit'),
    path('<str:customer_order_no>/delete/', views.po_delete, name='delete'),
    path('<str:customer_order_no>/generate-guide/', views.generate_guide, name='generate_guide'),
    path('<str:customer_order_no>/check-match/', views.check_fcms_match, name='check_match'),
]


