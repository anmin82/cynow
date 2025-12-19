from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('detail/', views.detail, name='detail'),
    path('toggle-hide/', views.toggle_hide_cylinder_type, name='toggle_hide'),
]

