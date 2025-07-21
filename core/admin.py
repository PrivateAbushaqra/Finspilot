from django.contrib import admin
from .models import CompanySettings, DocumentSequence, AuditLog, SystemNotification


@admin.register(CompanySettings)
class CompanySettingsAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'currency', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(DocumentSequence)
class DocumentSequenceAdmin(admin.ModelAdmin):
    list_display = ['document_type', 'prefix', 'digits', 'current_number', 'updated_at']
    list_filter = ['document_type']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action_type', 'content_type', 'timestamp']
    list_filter = ['action_type', 'content_type', 'timestamp']
    readonly_fields = ['timestamp']
    search_fields = ['user__username', 'description']


@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'notification_type', 'user', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    readonly_fields = ['created_at']
    search_fields = ['title', 'message']
