from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('sales/', views.sales_analytics, name='sales_analytics'),
    path('purchase/', views.purchase_analytics, name='purchase_analytics'),
    path('tax/', views.tax_analytics, name='tax_analytics'),
    path('cashflow/', views.cashflow_analytics, name='cashflow_analytics'),
    path('export/', views.export_analytics, name='export_analytics'),
]
