from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.index, name='index'),
    path('cylinder/', views.cylinder_inventory, name='cylinder'),
    path('product/', views.product_inventory, name='product'),
    path('snapshot/', views.snapshot_list, name='snapshot'),
]

