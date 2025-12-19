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
    
    # ⚠️ customer_order_no 기반 경로는 맨 아래 배치
    path('<str:customer_order_no>/', views.po_detail, name='detail'),
    path('<str:customer_order_no>/edit/', views.po_edit, name='edit'),
    path('<str:customer_order_no>/delete/', views.po_delete, name='delete'),
    path('<str:customer_order_no>/generate-guide/', views.generate_guide, name='generate_guide'),
    path('<str:customer_order_no>/check-match/', views.check_fcms_match, name='check_match'),
]


