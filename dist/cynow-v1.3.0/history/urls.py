from django.urls import path
from . import views

app_name = 'history'

urlpatterns = [
    path('', views.history, name='history'),
    path('snapshot/manual/', views.manual_snapshot, name='manual_snapshot'),
    path('export.xlsx', views.export_excel, name='export_excel'),
]

