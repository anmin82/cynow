from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('daily/', views.daily_report, name='daily'),
    path('daily/arrival/', views.arrival_report, name='arrival'),
    path('weekly/', views.weekly_report, name='weekly'),
    path('monthly/', views.monthly_report, name='monthly'),
    path('weekly/export.xlsx', views.export_weekly_excel, name='export_weekly_excel'),
    path('monthly/export.xlsx', views.export_monthly_excel, name='export_monthly_excel'),
]

