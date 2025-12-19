from django.urls import path
from . import views

app_name = 'plans'

urlpatterns = [
    path('forecast/', views.forecast, name='forecast'),
    path('forecast/save/', views.forecast_save, name='forecast_save'),
    path('scheduled/', views.scheduled, name='scheduled'),
    path('scheduled/save/', views.scheduled_save, name='scheduled_save'),
]

