from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('customer-statement/', views.customer_statement, name='customer_statement'),
    path('sales-by-salesperson/', views.sales_by_salesperson, name='sales_by_salesperson'),
]
