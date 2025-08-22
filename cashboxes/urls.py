from django.urls import path
from . import views

app_name = 'cashboxes'

urlpatterns = [
    # الصناديق
    path('', views.cashbox_list, name='cashbox_list'),
    path('create/', views.cashbox_create, name='cashbox_create'),
    path('<int:cashbox_id>/', views.cashbox_detail, name='cashbox_detail'),
    path('<int:cashbox_id>/edit/', views.cashbox_edit, name='cashbox_edit'),
    path('<int:cashbox_id>/delete/', views.cashbox_delete, name='cashbox_delete'),
    path('<int:cashbox_id>/clear-transactions/', views.ClearCashboxTransactionsView.as_view(), name='clear_transactions'),
    
    # التحويلات
    path('transfers/', views.transfer_list, name='transfer_list'),
    path('transfers/create/', views.transfer_create, name='transfer_create'),
    path('transfers/<int:transfer_id>/', views.transfer_detail, name='transfer_detail'),
    path('transfers/<int:transfer_id>/delete/', views.CashboxTransferDeleteView.as_view(), name='transfer_delete'),
    
    # المعاملات
    path('transactions/<int:transaction_id>/delete/', views.CashboxTransactionDeleteView.as_view(), name='transaction_delete'),
    
    # Ajax APIs
    path('api/cashbox/<int:cashbox_id>/balance/', views.get_cashbox_balance, name='get_cashbox_balance'),
    path('api/bank/<int:bank_id>/balance/', views.get_bank_balance, name='get_bank_balance'),
]
