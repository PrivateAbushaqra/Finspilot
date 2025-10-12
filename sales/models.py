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
        ('bank_transfer', _('Bank Transfer')),
        ('check', _('شيك')),
        ('installment', _('تقسيط')),
    ]

    invoice_number = models.CharField(_('رقم الفاتورة'), max_length=50, unique=True)
    date = models.DateField(_('Date'))
    customer = models.ForeignKey(CustomerSupplier, on_delete=models.PROTECT, 
                               verbose_name=_('Customer'), limit_choices_to={'type__in': ['customer', 'both']},
                               null=True, blank=True)
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT, 
                                verbose_name=_('Warehouse'), default=1)
    payment_type = models.CharField(_('نوع الدفع'), max_length=20, choices=PAYMENT_TYPES)
    cashbox = models.ForeignKey('cashboxes.Cashbox', on_delete=models.SET_NULL, 
                               verbose_name=_('الصندوق'), null=True, blank=True,
                               help_text=_('الصندوق المحصل منه النقد للمبيعات النقدية'))
    subtotal = models.DecimalField(_('المجموع الفرعي'), max_digits=15, decimal_places=3, default=0)
    tax_amount = models.DecimalField(_('مبلغ الضريبة'), max_digits=15, decimal_places=3, default=0)
    discount_amount = models.DecimalField(_('مبلغ الخصم'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('المبلغ الإجمالي'), max_digits=15, decimal_places=3, default=0)
    # new: whether tax is included/calculated for this invoice
    inclusive_tax = models.BooleanField(_('شامل ضريبة'), default=True)
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    # JoFotara integration fields
    jofotara_uuid = models.CharField(_('JoFotara UUID'), max_length=100, blank=True, null=True, 
                                   help_text=_('UUID returned from JoFotara API'))
    jofotara_sent_at = models.DateTimeField(_('Sent to JoFotara At'), blank=True, null=True,
                                          help_text=_('Date and time when invoice was sent to JoFotara'))

    class Meta:
        verbose_name = _('Sales Invoice')
        verbose_name_plural = _('Sales Invoices')
        ordering = ['-date', '-invoice_number']
        permissions = (
            ('can_toggle_invoice_tax', 'Can toggle invoice tax inclusion'),
            ('can_change_invoice_creator', 'Can change invoice creator'),
            ('can_send_to_jofotara', 'Can send invoices to JoFotara'),
        )

    def __str__(self):
        customer_name = self.customer.name if self.customer else 'عميل نقدي'
        return f"{self.invoice_number} - {customer_name}"

    def update_totals(self):
        """تحديث مجاميع الفاتورة بناءً على العناصر"""
        from decimal import Decimal
        
        items = self.items.all()
        subtotal = sum(item.quantity * item.unit_price for item in items)
        tax_amount = sum(item.tax_amount for item in items)
        total_amount = subtotal + tax_amount
        
        self.subtotal = subtotal.quantize(Decimal('0.001'))
        self.tax_amount = tax_amount.quantize(Decimal('0.001'))
        self.total_amount = total_amount.quantize(Decimal('0.001'))
        self.save(update_fields=['subtotal', 'tax_amount', 'total_amount'])


class SalesInvoiceItem(models.Model):
    """عنصر فاتورة المبيعات"""
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, 
                              verbose_name=_('الفاتورة'), related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, verbose_name=_('Product'))
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
    return_number = models.CharField(_('رقم مرتجع المبيعات'), max_length=50, unique=True)
    date = models.DateField(_('Date'))
    original_invoice = models.ForeignKey(SalesInvoice, on_delete=models.PROTECT, 
                                       verbose_name=_('الفاتورة الأصلية'))
    customer = models.ForeignKey(CustomerSupplier, on_delete=models.PROTECT, verbose_name=_('Customer'))
    subtotal = models.DecimalField(_('المجموع الفرعي'), max_digits=15, decimal_places=3, default=0)
    tax_amount = models.DecimalField(_('مبلغ الضريبة'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('المبلغ الإجمالي'), max_digits=15, decimal_places=3, default=0)
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Sales Return')
        verbose_name_plural = _('Sales Returns')
        ordering = ['-date', '-return_number']

    def __str__(self):
        return f"{self.return_number} - {self.customer.name}"


class SalesReturnItem(models.Model):
    """عنصر مردود المبيعات"""
    return_invoice = models.ForeignKey(SalesReturn, on_delete=models.CASCADE, 
                                     verbose_name=_('مردود المبيعات'), related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, verbose_name=_('Product'))
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


class SalesCreditNote(models.Model):
    """اشعار دائن لمبيعات"""
    note_number = models.CharField(_('رقم إشعار دائن'), max_length=50, unique=True)
    date = models.DateField(_('Date'))
    customer = models.ForeignKey(CustomerSupplier, on_delete=models.PROTECT, verbose_name=_('Customer'))
    subtotal = models.DecimalField(_('المجموع الفرعي'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('المبلغ الإجمالي'), max_digits=15, decimal_places=3, default=0)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    # JoFotara integration fields
    jofotara_uuid = models.CharField(_('JoFotara UUID'), max_length=100, blank=True, null=True, 
                                   help_text=_('UUID returned from JoFotara API'))
    jofotara_sent_at = models.DateTimeField(_('Sent to JoFotara At'), blank=True, null=True,
                                          help_text=_('Date and time when credit note was sent to JoFotara'))

    class Meta:
        verbose_name = _('اشعار دائن')
        verbose_name_plural = _('اشعارات دائن')
        ordering = ['-date', '-note_number']
        permissions = (
            ('can_send_to_jofotara', 'Can send credit notes to JoFotara'),
        )

    def save(self, *args, **kwargs):
        # الإجمالي يساوي المجموع الفرعي (بدون ضريبة)
        self.total_amount = self.subtotal
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.note_number} - {self.customer.name}"
