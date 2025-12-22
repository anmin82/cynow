from django.urls import path
from . import views

app_name = 'cylinders'

urlpatterns = [
    path('', views.cylinder_list, name='list'),
    path('search/', views.smart_search, name='smart_search'),
    path('search/autocomplete/', views.search_autocomplete, name='search_autocomplete'),
    path('scenario/<str:scenario_key>/', views.apply_scenario, name='apply_scenario'),
    path('export/excel/', views.cylinder_export_excel, name='export_excel'),
    path('export/qr-pdf/', views.cylinder_export_qr_pdf, name='export_qr_pdf'),
    path('<str:cylinder_no>/', views.cylinder_detail, name='detail'),
    path('<str:cylinder_no>/ship-history/', views.cylinder_ship_history, name='ship_history'),
    path('<str:cylinder_no>/memo/', views.memo_create, name='memo_create'),
    path('<str:cylinder_no>/memo/<int:memo_id>/reply/', views.memo_reply, name='memo_reply'),
    path('<str:cylinder_no>/memo/<int:memo_id>/edit/', views.memo_edit, name='memo_edit'),
    path('<str:cylinder_no>/memo/<int:memo_id>/delete/', views.memo_delete, name='memo_delete'),
]

