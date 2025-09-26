from django.contrib import admin
from .models import ProvisionType, Provision, ProvisionEntry


@admin.register(ProvisionType)
class ProvisionTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']


@admin.register(Provision)
class ProvisionAdmin(admin.ModelAdmin):
    list_display = ['name', 'provision_type', 'related_account', 'amount', 'fiscal_year', 'is_approved', 'is_active']
    list_filter = ['provision_type', 'fiscal_year', 'is_approved', 'is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['accumulated_amount', 'created_at', 'updated_at']


@admin.register(ProvisionEntry)
class ProvisionEntryAdmin(admin.ModelAdmin):
    list_display = ['provision', 'date', 'amount', 'created_by']
    list_filter = ['date', 'provision__provision_type']
    search_fields = ['provision__name', 'description']
