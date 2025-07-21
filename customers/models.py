from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomerSupplier(models.Model):
    """العملاء والموردون"""
    TYPES = [
        ('customer', _('عميل')),
        ('supplier', _('مورد')),
        ('both', _('عميل ومورد')),
    ]

    name = models.CharField(_('الاسم'), max_length=200)
    type = models.CharField(_('النوع'), max_length=20, choices=TYPES)
    email = models.EmailField(_('البريد الإلكتروني'), blank=True)
    phone = models.CharField(_('الهاتف'), max_length=50, blank=True)
    address = models.TextField(_('العنوان'), blank=True)
    tax_number = models.CharField(_('الرقم الضريبي'), max_length=50, blank=True)
    credit_limit = models.DecimalField(_('حد الائتمان'), max_digits=15, decimal_places=3, default=0)
    balance = models.DecimalField(_('الرصيد'), max_digits=15, decimal_places=3, default=0)
    is_active = models.BooleanField(_('نشط'), default=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('عميل/مورد')
        verbose_name_plural = _('العملاء والموردون')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

    @property
    def is_customer(self):
        return self.type in ['customer', 'both']

    @property
    def is_supplier(self):
        return self.type in ['supplier', 'both']

    @property
    def current_balance(self):
        """حساب الرصيد الحالي بناءً على المعاملات الفعلية"""
        try:
            from accounts.models import AccountTransaction
            from django.db.models import Sum
            
            transactions = AccountTransaction.objects.filter(customer_supplier=self)
            total_debit = transactions.filter(direction='debit').aggregate(
                total=Sum('amount'))['total'] or 0
            total_credit = transactions.filter(direction='credit').aggregate(
                total=Sum('amount'))['total'] or 0
            
            return total_debit - total_credit
        except ImportError:
            # في حالة عدم وجود نموذج الحسابات، استخدم الرصيد المحفوظ
            return self.balance
        except Exception:
            return self.balance
