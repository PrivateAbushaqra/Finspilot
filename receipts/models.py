from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from customers.models import CustomerSupplier
from cashboxes.models import Cashbox
from decimal import Decimal
from django.core.exceptions import ValidationError

User = get_user_model()


class PaymentReceipt(models.Model):
    """سند قبض من العميل"""
    PAYMENT_TYPES = [
        ('cash', _('نقدي')),
        ('check', _('شيك')),
    ]
    
    CHECK_STATUS = [
        ('pending', _('في الانتظار')),
        ('collected', _('تم التحصيل')),
        ('bounced', _('مرتد')),
        ('cancelled', _('ملغي')),
    ]
    
    receipt_number = models.CharField(_('رقم السند'), max_length=50, unique=True)
    date = models.DateField(_('تاريخ السند'))
    customer = models.ForeignKey(CustomerSupplier, on_delete=models.PROTECT, 
                               verbose_name=_('العميل'), related_name='payment_receipts')
    payment_type = models.CharField(_('نوع الدفع'), max_length=10, choices=PAYMENT_TYPES)
    amount = models.DecimalField(_('Amount'), max_digits=15, decimal_places=3)
    
    # للدفع النقدي
    cashbox = models.ForeignKey(Cashbox, on_delete=models.PROTECT, null=True, blank=True,
                              verbose_name=_('الصندوق النقدي'), related_name='payment_receipts')
    
    # للشيكات
    check_number = models.CharField(_('رقم الشيك'), max_length=50, blank=True)
    check_date = models.DateField(_('تاريخ الشيك'), null=True, blank=True)
    check_due_date = models.DateField(_('تاريخ استحقاق الشيك'), null=True, blank=True)
    bank_name = models.CharField(_('Bank Name'), max_length=200, blank=True)
    check_cashbox = models.ForeignKey(Cashbox, on_delete=models.PROTECT, null=True, blank=True,
                                    verbose_name=_('صندوق الشيك'), related_name='check_receipts')
    check_status = models.CharField(_('حالة الشيك'), max_length=20, choices=CHECK_STATUS, 
                                  default='pending', blank=True)
    
    # معلومات عامة
    description = models.TextField(_('Description'), blank=True)
    notes = models.TextField(_('Notes'), blank=True)
    
    # معلومات النظام
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    # حالة السند
    is_active = models.BooleanField(_('Active'), default=True)
    is_reversed = models.BooleanField(_('مُعكوس'), default=False)
    reversed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name=_('عُكس بواسطة'), related_name='reversed_receipts')
    reversed_at = models.DateTimeField(_('تاريخ العكس'), null=True, blank=True)
    reversal_reason = models.TextField(_('سبب العكس'), blank=True)

    class Meta:
        verbose_name = _('سند قبض')
        verbose_name_plural = _('سندات القبض')
        ordering = ['-date', '-receipt_number']
        permissions = [
                ('can_access_receipts', _('يمكن الوصول إلى سندات القبض')),
        ]

    def __str__(self):
        return f"{self.receipt_number} - {self.customer.name} - {self.amount}"
    
    def clean(self):
        """التحقق من صحة البيانات"""
        if self.payment_type == 'cash' and not self.cashbox:
            raise ValidationError(_('يجب تحديد الصندوق النقدي للدفع النقدي'))
        
        if self.payment_type == 'check':
            if not self.check_number:
                raise ValidationError(_('رقم الشيك مطلوب'))
            if not self.check_date:
                raise ValidationError(_('تاريخ الشيك مطلوب'))
            if not self.check_due_date:
                raise ValidationError(_('تاريخ استحقاق الشيك مطلوب'))
            if not self.bank_name:
                raise ValidationError(_('اسم البنك مطلوب'))
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    @property
    def can_be_reversed(self):
        """التحقق من إمكانية عكس السند"""
        return self.is_active and not self.is_reversed
    
    @property
    def effective_amount(self):
        """المبلغ الفعلي (سالب إذا كان معكوساً)"""
        return -self.amount if self.is_reversed else self.amount


class CheckCollection(models.Model):
    """تحصيل الشيك"""
    COLLECTION_STATUS = [
        ('collected', _('تم التحصيل')),
        ('bounced', _('مرتد')),
    ]
    
    receipt = models.ForeignKey(PaymentReceipt, on_delete=models.PROTECT, 
                              verbose_name=_('سند القبض'), related_name='collections')
    collection_date = models.DateField(_('تاريخ التحصيل'))
    status = models.CharField(_('حالة التحصيل'), max_length=20, choices=COLLECTION_STATUS)
    cashbox = models.ForeignKey(Cashbox, on_delete=models.PROTECT, null=True, blank=True,
                              verbose_name=_('الصندوق النقدي'))
    notes = models.TextField(_('Notes'), blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('تحصيل شيك')
        verbose_name_plural = _('تحصيل الشيكات')
        ordering = ['-collection_date']

    def __str__(self):
        return f"تحصيل {self.receipt.receipt_number} - {self.get_status_display()}"


class ReceiptReversal(models.Model):
    """عكس سند القبض"""
    original_receipt = models.OneToOneField(PaymentReceipt, on_delete=models.PROTECT,
                                          verbose_name=_('السند الأصلي'), related_name='reversal')
    reversal_date = models.DateField(_('تاريخ العكس'))
    reason = models.TextField(_('سبب العكس'))
    notes = models.TextField(_('Notes'), blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('عكس سند قبض')
        verbose_name_plural = _('عكس سندات القبض')
        ordering = ['-reversal_date']

    def __str__(self):
        return f"عكس {self.original_receipt.receipt_number}"
