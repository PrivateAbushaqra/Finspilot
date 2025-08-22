from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import Max


class CustomerSupplier(models.Model):
    """العملاء والموردون"""
    TYPES = [
        ('customer', _('عميل')),
        ('supplier', _('مورد')),
        ('both', _('عميل ومورد')),
    ]

    sequence_number = models.IntegerField(_('الرقم التسلسلي'), unique=True, null=True, blank=True)
    name = models.CharField(_('الاسم'), max_length=200)
    type = models.CharField(_('النوع'), max_length=20, choices=TYPES)
    email = models.EmailField(_('Email'), blank=True)
    phone = models.CharField(_('Phone'), max_length=50, blank=True)
    address = models.TextField(_('العنوان'), blank=True)
    city = models.CharField(_('المدينة'), max_length=100, blank=False)
    tax_number = models.CharField(_('الرقم الضريبي'), max_length=50, blank=True)
    credit_limit = models.DecimalField(_('حد الائتمان'), max_digits=15, decimal_places=3, default=0)
    balance = models.DecimalField(_('Balance'), max_digits=15, decimal_places=3, default=0)
    is_active = models.BooleanField(_('Active'), default=True)
    notes = models.TextField(_('Notes'), blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('عميل/مورد')
        verbose_name_plural = _('العملاء والموردون')
        ordering = ['sequence_number']

    def save(self, *args, **kwargs):
        if not self.sequence_number:
            self.sequence_number = self._get_next_sequence_number()
        super().save(*args, **kwargs)

    def _get_next_sequence_number(self):
        """الحصول على أول رقم تسلسلي متاح حسب النوع"""
        # تحديد نطاق الأرقام حسب النوع
        if self.type == 'customer':
            start_range = 10000
            end_range = 19999
        elif self.type == 'supplier':
            start_range = 20000
            end_range = 29999
        elif self.type == 'both':
            start_range = 30000
            end_range = 39999
        else:
            start_range = 10000
            end_range = 19999
        
        # البحث عن أول رقم متاح في النطاق المحدد
        existing_numbers = set(CustomerSupplier.objects.values_list('sequence_number', flat=True))
        
        for num in range(start_range, end_range + 1):
            if num not in existing_numbers:
                return num
        
        # في حالة نادرة جداً إذا امتلأت جميع الأرقام في النطاق
        max_num = CustomerSupplier.objects.filter(
            sequence_number__gte=start_range,
            sequence_number__lte=end_range
        ).aggregate(Max('sequence_number'))['sequence_number__max']
        return (max_num or start_range - 1) + 1

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
