"""
PO 관리 URL 라우팅
"""

from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # PO 리스트 및 생성
    path('', views.po_list, name='list'),
    path('new/', views.po_create, name='new'),  # create → new로 변경 (더 직관적)
    
    # 예약번호 관리
    path('reservation/<int:reservation_id>/release/', views.release_reservation, name='release_reservation'),
    
    # 역수입 검토
    path('backfill/review/', views.backfill_review, name='backfill_review'),
    path('backfill/<int:po_id>/approve/', views.approve_backfill, name='approve_backfill'),
    path('orphan/<int:orphan_id>/match/', views.match_orphan, name='match_orphan'),
    
    # 제조부 납기 화면
    path('manufacturing/schedule/', views.manufacturing_schedule, name='manufacturing_schedule'),
    
    # ⚠️ 이 경로들은 맨 아래에 배치 (customer_order_no가 다른 경로와 충돌하지 않도록)
    path('<str:customer_order_no>/', views.po_detail, name='detail'),
    path('<str:customer_order_no>/edit/', views.po_edit, name='edit'),
    path('<str:customer_order_no>/delete/', views.po_delete, name='delete'),
    path('<str:customer_order_no>/reserve/', views.reserve_doc_no, name='reserve_doc_no'),
    path('<str:customer_order_no>/check-match/', views.check_match, name='check_match'),
    path('<str:customer_order_no>/manual-match/', views.manual_match, name='manual_match'),
    path('<str:customer_order_no>/progress/', views.po_progress, name='progress'),
    path('<str:customer_order_no>/update-progress/', views.update_progress, name='update_progress'),
]

