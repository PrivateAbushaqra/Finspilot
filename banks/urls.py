from django.urls import path
from . import views

app_name = 'banks'

urlpatterns = [
    path('accounts/', views.BankAccountListView.as_view(), name='account_list'),
    path('accounts/add/', views.BankAccountCreateView.as_view(), name='account_add'),
    path('accounts/view/<int:pk>/', views.BankAccountDetailView.as_view(), name='account_detail'),
    path('accounts/edit/<int:pk>/', views.BankAccountUpdateView.as_view(), name='account_edit'),
    path('accounts/delete/<int:pk>/', views.BankAccountDeleteView.as_view(), name='account_delete'),
    path('accounts/superadmin-delete/<int:pk>/', views.BankAccountSuperAdminDeleteView.as_view(), name='account_superadmin_delete'),
    path('accounts/<int:pk>/transactions/', views.BankAccountTransactionsView.as_view(), name='account_transactions'),
    path('accounts/<int:pk>/export-xlsx/', views.account_export_xlsx, name='account_export_xlsx'),
    path('accounts/force-delete/<int:pk>/', views.BankAccountForceDeleteView.as_view(), name='account_force_delete'),
    path('accounts/toggle-status/<int:pk>/', views.BankAccountToggleStatusView.as_view(), name='account_toggle_status'),
    path('accounts/clear-transactions/<int:pk>/', views.ClearAccountTransactionsView.as_view(), name='clear_account_transactions'),
    path('transactions/delete/<int:pk>/', views.BankTransactionDeleteView.as_view(), name='transaction_delete'),
    path('transfers/', views.BankTransferListView.as_view(), name='transfer_list'),
    path('transfers/add/', views.BankTransferCreateView.as_view(), name='transfer_add'),
    path('transfers/view/<int:pk>/', views.BankTransferDetailView.as_view(), name='transfer_detail'),
    path('transfers/edit/<int:pk>/', views.BankTransferUpdateView.as_view(), name='transfer_edit'),
    path('transfers/delete/<int:pk>/', views.BankTransferDeleteView.as_view(), name='transfer_delete'),
    path('transfers/bank-cashbox/add/', views.BankCashboxTransferCreateView.as_view(), name='bank_cashbox_transfer_add'),
    path('transfers/bank-cashbox/view/<int:pk>/', views.CashboxTransferDetailView.as_view(), name='cashbox_transfer_detail'),
    path('transfers/bank-cashbox/edit/<int:pk>/', views.CashboxTransferUpdateView.as_view(), name='cashbox_transfer_edit'),
    path('transfers/bank-cashbox/delete/<int:pk>/', views.CashboxTransferDeleteView.as_view(), name='cashbox_transfer_delete'),
    # Bank Reconciliation URLs
    path('reconciliations/', views.BankReconciliationListView.as_view(), name='reconciliation_list'),
    path('reconciliations/add/', views.BankReconciliationCreateView.as_view(), name='reconciliation_add'),
    path('reconciliations/view/<int:pk>/', views.BankReconciliationDetailView.as_view(), name='reconciliation_detail'),
    path('reconciliations/edit/<int:pk>/', views.BankReconciliationUpdateView.as_view(), name='reconciliation_edit'),
    # Bank Statement URLs
    path('statements/', views.BankStatementListView.as_view(), name='statement_list'),
    path('statements/add/', views.BankStatementCreateView.as_view(), name='statement_add'),
    path('statements/edit/<int:pk>/', views.BankStatementUpdateView.as_view(), name='statement_edit'),
]
