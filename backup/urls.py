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
    path('restore-backup/', views.restore_backup, name='restore_backup'),
    path('restore-progress/', views.get_restore_progress, name='restore_progress'),
    path('download-backup/<str:filename>/', views.download_backup, name='download_backup'),
    path('delete-backup/<str:filename>/', views.delete_backup, name='delete_backup'),
    path('list-backups/', views.list_backups, name='list_backups'),
]
