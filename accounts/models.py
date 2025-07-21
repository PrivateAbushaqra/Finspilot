from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from customers.models import CustomerSupplier
from decimal import Decimal

User = get_user_model()


class AccountTransaction(models.Model):
    """حركات الحسابات المالية للعملاء والموردين"""
    TRANSACTION_TYPES = [
        ('sales_invoice', _('فاتورة مبيعات')),
        ('purchase_invoice', _('فاتورة مشتريات')),
        ('sales_return', _('مردود مبيعات')),
        ('purchase_return', _('مردود مشتريات')),
        ('payment', _('دفعة')),
        ('adjustment', _('تسوية')),
    ]
    
    DIRECTION_TYPES = [
        ('debit', _('مدين')),
        ('credit', _('دائن')),
    ]

    transaction_number = models.CharField(_('رقم الحركة'), max_length=50, unique=True)
    date = models.DateField(_('التاريخ'))
    customer_supplier = models.ForeignKey(CustomerSupplier, on_delete=models.PROTECT, 
                                        verbose_name=_('العميل/المورد'), related_name='transactions')
    transaction_type = models.CharField(_('نوع الحركة'), max_length=20, choices=TRANSACTION_TYPES)
    direction = models.CharField(_('الاتجاه'), max_length=10, choices=DIRECTION_TYPES)
    amount = models.DecimalField(_('المبلغ'), max_digits=15, decimal_places=3)
    
    # ربط بالمستندات الأصلية
    reference_type = models.CharField(_('نوع المرجع'), max_length=20, blank=True)
    reference_id = models.PositiveIntegerField(_('معرف المرجع'), blank=True, null=True)
    
    description = models.TextField(_('الوصف'), blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    # الرصيد بعد الحركة
    balance_after = models.DecimalField(_('الرصيد بعد الحركة'), max_digits=15, decimal_places=3, default=0)
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('أنشئ بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('حركة حساب')
        verbose_name_plural = _('حركات الحسابات')
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['customer_supplier', 'date']),
            models.Index(fields=['transaction_type', 'date']),
            models.Index(fields=['reference_type', 'reference_id']),
        ]

    def __str__(self):
        return f"{self.transaction_number} - {self.customer_supplier.name} - {self.amount}"

    def save(self, *args, **kwargs):
        # توليد رقم الحركة إذا لم يكن موجوداً
        if not self.transaction_number:
            self.transaction_number = self.generate_transaction_number()
        
        # حساب الرصيد بعد الحركة
        if not self.balance_after:
            self.balance_after = self.calculate_balance_after()
        
        super().save(*args, **kwargs)
        
        # تحديث رصيد العميل/المورد
        self.update_customer_supplier_balance()

    def generate_transaction_number(self):
        """توليد رقم الحركة"""
        from datetime import datetime
        import uuid
        
        prefix = 'TXN'
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_part = str(uuid.uuid4())[:8].upper()
        
        return f"{prefix}-{timestamp}-{random_part}"

    def calculate_balance_after(self):
        """حساب الرصيد بعد الحركة"""
        current_balance = self.customer_supplier.balance
        
        if self.direction == 'debit':
            # المدين يزيد الرصيد (للعملاء = دين عليهم، للموردين = دين لهم)
            return current_balance + self.amount
        else:
            # الدائن يقلل الرصيد (للعملاء = دفع منهم، للموردين = دفع لهم)
            return current_balance - self.amount

    def update_customer_supplier_balance(self):
        """تحديث رصيد العميل/المورد"""
        # حساب الرصيد الجديد بناءً على جميع الحركات
        transactions = AccountTransaction.objects.filter(
            customer_supplier=self.customer_supplier
        ).order_by('date', 'created_at')
        
        new_balance = Decimal('0')
        for transaction in transactions:
            if transaction.direction == 'debit':
                new_balance += transaction.amount
            else:
                new_balance -= transaction.amount
        
        # تحديث رصيد العميل/المورد
        self.customer_supplier.balance = new_balance
        self.customer_supplier.save()

    @staticmethod
    def create_transaction(customer_supplier, transaction_type, direction, amount, 
                          reference_type=None, reference_id=None, description='', 
                          notes='', user=None, date=None):
        """إنشاء حركة حساب جديدة"""
        from datetime import date as today_date
        
        if date is None:
            date = today_date.today()
        
        transaction = AccountTransaction.objects.create(
            date=date,
            customer_supplier=customer_supplier,
            transaction_type=transaction_type,
            direction=direction,
            amount=amount,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
            notes=notes,
            created_by=user
        )
        
        return transaction
