from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from customers.models import CustomerSupplier

User = get_user_model()


class SalesInvoice(models.Model):
    """فاتورة المبيعات"""
    PAYMENT_TYPES = [
        ('cash', _('نقدي')),
        ('credit', _('ذمم (آجل)')),
        ('bank_transfer', _('تحويل بنكي')),
        ('check', _('شيك')),
        ('installment', _('تقسيط')),
    ]

    invoice_number = models.CharField(_('رقم الفاتورة'), max_length=50, unique=True)
    date = models.DateField(_('التاريخ'))
    customer = models.ForeignKey(CustomerSupplier, on_delete=models.PROTECT, 
                               verbose_name=_('العميل'), limit_choices_to={'type__in': ['customer', 'both']},
                               null=True, blank=True)
    payment_type = models.CharField(_('نوع الدفع'), max_length=20, choices=PAYMENT_TYPES)
    subtotal = models.DecimalField(_('المجموع الفرعي'), max_digits=15, decimal_places=3, default=0)
    tax_amount = models.DecimalField(_('مبلغ الضريبة'), max_digits=15, decimal_places=3, default=0)
    discount_amount = models.DecimalField(_('مبلغ الخصم'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('المبلغ الإجمالي'), max_digits=15, decimal_places=3, default=0)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('أنشئ بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('فاتورة مبيعات')
        verbose_name_plural = _('فواتير المبيعات')
        ordering = ['-date', '-invoice_number']

    def __str__(self):
        customer_name = self.customer.name if self.customer else 'عميل نقدي'
        return f"{self.invoice_number} - {customer_name}"


class SalesInvoiceItem(models.Model):
    """عنصر فاتورة المبيعات"""
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, 
                              verbose_name=_('الفاتورة'), related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, verbose_name=_('المنتج'))
    quantity = models.DecimalField(_('الكمية'), max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(_('سعر الوحدة'), max_digits=15, decimal_places=3)
    tax_rate = models.DecimalField(_('نسبة الضريبة'), max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_('مبلغ الضريبة'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('المبلغ الإجمالي'), max_digits=15, decimal_places=3, default=0)

    class Meta:
        verbose_name = _('عنصر فاتورة المبيعات')
        verbose_name_plural = _('عناصر فواتير المبيعات')

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.product.name}"

    def save(self, *args, **kwargs):
        # حساب مبلغ الضريبة والمبلغ الإجمالي
        from decimal import Decimal, ROUND_HALF_UP
        
        subtotal = self.quantity * self.unit_price
        tax_amount = subtotal * (self.tax_rate / Decimal('100'))
        
        # تقريب إلى 3 خانات عشرية
        self.tax_amount = tax_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        self.total_amount = (subtotal + tax_amount).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        super().save(*args, **kwargs)


class SalesReturn(models.Model):
    """مردود المبيعات"""
    return_number = models.CharField(_('رقم المردود'), max_length=50, unique=True)
    date = models.DateField(_('التاريخ'))
    original_invoice = models.ForeignKey(SalesInvoice, on_delete=models.PROTECT, 
                                       verbose_name=_('الفاتورة الأصلية'))
    customer = models.ForeignKey(CustomerSupplier, on_delete=models.PROTECT, verbose_name=_('العميل'))
    subtotal = models.DecimalField(_('المجموع الفرعي'), max_digits=15, decimal_places=3, default=0)
    tax_amount = models.DecimalField(_('مبلغ الضريبة'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('المبلغ الإجمالي'), max_digits=15, decimal_places=3, default=0)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('أنشئ بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('مردود مبيعات')
        verbose_name_plural = _('مردود المبيعات')
        ordering = ['-date', '-return_number']

    def __str__(self):
        return f"{self.return_number} - {self.customer.name}"


class SalesReturnItem(models.Model):
    """عنصر مردود المبيعات"""
    return_invoice = models.ForeignKey(SalesReturn, on_delete=models.CASCADE, 
                                     verbose_name=_('مردود المبيعات'), related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, verbose_name=_('المنتج'))
    quantity = models.DecimalField(_('الكمية'), max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(_('سعر الوحدة'), max_digits=15, decimal_places=3)
    tax_rate = models.DecimalField(_('نسبة الضريبة'), max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_('مبلغ الضريبة'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('المبلغ الإجمالي'), max_digits=15, decimal_places=3, default=0)

    class Meta:
        verbose_name = _('عنصر مردود المبيعات')
        verbose_name_plural = _('عناصر مردود المبيعات')

    def __str__(self):
        return f"{self.return_invoice.return_number} - {self.product.name}"

    def save(self, *args, **kwargs):
        # حساب مبلغ الضريبة والمبلغ الإجمالي
        from decimal import Decimal, ROUND_HALF_UP
        
        subtotal = self.quantity * self.unit_price
        tax_amount = subtotal * (self.tax_rate / Decimal('100'))
        
        # تقريب إلى 3 خانات عشرية
        self.tax_amount = tax_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        self.total_amount = (subtotal + tax_amount).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        super().save(*args, **kwargs)
