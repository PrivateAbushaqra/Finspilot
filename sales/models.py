from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from customers.models import CustomerSupplier

User = get_user_model()


class SalesInvoice(models.Model):
    """فاتورة المبيعات"""
    PAYMENT_TYPES = [
        ('cash', _('Cash')),
        ('credit', _('Credit')),
        ('bank_transfer', _('Bank Transfer')),
        ('check', _('Check')),
        ('installment', _('Installment')),
    ]

    invoice_number = models.CharField(_('Invoice Number'), max_length=50, unique=True)
    date = models.DateField(_('Date'))
    customer = models.ForeignKey(CustomerSupplier, on_delete=models.PROTECT, 
                               verbose_name=_('Customer'), limit_choices_to={'type__in': ['customer', 'both']},
                               null=True, blank=True)
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT, 
                                verbose_name=_('Warehouse'), default=1)
    payment_type = models.CharField(_('Payment Type'), max_length=20, choices=PAYMENT_TYPES)
    cashbox = models.ForeignKey('cashboxes.Cashbox', on_delete=models.SET_NULL, 
                               verbose_name=_('Cashbox'), null=True, blank=True,
                               help_text=_('Cashbox from which cash is collected for cash sales'))
    subtotal = models.DecimalField(_('Subtotal'), max_digits=15, decimal_places=3, default=0)
    tax_amount = models.DecimalField(_('Tax Amount'), max_digits=15, decimal_places=3, default=0)
    discount_amount = models.DecimalField(_('Discount Amount'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('Total Amount'), max_digits=15, decimal_places=3, default=0)
    # new: whether tax is included/calculated for this invoice
    inclusive_tax = models.BooleanField(_('Inclusive Tax'), default=True)
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    # JoFotara integration fields
    jofotara_uuid = models.CharField(_('JoFotara UUID'), max_length=100, blank=True, null=True, 
                                   help_text=_('UUID returned from JoFotara API'))
    jofotara_sent_at = models.DateTimeField(_('Sent to JoFotara At'), blank=True, null=True,
                                          help_text=_('Date and time when invoice was sent to JoFotara'))
    jofotara_verification_url = models.URLField(_('JoFotara Verification URL'), blank=True, null=True,
                                              help_text=_('URL to verify invoice on JoFotara portal'))

    class Meta:
        verbose_name = _('Sales Invoice')
        verbose_name_plural = _('Sales Invoices')
        ordering = ['-date', '-invoice_number']
        default_permissions = []  # No default permissions
        permissions = [
            ('can_view_sales', 'Can View Sales'),
            ('can_add_sales', 'Can Add Sales'),
            ('can_edit_sales', 'Can Edit Sales'),
            ('can_delete_sales', 'Can Delete Sales'),
        ]

    def __str__(self):
        customer_name = self.customer.name if self.customer else 'عميل نقدي'
        return f"{self.invoice_number} - {customer_name}"

    def update_totals(self):
        """تحديث مجاميع الفاتورة بناءً على العناصر"""
        from decimal import Decimal
        
        items = self.items.all()
        if items.exists():
            subtotal = sum(item.quantity * item.unit_price for item in items)
            tax_amount = sum(item.tax_amount for item in items)
        else:
            subtotal = Decimal('0')
            tax_amount = Decimal('0')
        # خصم المبيعات (إن وجد)
        discount = getattr(self, 'discount_amount', Decimal('0')) or Decimal('0')

        # إجمالي الفاتورة = subtotal + tax - discount
        total_amount = Decimal(subtotal) + Decimal(tax_amount) - Decimal(discount)

        # تأكد من عدم أن يكون الإجمالي سالباً
        if total_amount < 0:
            total_amount = Decimal('0')

        self.subtotal = Decimal(subtotal).quantize(Decimal('0.001'))
        self.tax_amount = Decimal(tax_amount).quantize(Decimal('0.001'))
        self.discount_amount = Decimal(discount).quantize(Decimal('0.001')) if hasattr(self, 'discount_amount') else Decimal('0')
        self.total_amount = Decimal(total_amount).quantize(Decimal('0.001'))
        self.save(update_fields=['subtotal', 'tax_amount', 'total_amount'])

    def clean(self):
        """التحقق من صحة البيانات"""
        from django.core.exceptions import ValidationError
        
        # التحقق من أن الصندوق مطلوب للفواتير النقدية
        if self.payment_type == 'cash' and not self.cashbox:
            raise ValidationError(_('يجب تحديد الصندوق النقدي للفواتير النقدية'))
        
        # استدعاء التحقق الأساسي
        super().clean()


class SalesInvoiceItem(models.Model):
    """عنصر فاتورة المبيعات"""
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, 
                              verbose_name=_('Invoice'), related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, verbose_name=_('Product'))
    quantity = models.DecimalField(_('Quantity'), max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(_('Unit Price'), max_digits=15, decimal_places=3)
    tax_rate = models.DecimalField(_('Tax Rate'), max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_('Tax Amount'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('Total Amount'), max_digits=15, decimal_places=3, default=0)

    class Meta:
        verbose_name = _('Sales Invoice Item')
        verbose_name_plural = _('Sales Invoice Items')
        default_permissions = []  # No permissions needed - available to everyone

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
    return_number = models.CharField(_('Sales Return Number'), max_length=50, unique=True)
    date = models.DateField(_('Date'))
    original_invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, 
                                       verbose_name=_('Original Invoice'))
    customer = models.ForeignKey(CustomerSupplier, on_delete=models.PROTECT, verbose_name=_('Customer'))
    subtotal = models.DecimalField(_('Subtotal'), max_digits=15, decimal_places=3, default=0)
    tax_amount = models.DecimalField(_('Tax Amount'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('Total Amount'), max_digits=15, decimal_places=3, default=0)
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Sales Return')
        verbose_name_plural = _('Sales Returns')
        ordering = ['-date', '-return_number']
        default_permissions = []  # No default permissions
        permissions = [
            ('can_view_sales_returns', 'Can View Sales Returns'),
            ('can_add_sales_returns', 'Can Add Sales Returns'),
            ('can_edit_sales_returns', 'Can Edit Sales Returns'),
            ('can_delete_sales_returns', 'Can Delete Sales Returns'),
        ]

    def __str__(self):
        return f"{self.return_number} - {self.customer.name}"


class SalesReturnItem(models.Model):
    """عنصر مردود المبيعات"""
    return_invoice = models.ForeignKey(SalesReturn, on_delete=models.CASCADE, 
                                     verbose_name=_('Sales Return'), related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, verbose_name=_('Product'))
    quantity = models.DecimalField(_('Quantity'), max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(_('Unit Price'), max_digits=15, decimal_places=3)
    tax_rate = models.DecimalField(_('Tax Rate'), max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_('Tax Amount'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('Total Amount'), max_digits=15, decimal_places=3, default=0)

    class Meta:
        verbose_name = _('Sales Return Item')
        verbose_name_plural = _('Sales Return Items')
        default_permissions = []  # No permissions needed - available to everyone

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
    note_number = models.CharField(_('Credit Note Number'), max_length=50, unique=True)
    date = models.DateField(_('Date'))
    customer = models.ForeignKey(CustomerSupplier, on_delete=models.PROTECT, verbose_name=_('Customer'))
    subtotal = models.DecimalField(_('Subtotal'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('Total Amount'), max_digits=15, decimal_places=3, default=0)
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    # JoFotara integration fields
    jofotara_uuid = models.CharField(_('JoFotara UUID'), max_length=100, blank=True, null=True, 
                                   help_text=_('UUID returned from JoFotara API'))
    jofotara_sent_at = models.DateTimeField(_('Sent to JoFotara At'), blank=True, null=True,
                                          help_text=_('Date and time when credit note was sent to JoFotara'))
    jofotara_verification_url = models.URLField(_('JoFotara Verification URL'), blank=True, null=True,
                                              help_text=_('URL to verify credit note on JoFotara portal'))

    class Meta:
        verbose_name = _('Credit Note')
        verbose_name_plural = _('Credit Notes')
        ordering = ['-date', '-note_number']
        default_permissions = []  # No permissions needed - available to everyone

    def save(self, *args, **kwargs):
        # الإجمالي يساوي المجموع الفرعي (بدون ضريبة)
        self.total_amount = self.subtotal
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.note_number} - {self.customer.name}"
