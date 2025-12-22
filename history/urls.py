from django.urls import path
from . import views

app_name = 'history'

urlpatterns = [
    path('', views.history, name='history'),
    path('movement/', views.history_movement, name='history_movement'),
    path('charge/', views.history_charge, name='history_charge'),
    path('charge/export.xlsx', views.history_charge_export, name='history_charge_export'),
    path('clf3/', views.history_clf3, name='history_clf3'),
    path('trend/', views.history_trend, name='history_trend'),
    path('trend/export.xlsx', views.history_trend_export, name='history_trend_export'),
    path('snapshot/manual/', views.manual_snapshot, name='manual_snapshot'),
    path('export.xlsx', views.export_excel, name='export_excel'),
]

