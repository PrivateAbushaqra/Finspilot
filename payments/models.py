from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from customers.models import CustomerSupplier
from cashboxes.models import Cashbox
from banks.models import BankAccount
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone as django_timezone

User = get_user_model()


class PaymentVoucher(models.Model):
    """سند صرف للموردين أو مصاريف"""
    PAYMENT_TYPES = [
        ('cash', _('نقدي')),
        ('check', _('شيك')),
        ('bank_transfer', _('تحويل بنكي')),
    ]
    
    VOUCHER_TYPES = [
        ('supplier', _('دفع لمورد')),
        ('expense', _('مصروفات')),
        ('salary', _('راتب')),
        ('other', _('أخرى')),
    ]
    
    CHECK_STATUS = [
        ('pending', _('في الانتظار')),
        ('cleared', _('تم الصرف')),
        ('cancelled', _('ملغي')),
    ]
    
    # معلومات أساسية
    voucher_number = models.CharField(_('رقم السند'), max_length=50, unique=True)
    date = models.DateField(_('تاريخ السند'))
    voucher_type = models.CharField(_('نوع السند'), max_length=20, choices=VOUCHER_TYPES)
    payment_type = models.CharField(_('نوع الدفع'), max_length=15, choices=PAYMENT_TYPES)
    amount = models.DecimalField(_('المبلغ'), max_digits=15, decimal_places=3)
    
    # المستفيد
    supplier = models.ForeignKey(CustomerSupplier, on_delete=models.PROTECT, null=True, blank=True,
                               verbose_name=_('المورد'), related_name='payment_vouchers')
    beneficiary_name = models.CharField(_('اسم المستفيد'), max_length=200, blank=True,
                                      help_text=_('في حالة عدم كون المستفيد مورد مسجل'))
    
    # للدفع النقدي
    cashbox = models.ForeignKey(Cashbox, on_delete=models.PROTECT, null=True, blank=True,
                              verbose_name=_('الصندوق النقدي'), related_name='payment_vouchers')
    
    # للتحويل البنكي
    bank = models.ForeignKey(BankAccount, on_delete=models.PROTECT, null=True, blank=True,
                           verbose_name=_('البنك'), related_name='payment_vouchers')
    bank_reference = models.CharField(_('مرجع التحويل'), max_length=100, blank=True)
    
    # للشيكات
    check_number = models.CharField(_('رقم الشيك'), max_length=50, blank=True)
    check_date = models.DateField(_('تاريخ الشيك'), null=True, blank=True)
    check_due_date = models.DateField(_('تاريخ استحقاق الشيك'), null=True, blank=True)
    check_bank_name = models.CharField(_('اسم البنك'), max_length=200, blank=True)
    check_status = models.CharField(_('حالة الشيك'), max_length=20, choices=CHECK_STATUS, 
                                  default='pending', blank=True)
    
    # معلومات إضافية
    description = models.TextField(_('الوصف'))
    notes = models.TextField(_('ملاحظات'), blank=True)
    
    # معلومات النظام
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('أنشئ بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    # حالة السند
    is_active = models.BooleanField(_('نشط'), default=True)
    is_reversed = models.BooleanField(_('مُعكوس'), default=False)
    reversed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name=_('عُكس بواسطة'), related_name='reversed_payments')
    reversed_at = models.DateTimeField(_('تاريخ العكس'), null=True, blank=True)
    reversal_reason = models.TextField(_('سبب العكس'), blank=True)

    class Meta:
        verbose_name = _('سند صرف')
        verbose_name_plural = _('سندات الصرف')
        ordering = ['-date', '-voucher_number']

    def __str__(self):
        beneficiary = self.supplier.name if self.supplier else self.beneficiary_name
        return f"{self.voucher_number} - {beneficiary} - {self.amount}"
    
    def clean(self):
        """التحقق من صحة البيانات الأساسية"""
        # التحقق الأساسي فقط - التحقق التفصيلي يتم في Form
        pass
    
    def save(self, *args, **kwargs):
        self.clean()
        
        # توليد رقم السند تلقائياً إذا لم يكن موجوداً
        if not self.voucher_number:
            self.voucher_number = self.generate_voucher_number()
        
        super().save(*args, **kwargs)
    
    def generate_voucher_number(self):
        """توليد رقم سند صرف تلقائي"""
        from django.db.models import Max
        
        # الحصول على آخر رقم سند في نفس السنة
        current_year = django_timezone.now().year
        last_voucher = PaymentVoucher.objects.filter(
            voucher_number__startswith=f'PV{current_year}'
        ).aggregate(Max('voucher_number'))['voucher_number__max']
        
        if last_voucher:
            # استخراج الرقم التسلسلي
            try:
                last_number = int(last_voucher.split('-')[-1])
                new_number = last_number + 1
            except (ValueError, IndexError):
                new_number = 1
        else:
            new_number = 1
        
        return f'PV{current_year}-{new_number:06d}'
    
    @property
    def can_be_reversed(self):
        """التحقق من إمكانية عكس السند"""
        return self.is_active and not self.is_reversed
    
    @property
    def effective_amount(self):
        """المبلغ الفعلي (سالب إذا كان معكوساً)"""
        return -self.amount if self.is_reversed else self.amount
    
    @property
    def beneficiary_display(self):
        """عرض اسم المستفيد"""
        return self.supplier.name if self.supplier else self.beneficiary_name


# PaymentVoucherItem سيتم إضافته لاحقاً في إصدار مستقبلي
# class PaymentVoucherItem(models.Model):
#     """عناصر سند الصرف (في حالة تفصيل المصاريف)"""
#     voucher = models.ForeignKey(PaymentVoucher, on_delete=models.CASCADE, 
#                                related_name='items', verbose_name=_('سند الصرف'))
#     description = models.CharField(_('الوصف'), max_length=200)
#     amount = models.DecimalField(_('المبلغ'), max_digits=15, decimal_places=3)
#     account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT, null=True, blank=True,
#                                verbose_name=_('الحساب'), related_name='payment_items')
#     
#     class Meta:
#         verbose_name = _('عنصر سند صرف')
#         verbose_name_plural = _('عناصر سند الصرف')
#     
#     def __str__(self):
#         return f"{self.voucher.voucher_number} - {self.description} - {self.amount}"
