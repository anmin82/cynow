from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # 제품코드 목록
    path('', views.product_list, name='list'),
    
    # CDC 동기화
    path('sync/', views.sync_from_cdc, name='sync'),
    
    # 제품코드 상세/수정
    path('<str:pk>/', views.product_detail, name='detail'),
    path('<str:pk>/edit/', views.product_edit, name='edit'),
    
    # 단가 관리
    path('<str:pk>/price/add/', views.price_add, name='price_add'),
    path('price/<int:price_id>/delete/', views.price_delete, name='price_delete'),
]

