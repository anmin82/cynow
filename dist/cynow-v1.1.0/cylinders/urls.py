from django.urls import path
from . import views

app_name = 'cylinders'

urlpatterns = [
    path('', views.cylinder_list, name='list'),
    path('<str:cylinder_no>/', views.cylinder_detail, name='detail'),
]

