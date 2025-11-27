from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from customers.models import CustomerSupplier
from decimal import Decimal, ROUND_HALF_UP

User = get_user_model()


class PurchaseInvoice(models.Model):
    """فاتورة المشتريات"""
    PAYMENT_TYPES = [
        ('cash', _('Cash')),
        ('credit', _('Credit')),
    ]

    PAYMENT_METHODS = [
        ('cash', _('Cash Payment')),
        ('check', _('Check Payment')),
        ('transfer', _('Bank Transfer')),
        ('credit', _('Credit Payment')),
    ]

    invoice_number = models.CharField(_('Invoice Number'), max_length=50)
    supplier_invoice_number = models.CharField(_('Supplier Invoice Number'), max_length=50)
    date = models.DateField(_('Date'))
    supplier = models.ForeignKey(CustomerSupplier, on_delete=models.PROTECT, 
                               verbose_name=_('Supplier'), limit_choices_to={'type__in': ['supplier', 'both']})
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT, 
                                verbose_name=_('Warehouse'), default=1)
    payment_type = models.CharField(_('Payment Type'), max_length=20, choices=PAYMENT_TYPES)
    payment_method = models.CharField(_('Payment Method'), max_length=20, choices=PAYMENT_METHODS, blank=True)
    cashbox = models.ForeignKey('cashboxes.Cashbox', on_delete=models.PROTECT, 
                               verbose_name=_('Cash Box'), null=True, blank=True)
    bank_account = models.ForeignKey('banks.BankAccount', on_delete=models.PROTECT, 
                                   verbose_name=_('Bank Account'), null=True, blank=True)
    check_number = models.CharField(_('Check Number'), max_length=50, blank=True)
    check_date = models.DateField(_('Check Date'), null=True, blank=True)
    is_tax_inclusive = models.BooleanField(_('Tax Inclusive'), default=True, 
                                         help_text=_('When selected, prices will include tax'))
    subtotal = models.DecimalField(_('Subtotal'), max_digits=15, decimal_places=3, default=0)
    tax_amount = models.DecimalField(_('Tax Amount'), max_digits=15, decimal_places=3, default=0)
    total_amount = models.DecimalField(_('Total Amount'), max_digits=15, decimal_places=3, default=0)
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    # JoFotara integration fields
    jofotara_uuid = models.CharField(_('JoFotara UUID'), max_length=100, blank=True, null=True,
                                   help_text=_('UUID returned from JoFotara API'))
    jofotara_qr_code = models.TextField(_('JoFotara QR Code'), blank=True, null=True,
                                      help_text=_('QR Code image data URL from JoFotara'))
    jofotara_sent_at = models.DateTimeField(_('Sent to JoFotara At'), blank=True, null=True,
                                          help_text=_('Date and time when invoice was sent to JoFotara'))
    jofotara_verification_url = models.URLField(_('JoFotara Verification URL'), blank=True, null=True,
                                              help_text=_('URL to verify invoice on JoFotara portal'))
    is_posted_to_tax = models.BooleanField(_('Posted to Tax Authority'), default=False,
                                         help_text=_('Whether this invoice has been successfully posted to tax authority'))

    class Meta:
        verbose_name = _('Purchase Invoice')
        verbose_name_plural = _('Purchase Invoices')
        ordering = ['-date', '-invoice_number']
        default_permissions = []  # No default permissions
        permissions = [
            ('can_view_purchases', 'Can View Purchases'),
            ('can_add_purchases', 'Can Add Purchases'),
            ('can_edit_purchases', 'Can Edit Purchases'),
            ('can_delete_purchases', 'Can Delete Purchases'),
            ('can_view_purchase_statement', 'Can View Purchase Statement'),
        ]

    def __str__(self):
        return f"{self.supplier_invoice_number} - {self.supplier.name}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.payment_type == 'cash':
            if self.payment_method == 'cash' and not self.cashbox:
                raise ValidationError(_('Cash box must be selected for cash payment'))
            elif self.payment_method in ['check', 'transfer'] and not self.bank_account:
                raise ValidationError(_('Bank account must be selected for check or transfer payment'))
            if self.payment_method == 'check' and not self.check_number:
                raise ValidationError(_('Check number is required for check payment'))
            if self.payment_method == 'check' and not self.check_date:
                raise ValidationError(_('Check date is required for check payment'))
        
        # التحقق من تطابق المجاميع مع العناصر (للفواتير الموجودة فقط)
        if self.pk and self.items.exists():
            calculated_subtotal = Decimal('0')
            calculated_tax_amount = Decimal('0')
            calculated_total_amount = Decimal('0')

            for item in self.items.all():
                calculated_subtotal += item.quantity * item.unit_price
                calculated_tax_amount += item.tax_amount
                calculated_total_amount += item.total_amount

            calculated_subtotal = calculated_subtotal.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
            calculated_tax_amount = calculated_tax_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
            calculated_total_amount = calculated_total_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)

            # السماح بهامش خطأ صغير بسبب التقريب
            tolerance = Decimal('0.01')
            
            if abs(self.subtotal - calculated_subtotal) > tolerance:
                raise ValidationError(_('Subtotal does not match calculated value from items. Expected: %(expected)s, Current: %(current)s') % {
                    'expected': calculated_subtotal, 'current': self.subtotal})
            
            if abs(self.tax_amount - calculated_tax_amount) > tolerance:
                raise ValidationError(_('Tax amount does not match calculated value from items. Expected: %(expected)s, Current: %(current)s') % {
                    'expected': calculated_tax_amount, 'current': self.tax_amount})
            
            if abs(self.total_amount - calculated_total_amount) > tolerance:
                raise ValidationError(_('Total amount does not match calculated value from items. Expected: %(expected)s, Current: %(current)s') % {
                    'expected': calculated_total_amount, 'current': self.total_amount})

    def verify_totals_integrity(self):
        """
        التحقق من تطابق المجاميع مع العناصر
        يرجع True إذا كانت المجاميع صحيحة، False إذا كانت خاطئة
        """
        if not self.items.exists():
            return True  # لا توجد عناصر للمقارنة
        
        calculated_subtotal = Decimal('0')
        calculated_tax_amount = Decimal('0')
        calculated_total_amount = Decimal('0')

        for item in self.items.all():
            calculated_subtotal += item.quantity * item.unit_price
            calculated_tax_amount += item.tax_amount
            calculated_total_amount += item.total_amount

        calculated_subtotal = calculated_subtotal.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        calculated_tax_amount = calculated_tax_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        calculated_total_amount = calculated_total_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)

        # السماح بهامش خطأ صغير بسبب التقريب
        tolerance = Decimal('0.01')
        
        return (abs(self.subtotal - calculated_subtotal) <= tolerance and
                abs(self.tax_amount - calculated_tax_amount) <= tolerance and
                abs(self.total_amount - calculated_total_amount) <= tolerance)

    def calculate_subtotal_from_items(self):
        """حساب المجموع الفرعي من العناصر"""
        if not self.items.exists():
            return Decimal('0')
        return sum(item.quantity * item.unit_price for item in self.items.all()).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)

    def calculate_tax_from_items(self):
        """حساب مبلغ الضريبة من العناصر"""
        if not self.items.exists():
            return Decimal('0')
        return sum(item.tax_amount for item in self.items.all()).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)

    def calculate_total_from_items(self):
        """حساب المجموع الكلي من العناصر"""
        if not self.items.exists():
            return Decimal('0')
        return sum(item.total_amount for item in self.items.all()).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        from decimal import Decimal, ROUND_HALF_UP
        
        # حساب المجاميع من العناصر فقط للفاتورة الجديدة
        if not self.pk:  # فاتورة جديدة
            super().save(*args, **kwargs)
            # حساب المجاميع بعد الحفظ الأول
            if self.items.exists():
                subtotal = Decimal('0')
                tax_amount = Decimal('0')
                total_amount = Decimal('0')

                for item in self.items.all():
                    subtotal += item.quantity * item.unit_price
                    tax_amount += item.tax_amount
                    total_amount += item.total_amount

                self.subtotal = subtotal.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                self.tax_amount = tax_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                self.total_amount = total_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                super().save(update_fields=['subtotal', 'tax_amount', 'total_amount'])
        else:
            # للفاتورة الموجودة، لا نعيد حساب المجاميع إلا إذا تم طلب ذلك صراحة
            super().save(*args, **kwargs)


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
        default_permissions = []  # No permissions needed - available to everyone

    def __str__(self):
        return f"{self.invoice.supplier_invoice_number} - {self.product.name}"

    def save(self, *args, **kwargs):
        # حساب مبلغ الضريبة والمبلغ الإجمالي
        from decimal import Decimal, ROUND_HALF_UP
        
        subtotal = self.quantity * self.unit_price
        
        if self.invoice.is_tax_inclusive:
            # السعر شامل الضريبة: نستخرج الضريبة من المبلغ
            # الصيغة: الضريبة = المبلغ × (نسبة الضريبة ÷ (100 + نسبة الضريبة))
            if self.tax_rate > 0:
                tax_amount = subtotal * (self.tax_rate / (Decimal('100') + self.tax_rate))
                total_amount = subtotal  # المبلغ الإجمالي هو نفسه المبلغ المدخل (شامل الضريبة)
            else:
                tax_amount = Decimal('0')
                total_amount = subtotal
        else:
            # السعر غير شامل الضريبة: نضيف الضريبة للمبلغ
            # الصيغة: الضريبة = المبلغ × (نسبة الضريبة ÷ 100)
            if self.tax_rate > 0:
                tax_amount = subtotal * (self.tax_rate / Decimal('100'))
                total_amount = subtotal + tax_amount
            else:
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
    original_invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, 
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
    
    # JoFotara integration fields
    jofotara_uuid = models.CharField(_('JoFotara UUID'), max_length=100, blank=True, null=True,
                                   help_text=_('UUID returned from JoFotara API'))
    jofotara_qr_code = models.TextField(_('JoFotara QR Code'), blank=True, null=True,
                                      help_text=_('QR Code image data URL from JoFotara'))
    jofotara_sent_at = models.DateTimeField(_('Sent to JoFotara At'), blank=True, null=True,
                                          help_text=_('Date and time when return was sent to JoFotara'))
    jofotara_verification_url = models.URLField(_('JoFotara Verification URL'), blank=True, null=True,
                                              help_text=_('URL to verify return on JoFotara portal'))
    is_posted_to_tax = models.BooleanField(_('Posted to Tax Authority'), default=False,
                                         help_text=_('Whether this return has been successfully posted to tax authority'))

    class Meta:
        verbose_name = _('Purchase Return')
        verbose_name_plural = _('Purchase Returns')
        ordering = ['-date', '-return_number']
        default_permissions = []  # No default permissions
        permissions = [
            ('can_view_purchase_returns', 'Can View Purchase Returns'),
            ('can_add_purchase_returns', 'Can Add Purchase Returns'),
            ('can_edit_purchase_returns', 'Can Edit Purchase Returns'),
            ('can_delete_purchase_returns', 'Can Delete Purchase Returns'),
        ]

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
        default_permissions = []  # No permissions needed - available to everyone

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
    jofotara_qr_code = models.TextField(_('JoFotara QR Code'), blank=True, null=True,
                                      help_text=_('QR Code image data URL from JoFotara'))
    jofotara_sent_at = models.DateTimeField(_('Sent to JoFotara At'), blank=True, null=True,
                                          help_text=_('Date and time when debit note was sent to JoFotara'))
    jofotara_verification_url = models.URLField(_('JoFotara Verification URL'), blank=True, null=True,
                                              help_text=_('URL to verify debit note on JoFotara portal'))
    is_posted_to_tax = models.BooleanField(_('Posted to Tax Authority'), default=False,
                                         help_text=_('Whether this debit note has been successfully posted to tax authority'))

    class Meta:
        verbose_name = _('Debit Note')
        verbose_name_plural = _('Debit Notes')
        ordering = ['-date', '-note_number']
        default_permissions = []  # No default permissions
        permissions = [
            ('can_view_debit_notes', 'Can View Debit Notes'),
            ('can_add_debit_notes', 'Can Add Debit Notes'),
            ('can_edit_debit_notes', 'Can Edit Debit Notes'),
            ('can_delete_debit_notes', 'Can Delete Debit Notes'),
        ]

    def save(self, *args, **kwargs):
        # في إشعار الخصم، لا يوجد ضريبة - المبلغ الإجمالي = المجموع الفرعي
        self.total_amount = self.subtotal
        super().save(*args, **kwargs)
