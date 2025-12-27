from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('detail/', views.detail, name='detail'),
    path('toggle-hide/', views.toggle_hide_cylinder_type, name='toggle_hide'),
    path('api/move-report-cylinders/', views.api_move_report_cylinders, name='api_move_report_cylinders'),
]

