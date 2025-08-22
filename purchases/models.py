from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from customers.models import CustomerSupplier

User = get_user_model()


class PurchaseInvoice(models.Model):
    """فاتورة المشتريات"""
    PAYMENT_TYPES = [
        ('cash', _('كاش')),
        ('credit', _('ذمم')),
    ]

    invoice_number = models.CharField(_('رقم الفاتورة'), max_length=50)
    supplier_invoice_number = models.CharField(_('رقم فاتورة المورد'), max_length=50)
    date = models.DateField(_('Date'))
    supplier = models.ForeignKey(CustomerSupplier, on_delete=models.PROTECT, 
                               verbose_name=_('المورد'), limit_choices_to={'type__in': ['supplier', 'both']})
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT, 
                                verbose_name=_('المستودع'), null=True, blank=True)
    payment_type = models.CharField(_('نوع الدفع'), max_length=20, choices=PAYMENT_TYPES)
    subtotal = models.DecimalField(_('المجموع الفرعي'), max_digits=15, decimal_places=3, default=0)
    tax_amount = models.DecimalField(_('مبلغ الضريبة'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('المبلغ الإجمالي'), max_digits=15, decimal_places=3, default=0)
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('فاتورة مشتريات')
        verbose_name_plural = _('فواتير المشتريات')
        ordering = ['-date', '-invoice_number']

    def __str__(self):
        return f"{self.supplier_invoice_number} - {self.supplier.name}"


class PurchaseInvoiceItem(models.Model):
    """عنصر فاتورة المشتريات"""
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, 
                              verbose_name=_('الفاتورة'), related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, verbose_name=_('المنتج'))
    quantity = models.DecimalField(_('الكمية'), max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(_('سعر الوحدة'), max_digits=15, decimal_places=3)
    tax_rate = models.DecimalField(_('نسبة الضريبة'), max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_('مبلغ الضريبة'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('المبلغ الإجمالي'), max_digits=15, decimal_places=3, default=0)

    class Meta:
        verbose_name = _('عنصر فاتورة المشتريات')
        verbose_name_plural = _('عناصر فواتير المشتريات')

    def __str__(self):
        return f"{self.invoice.supplier_invoice_number} - {self.product.name}"

    def save(self, *args, **kwargs):
        # حساب مبلغ الضريبة والمبلغ الإجمالي
        from decimal import Decimal, ROUND_HALF_UP
        
        subtotal = self.quantity * self.unit_price
        tax_amount = subtotal * (self.tax_rate / Decimal('100'))
        
        # تقريب إلى 3 خانات عشرية
        self.tax_amount = tax_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        self.total_amount = (subtotal + tax_amount).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        super().save(*args, **kwargs)


class PurchaseReturn(models.Model):
    """مردود مشتريات"""
    RETURN_TYPES = [
        ('full', _('مردود كامل')),
        ('partial', _('مردود جزئي')),
    ]
    
    RETURN_REASONS = [
        ('defective', _('منتج معيب')),
        ('wrong_item', _('صنف خاطئ')),
        ('excess', _('فائض عن الحاجة')),
        ('expired', _('منتهي الصلاحية')),
        ('damaged', _('تالف أثناء النقل')),
        ('other', _('أخرى')),
    ]

    return_number = models.CharField(_('رقم المردود'), max_length=50, unique=True)
    original_invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.PROTECT, 
                                       verbose_name=_('الفاتورة الأصلية'), related_name='returns')
    date = models.DateField(_('تاريخ المردود'))
    return_type = models.CharField(_('نوع المردود'), max_length=20, choices=RETURN_TYPES, default='partial')
    return_reason = models.CharField(_('سبب المردود'), max_length=20, choices=RETURN_REASONS)
    subtotal = models.DecimalField(_('المجموع الفرعي'), max_digits=15, decimal_places=3, default=0)
    tax_amount = models.DecimalField(_('مبلغ الضريبة'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('المبلغ الإجمالي'), max_digits=15, decimal_places=3, default=0)
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('مردود مشتريات')
        verbose_name_plural = _('مردودات المشتريات')
        ordering = ['-date', '-return_number']

    def __str__(self):
        return f"{self.return_number} - {self.original_invoice.supplier.name}"

    @property
    def supplier(self):
        return self.original_invoice.supplier


class PurchaseReturnItem(models.Model):
    """عنصر مردود المشتريات"""
    return_invoice = models.ForeignKey(PurchaseReturn, on_delete=models.CASCADE, 
                                     verbose_name=_('مردود المشتريات'), related_name='items')
    original_item = models.ForeignKey(PurchaseInvoiceItem, on_delete=models.PROTECT, 
                                    verbose_name=_('العنصر الأصلي'))
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, verbose_name=_('المنتج'))
    returned_quantity = models.DecimalField(_('الكمية المرتجعة'), max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(_('سعر الوحدة'), max_digits=15, decimal_places=3)
    tax_rate = models.DecimalField(_('نسبة الضريبة'), max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_('مبلغ الضريبة'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('المبلغ الإجمالي'), max_digits=15, decimal_places=3, default=0)

    class Meta:
        verbose_name = _('عنصر مردود مشتريات')
        verbose_name_plural = _('عناصر مردود المشتريات')

    def __str__(self):
        return f"{self.product.name} - {self.returned_quantity}"

    def clean(self):
        """التحقق من صحة الكمية المرتجعة"""
        from django.core.exceptions import ValidationError
        
        if self.returned_quantity > self.original_item.quantity:
            raise ValidationError(_('الكمية المرتجعة لا يمكن أن تكون أكبر من الكمية الأصلية'))
        
        # التحقق من المردودات السابقة
        previous_returns = PurchaseReturnItem.objects.filter(
            original_item=self.original_item
        ).exclude(pk=self.pk)
        
        total_returned = sum(item.returned_quantity for item in previous_returns)
        if total_returned + self.returned_quantity > self.original_item.quantity:
            raise ValidationError(_('إجمالي الكمية المرتجعة يتجاوز الكمية الأصلية'))

    def save(self, *args, **kwargs):
        # حساب المبالغ
        from decimal import Decimal, ROUND_HALF_UP
        
        subtotal = self.returned_quantity * self.unit_price
        tax_amount = subtotal * (self.tax_rate / Decimal('100'))
        
        # تقريب إلى 3 خانات عشرية
        self.tax_amount = tax_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        self.total_amount = (subtotal + tax_amount).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        
        self.full_clean()
        super().save(*args, **kwargs)
