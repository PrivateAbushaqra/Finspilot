from django.urls import path
from . import views

app_name = 'journal'

urlpatterns = [
    # لوحة التحكم
    path('', views.journal_dashboard, name='dashboard'),
    
    # إدارة الحسابات
    path('accounts/', views.account_list, name='account_list'),
    path('accounts/create/', views.account_create, name='account_create'),
    path('accounts/<int:pk>/', views.account_detail, name='account_detail'),
    path('accounts/<int:pk>/edit/', views.account_edit, name='account_edit'),
    path('accounts/<int:pk>/delete/', views.account_delete, name='account_delete'),
    path('accounts/<int:pk>/ledger/', views.account_ledger, name='account_ledger'),
    
    # إدارة القيود المحاسبية
    path('entries/', views.journal_entry_list, name='entry_list'),
    path('entries/by-type/', views.journal_entries_by_type, name='entries_by_type'),
    path('entries/create/', views.journal_entry_create, name='entry_create'),
    path('entries/<int:pk>/', views.journal_entry_detail, name='entry_detail'),
    path('entries/<int:pk>/detail/', views.journal_entry_detail_with_lines, name='entry_detail_with_lines'),
    path('entries/<int:pk>/delete/', views.delete_journal_entry, name='entry_delete'),
        path('entries/<int:pk>/edit/', views.journal_entry_edit, name='entry_edit'),
    
    # التقارير
    path('trial-balance/', views.trial_balance, name='trial_balance'),
    
    # APIs
    path('api/accounts/', views.accounts_api, name='accounts_api'),
    path('api/accounts/<int:account_id>/balance/', views.get_account_balance, name='account_balance_api'),
]
