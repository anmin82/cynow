from django.urls import path
from . import views

app_name = 'simulation'

urlpatterns = [
    path('', views.simulation_view, name='index'),
    path('api/calculate/', views.calculate_simulation, name='calculate'),
    path('api/cylinder-types/', views.get_cylinder_types, name='cylinder_types'),
]

