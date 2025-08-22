from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import PaymentVoucher  # , PaymentVoucherItem


# PaymentVoucherItemInline سيتم إضافته لاحقاً
# class PaymentVoucherItemInline(admin.TabularInline):
#     model = PaymentVoucherItem
#     extra = 0
#     fields = ['description', 'amount', 'account']


@admin.register(PaymentVoucher)
class PaymentVoucherAdmin(admin.ModelAdmin):
    list_display = [
        'voucher_number', 'date', 'beneficiary_display', 'voucher_type',
        'payment_type', 'amount', 'is_reversed', 'created_by'
    ]
    list_filter = [
        'voucher_type', 'payment_type', 'is_reversed', 'date',
        'created_at'
    ]
    search_fields = [
        'voucher_number', 'supplier__name', 'beneficiary_name',
        'description'
    ]
    readonly_fields = [
        'voucher_number', 'created_by', 'created_at', 'updated_at',
        'reversed_by', 'reversed_at'
    ]
    # inlines = [PaymentVoucherItemInline]  # سيتم إضافته لاحقاً
    
    fieldsets = (
        (_('معلومات أساسية'), {
            'fields': ('voucher_number', 'date', 'voucher_type', 'payment_type', 'amount')
        }),
        (_('المستفيد'), {
            'fields': ('supplier', 'beneficiary_name')
        }),
        (_('Description'), {
            'fields': ('description', 'notes')
        }),
        (_('تفاصيل الدفع'), {
            'fields': ('cashbox', 'bank', 'bank_reference'),
            'classes': ('collapse',)
        }),
        (_('تفاصيل الشيك'), {
            'fields': ('check_number', 'check_date', 'check_due_date', 'check_bank_name', 'check_status'),
            'classes': ('collapse',)
        }),
        (_('معلومات النظام'), {
            'fields': ('created_by', 'created_at', 'updated_at', 'is_active'),
            'classes': ('collapse',)
        }),
        (_('معلومات العكس'), {
            'fields': ('is_reversed', 'reversed_by', 'reversed_at', 'reversal_reason'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # عند الإنشاء
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# PaymentVoucherItem Admin سيتم إضافته لاحقاً
# @admin.register(PaymentVoucherItem)
# class PaymentVoucherItemAdmin(admin.ModelAdmin):
#     list_display = ['voucher', 'description', 'amount', 'account']
#     list_filter = ['voucher__voucher_type', 'account']
#     search_fields = ['voucher__voucher_number', 'description']
