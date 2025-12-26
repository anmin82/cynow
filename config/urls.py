"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Public (anonymous access allowed)
    path('', include('dashboard.urls')),
    path('cylinders/', include('cylinders.urls')),
    path('alerts/', include('alerts.urls')),
    path('reports/', include('reports.urls')),
    path('history/', include('history.urls')),
    path('orders/', include('orders.urls')),  # 🆕 수주 관리
    path('inventory/', include('inventory.urls')),  # 재고 관리
    
    # Authentication
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Login required (write operations)
    path('plans/', include('plans.urls')),
    path('simulation/', include('simulation.urls')),
    path('products/', include('products.urls')),  # 제품코드 관리
    path('voucher/', include('voucher.urls')),  # 전표/견적서 생성
    
    # Policy management (staff only)
    path('core/', include('core.urls')),
    
    # Scale Gateway API (내부망, POC는 인증 생략, 추후 인증 적용 권장)
    path('api/', include('devices.urls')),
]
