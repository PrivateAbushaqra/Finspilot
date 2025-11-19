from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import Max


class CustomerSupplier(models.Model):
    """العملاء والموردون"""
    TYPES = [
        ('customer', _('Customer')),
        ('supplier', _('Supplier')),
        ('both', _('Customer and Supplier')),
    ]

    sequence_number = models.IntegerField(_('Sequence Number'), unique=True, null=True, blank=True)
    name = models.CharField(_('Name'), max_length=200)
    type = models.CharField(_('Type'), max_length=20, choices=TYPES)
    email = models.EmailField(_('Email'), blank=True)
    phone = models.CharField(_('Phone'), max_length=50, blank=True)
    address = models.TextField(_('Address'), blank=True)
    city = models.CharField(_('City'), max_length=100, blank=False)
    tax_number = models.CharField(_('Tax Number'), max_length=50, blank=True)
    credit_limit = models.DecimalField(_('Credit Limit'), max_digits=15, decimal_places=3, default=0)
    balance = models.DecimalField(_('Balance'), max_digits=15, decimal_places=3, default=0)
    is_active = models.BooleanField(_('Active'), default=True)
    notes = models.TextField(_('Notes'), blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Customer/Supplier')
        verbose_name_plural = _('Customers and Suppliers')
        ordering = ['sequence_number']
        default_permissions = []  # No default permissions
        permissions = [
            ('can_view_customers', 'Can View Customers'),
            ('can_add_customers', 'Can Add Customers'),
            ('can_edit_customers', 'Can Edit Customers'),
            ('can_delete_customers', 'Can Delete Customers'),
            ('can_view_suppliers', 'Can View Suppliers'),
            ('can_add_suppliers', 'Can Add Suppliers'),
            ('can_edit_suppliers', 'Can Edit Suppliers'),
            ('can_delete_suppliers', 'Can Delete Suppliers'),
        ]

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
        """حساب الرصيد الحالي - يتم تحديثه تلقائياً من AccountTransaction.save()"""
        # الرصيد يتم تحديثه تلقائياً عند حفظ أي معاملة
        # في AccountTransaction.update_customer_supplier_balance()
        # لذلك نرجع self.balance مباشرة الذي يحتوي على الرصيد المحدث
        return self.balance
    
    def sync_balance(self):
        """مزامنة رصيد العميل/المورد مع المعاملات الفعلية"""
        from decimal import Decimal
        from django.db.models import Sum
        from django.apps import apps
        
        AccountTransaction = apps.get_model('accounts', 'AccountTransaction')
        
        # حساب إجمالي المدينات والدائنات من جميع المعاملات
        debits = AccountTransaction.objects.filter(
            customer_supplier=self,
            direction='debit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        credits = AccountTransaction.objects.filter(
            customer_supplier=self,
            direction='credit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # حساب الرصيد الجديد: المدينات - الدائنات (الرصيد الأولي = 0)
        new_balance = debits - credits
        
        # تحديث الرصيد إذا كان مختلفاً
        if self.balance != new_balance:
            old_balance = self.balance
            self.balance = new_balance
            self.save(update_fields=['balance'])
            
            # تسجيل في سجل الأنشطة
            from core.models import AuditLog
            from django.contrib.auth import get_user_model
            User = get_user_model()
            system_user = User.objects.filter(username='super').first() or User.objects.first()
            if system_user:
                AuditLog.objects.create(
                    user=system_user,
                    action_type='update',
                    content_type='customer_supplier',
                    object_id=self.id,
                    description=f'إصلاح رصيد {self.name}: من {old_balance} إلى {new_balance} (مزامنة مع المعاملات)',
                    ip_address=None
                )
            
            print(f"🔧 تم إصلاح رصيد {self.name}: {old_balance} → {new_balance}")
        
        return new_balance

    def check_balance_integrity(self):
        """فحص سلامة الرصيد وإصلاح أي عدم تطابق"""
        from decimal import Decimal
        from django.db.models import Sum
        from django.apps import apps
        
        AccountTransaction = apps.get_model('accounts', 'AccountTransaction')
        
        # حساب الرصيد من المعاملات
        debits = AccountTransaction.objects.filter(
            customer_supplier=self,
            direction='debit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        credits = AccountTransaction.objects.filter(
            customer_supplier=self,
            direction='credit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        calculated_balance = debits - credits
        
        # فحص التطابق
        if self.balance != calculated_balance:
            print(f"⚠️ عدم تطابق في رصيد {self.name}: محفوظ={self.balance}, محسوب={calculated_balance}")
            return False, calculated_balance
        
        return True, self.balance
