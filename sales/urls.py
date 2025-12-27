from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path("", views.index, name="index"),
    path("statement/", views.transaction_statement, name="statement"),
    path("shipping-instruction/", views.shipping_instruction, name="shipping_instruction"),
    path("summary/", views.sales_summary, name="summary"),
]



