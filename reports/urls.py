from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('customer-statement/', views.customer_statement, name='customer_statement'),
    path('sales-by-salesperson/', views.sales_by_salesperson, name='sales_by_salesperson'),
    path('trial-balance/', views.trial_balance, name='trial_balance'),
    path('balance-sheet/', views.balance_sheet, name='balance_sheet'),
    path('income-statement/', views.income_statement, name='income_statement'),
    path('cash-flow/', views.cash_flow, name='cash_flow'),
    path('financial-ratios/', views.financial_ratios, name='financial_ratios'),
    path('aging-report/', views.aging_report, name='aging_report'),
    path('inventory-report/', views.inventory_report, name='inventory_report'),
]
