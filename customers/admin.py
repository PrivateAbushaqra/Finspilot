from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import CustomerSupplier


@admin.register(CustomerSupplier)
class CustomerSupplierAdmin(admin.ModelAdmin):
    list_display = ['sequence_number', 'name', 'type', 'balance', 'is_active', 'created_at']
    list_filter = ['type', 'is_active', 'city']
    search_fields = ['name', 'email', 'phone', 'sequence_number']
    ordering = ['sequence_number']

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('sequence_number', 'name', 'type', 'email', 'phone', 'address', 'city')
        }),
        (_('Financial Information'), {
            'fields': ('tax_number', 'credit_limit', 'balance')
        }),
        (_('Status'), {
            'fields': ('is_active', 'notes')
        }),
    )

    readonly_fields = ['balance']  # جعل الرصيد غير قابل للتعديل يدوياً

    def get_readonly_fields(self, request, obj=None):
        """جعل الرصيد غير قابل للتعديل دائماً"""
        readonly_fields = list(self.readonly_fields)
        if obj:  # إذا كان هناك كائن موجود
            readonly_fields.append('balance')
        return readonly_fields

    def save_model(self, request, obj, form, change):
        """منع حفظ التعديلات على الرصيد"""
        if change and 'balance' in form.changed_data:
            # إذا تم محاولة تعديل الرصيد، أعد حسابه من المعاملات
            obj.sync_balance()
            self.message_user(
                request,
                _("لا يمكن تعديل الرصيد يدوياً. تم إعادة حساب الرصيد من المعاملات."),
                level='warning'
            )
        super().save_model(request, obj, form, change)