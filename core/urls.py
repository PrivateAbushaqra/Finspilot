from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('notifications/', views.NotificationListView.as_view(), name='notifications'),
    path('notifications/mark-read/<int:pk>/', views.mark_notification_read, name='mark_notification_read'),
    path('audit-log/', views.AuditLogListView.as_view(), name='audit_log'),
    path('reports/tax/', views.TaxReportView.as_view(), name='tax_report'),
    path('reports/profit-loss/', views.ProfitLossReportView.as_view(), name='profit_loss_report'),
    path('sync-balances/', views.sync_balances_view, name='sync_balances'),
    path('backup-export/', views.backup_export_view, name='backup_export'),
    path('export-backup-data/', views.export_backup_data, name='export_backup_data'),
    path('import-backup-data/', views.import_backup_data, name='import_backup_data'),
    path('api/extend-session/', views.extend_session_api, name='extend_session_api'),
]
