from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from customers.models import CustomerSupplier

User = get_user_model()


class PurchaseInvoice(models.Model):
    """فاتورة المشتريات"""
    PAYMENT_TYPES = [
        ('cash', _('Cash')),
        ('credit', _('Credit')),
    ]

    invoice_number = models.CharField(_('Invoice Number'), max_length=50)
    supplier_invoice_number = models.CharField(_('Supplier Invoice Number'), max_length=50)
    date = models.DateField(_('Date'))
    supplier = models.ForeignKey(CustomerSupplier, on_delete=models.PROTECT, 
                               verbose_name=_('Supplier'), limit_choices_to={'type__in': ['supplier', 'both']})
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT, 
                                verbose_name=_('Warehouse'), default=1)
    payment_type = models.CharField(_('Payment Type'), max_length=20, choices=PAYMENT_TYPES)
    is_tax_inclusive = models.BooleanField(_('Tax Inclusive'), default=True, 
                                         help_text=_('When selected, prices will include tax'))
    subtotal = models.DecimalField(_('Subtotal'), max_digits=15, decimal_places=3, default=0)
    tax_amount = models.DecimalField(_('Tax Amount'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('Total Amount'), max_digits=15, decimal_places=3, default=0)
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Purchase Invoice')
        verbose_name_plural = _('Purchase Invoices')
        ordering = ['-date', '-invoice_number']
        permissions = [
            ('can_view_purchases', _('Can View Purchase')),
            ('can_view_purchase_statement', _('Can View Purchase Statement')),
        ]
    # لا يجب تعريف صلاحية view_purchaseinvoice هنا لأنها افتراضية من Django

    def __str__(self):
        return f"{self.supplier_invoice_number} - {self.supplier.name}"


class PurchaseInvoiceItem(models.Model):
    """عنصر فاتورة المشتريات"""
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, 
                              verbose_name=_('Invoice'), related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, verbose_name=_('Product'))
    quantity = models.DecimalField(_('Quantity'), max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(_('Unit Price'), max_digits=15, decimal_places=3)
    tax_rate = models.DecimalField(_('Tax Rate'), max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_('Tax Amount'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('Total Amount'), max_digits=15, decimal_places=3, default=0)

    class Meta:
        verbose_name = _('Purchase Invoice Item')
        verbose_name_plural = _('Purchase Invoice Items')

    def __str__(self):
        return f"{self.invoice.supplier_invoice_number} - {self.product.name}"

    def save(self, *args, **kwargs):
        # حساب مبلغ الضريبة والمبلغ الإجمالي
        from decimal import Decimal, ROUND_HALF_UP
        
        subtotal = self.quantity * self.unit_price
        
        if self.invoice.is_tax_inclusive:
            # عند تفعيل "شامل ضريبة": يحسب الضريبة بشكل طبيعي
            tax_amount = subtotal * (self.tax_rate / Decimal('100'))
            total_amount = subtotal + tax_amount
        else:
            # عند إلغاء "شامل ضريبة": لا يحسب أي ضريبة
            tax_amount = Decimal('0')
            total_amount = subtotal
        
        # تقريب إلى 3 خانات عشرية
        self.tax_amount = tax_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        self.total_amount = total_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        super().save(*args, **kwargs)


class PurchaseReturn(models.Model):
    """مردود مشتريات"""
    RETURN_TYPES = [
        ('full', _('Full Return')),
        ('partial', _('Partial Return')),
    ]
    
    RETURN_REASONS = [
        ('defective', _('Defective Product')),
        ('wrong_item', _('Wrong Item')),
        ('excess', _('Excess Quantity')),
        ('expired', _('Expired')),
        ('damaged', _('Damaged During Transport')),
        ('other', _('Other')),
    ]

    return_number = models.CharField(_('Return Number'), max_length=50, unique=True)
    supplier_return_number = models.CharField(_('Supplier Return Number (Source)'), max_length=50, 
                                            help_text=_('The return number issued by the supplier'))
    original_invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.PROTECT, 
                                       verbose_name=_('Original Invoice'), related_name='returns')
    date = models.DateField(_('Return Date'))
    return_type = models.CharField(_('Return Type'), max_length=20, choices=RETURN_TYPES, default='partial')
    return_reason = models.CharField(_('Return Reason'), max_length=20, choices=RETURN_REASONS)
    subtotal = models.DecimalField(_('Subtotal'), max_digits=15, decimal_places=3, default=0)
    tax_amount = models.DecimalField(_('Tax Amount'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('Total Amount'), max_digits=15, decimal_places=3, default=0)
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Purchase Return')
        verbose_name_plural = _('Purchase Returns')
        ordering = ['-date', '-return_number']
        permissions = (
            ('can_view_purchasereturn', _('Can view purchase returns')),
        )

    def __str__(self):
        return f"{self.return_number} - {self.original_invoice.supplier.name}"

    def save(self, *args, **kwargs):
        if not self.return_number:
            try:
                from core.models import DocumentSequence
                seq = DocumentSequence.objects.get(document_type='purchase_return')
                self.return_number = seq.get_next_number()
            except DocumentSequence.DoesNotExist:
                raise ValueError(_('Document sequence for purchase returns must be set up first'))
        super().save(*args, **kwargs)

    @property
    def supplier(self):
        return self.original_invoice.supplier


class PurchaseReturnItem(models.Model):
    """عنصر مردود المشتريات"""
    return_invoice = models.ForeignKey(PurchaseReturn, on_delete=models.CASCADE, 
                                     verbose_name=_('Purchase Return'), related_name='items')
    original_item = models.ForeignKey(PurchaseInvoiceItem, on_delete=models.PROTECT, 
                                    verbose_name=_('Original Item'))
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, verbose_name=_('Product'))
    returned_quantity = models.DecimalField(_('Returned Quantity'), max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(_('Unit Price'), max_digits=15, decimal_places=3)
    tax_rate = models.DecimalField(_('Tax Rate'), max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_('Tax Amount'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('Total Amount'), max_digits=15, decimal_places=3, default=0)

    class Meta:
        verbose_name = _('Purchase Return Item')
        verbose_name_plural = _('Purchase Return Items')

    def __str__(self):
        return f"{self.product.name} - {self.returned_quantity}"

    def clean(self):
        """التحقق من صحة الكمية المرتجعة"""
        from django.core.exceptions import ValidationError
        
        if self.returned_quantity > self.original_item.quantity:
            raise ValidationError(_('Returned quantity cannot be greater than the original quantity'))
        
        # التحقق من المردودات السابقة
        previous_returns = PurchaseReturnItem.objects.filter(
            original_item=self.original_item
        ).exclude(pk=self.pk)
        
        total_returned = sum(item.returned_quantity for item in previous_returns)
        if total_returned + self.returned_quantity > self.original_item.quantity:
            raise ValidationError(_('Total returned quantity exceeds the original quantity'))

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


class PurchaseDebitNote(models.Model):
    """Purchase Debit Note"""
    note_number = models.CharField(_('Debit Note Number'), max_length=50, unique=True)
    date = models.DateField(_('Date'))
    supplier = models.ForeignKey(CustomerSupplier, on_delete=models.PROTECT, verbose_name=_('Supplier'))
    supplier_debit_note_number = models.CharField(_('Supplier Debit Note Number (Source)'), max_length=50, 
                                                help_text=_('The debit note number issued by the supplier'))
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
                                          help_text=_('Date and time when debit note was sent to JoFotara'))
    jofotara_verification_url = models.URLField(_('JoFotara Verification URL'), blank=True, null=True,
                                              help_text=_('URL to verify debit note on JoFotara portal'))

    class Meta:
        verbose_name = _('Debit Note')
        verbose_name_plural = _('Debit Notes')
        ordering = ['-date', '-note_number']
        permissions = (
            ('can_send_to_jofotara', 'Can send debit notes to JoFotara'),
            ('can_view_debitnote', _('Can view debit notes')),
        )

    def save(self, *args, **kwargs):
        # في إشعار الخصم، لا يوجد ضريبة - المبلغ الإجمالي = المجموع الفرعي
        self.total_amount = self.subtotal
        super().save(*args, **kwargs)
