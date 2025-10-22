from django.urls import path
from . import views

app_name = 'backup'

urlpatterns = [
    path('', views.BackupRestoreView.as_view(), name='backup_restore'),
    path('advanced/', views.BackupRestoreView.as_view(), name='backup_restore_advanced'),
    path('create-backup/', views.create_backup, name='create_backup'),
    path('backup-progress/', views.get_backup_progress, name='backup_progress'),
    path('backup-tables/', views.get_backup_tables, name='backup_tables'),
    path('clear-cache/', views.clear_backup_cache, name='clear_backup_cache'),
    path('deletable-tables/', views.get_deletable_tables, name='deletable_tables'),
    path('delete-tables/', views.delete_selected_tables, name='delete_tables'),
    path('restore-backup/', views.restore_backup, name='restore_backup'),
    path('restore-progress/', views.get_restore_progress, name='restore_progress'),
    path('download-backup/<str:filename>/', views.download_backup, name='download_backup'),
    path('delete-backup/<str:filename>/', views.delete_backup, name='delete_backup'),
    path('list-backups/', views.list_backups, name='list_backups'),
    path('clear-all-data/', views.clear_all_data, name='clear_all_data'),
    path('clear-progress/', views.get_clear_progress, name='clear_progress'),
    path('create-basic-accounts/', views.create_basic_accounts_view, name='create_basic_accounts'),
]
