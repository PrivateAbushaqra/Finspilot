from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserGroup, UserGroupMembership


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'user_type', 'is_active']
    list_filter = ['user_type', 'is_active', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('معلومات إضافية', {
            'fields': ('user_type', 'phone', 'department')
        }),
        ('الصلاحيات', {
            'fields': (
                'can_access_sales', 'can_access_purchases', 'can_access_inventory',
                'can_access_banks', 'can_access_reports', 'can_delete_invoices',
                'can_edit_dates', 'can_edit_invoice_numbers', 'cash_only',
                'credit_only', 'can_see_low_stock_alerts', 'can_access_pos', 'pos_only'
            )
        }),
        ('التواريخ', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UserGroup)
class UserGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UserGroupMembership)
class UserGroupMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'group', 'created_at']
    list_filter = ['group']
    readonly_fields = ['created_at']
