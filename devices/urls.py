"""
devices 앱 URL 라우팅

Scale Gateway API
"""
from django.urls import path
from . import views

app_name = 'devices'

urlpatterns = [
    # Scale Gateway API
    path('scale-gateway/latest/', views.latest_weight, name='scale_gateway_latest'),
    path('scale-gateway/commit/', views.commit_weight, name='scale_gateway_commit'),
]





