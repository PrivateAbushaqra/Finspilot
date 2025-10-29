from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Account, JournalEntry, JournalLine


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'account_type', 'parent', 'balance', 'is_active']
    list_filter = ['account_type', 'is_active', 'created_at']
    search_fields = ['code', 'name', 'description']
    ordering = ['code']
    list_editable = ['is_active']
    
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('code', 'name', 'account_type', 'parent')
        }),
        (_('تفاصيل إضافية'), {
            'fields': ('description', 'is_active')
        }),
    )


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 2
    fields = ['account', 'debit', 'credit', 'line_description']


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['entry_number', 'entry_date', 'description', 'total_amount', 'created_by']
    list_filter = ['entry_date', 'created_at']
    search_fields = ['entry_number', 'description']
    ordering = ['-entry_date', '-created_at']
    readonly_fields = ['entry_number', 'created_at', 'updated_at']
    
    inlines = [JournalLineInline]
    
    fieldsets = (
        (_('معلومات القيد'), {
            'fields': ('entry_number', 'entry_date', 'reference_id')
        }),
        (_('التفاصيل'), {
            'fields': ('description', 'total_amount', 'created_by')
        }),
        (_('معلومات النظام'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(JournalLine)
class JournalLineAdmin(admin.ModelAdmin):
    list_display = ['journal_entry', 'account', 'debit', 'credit', 'line_description']
    list_filter = ['account__account_type', 'created_at']
    search_fields = ['journal_entry__entry_number', 'account__name', 'line_description']
    ordering = ['-created_at']
