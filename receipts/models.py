from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from customers.models import CustomerSupplier
from cashboxes.models import Cashbox
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone

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
                               verbose_name=_('Customer'), related_name='payment_receipts')
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
    bounce_reason = models.CharField(_('سبب الارتداد'), max_length=100, blank=True, 
                                   help_text=_('سبب ارتداد الشيك (رصيد غير كافٍ، توقيع غير صحيح، إيقاف من البنك...)'))
    
    # IFRS 9 - خسائر الائتمان المتوقعة
    expected_credit_loss = models.DecimalField(_('خسائر الائتمان المتوقعة (ECL)'), max_digits=15, decimal_places=3, 
                                            default=0, help_text=_('قيمة الخسارة المتوقعة وفق IFRS 9'))
    ecl_calculation_date = models.DateTimeField(_('تاريخ حساب ECL'), null=True, blank=True)
    ecl_calculation_method = models.CharField(_('طريقة حساب ECL'), max_length=50, blank=True,
                                           help_text=_('طريقة حساب الخسارة المتوقعة (مرتد، متأخر، إلخ)'))
    
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
    
    def calculate_expected_credit_loss(self):
        """
        حساب خسائر الائتمان المتوقعة وفق IFRS 9
        محسن ليشمل تقييم مخاطر العميل وسجله الائتماني
        """
        from datetime import datetime, timedelta
        
        if self.payment_type != 'check':
            return Decimal('0.000'), ''
        
        current_date = datetime.now().date()
        ecl_amount = Decimal('0.000')
        
        # تقييم مخاطر العميل بناءً على سجله
        customer_risk_factor = self._calculate_customer_risk_factor()
        
        if self.check_status == 'bounced':
            # شيك مرتد - خسارة كاملة
            ecl_amount = self.amount
            self.ecl_calculation_method = 'شيك مرتد - خسارة كاملة'
            
        elif self.check_status == 'collected':
            # شيك محصل - تحقق من التأخير
            collection = self.collections.filter(status='collected').first()
            if collection:
                days_late = (collection.collection_date - self.check_due_date).days
                
                if days_late > 0:
                    # شيك متأخر - حساب خسارة جزئية حسب مدة التأخير ومخاطر العميل
                    base_percentage = Decimal('0.05')  # 5% أساسي
                    
                    if days_late <= 30:
                        ecl_percentage = base_percentage
                    elif days_late <= 90:
                        ecl_percentage = Decimal('0.15')
                    elif days_late <= 180:
                        ecl_percentage = Decimal('0.30')
                    else:
                        ecl_percentage = Decimal('0.50')
                    
                    # تطبيق عامل مخاطر العميل
                    ecl_percentage *= customer_risk_factor
                    
                    ecl_amount = self.amount * ecl_percentage
                    self.ecl_calculation_method = f'متأخر {days_late}يوم - {ecl_percentage*100:.1f}%'
                else:
                    # شيك محصل في الموعد أو مبكراً - لا خسارة
                    ecl_amount = Decimal('0.000')
                    self.ecl_calculation_method = 'محصل في الموعد'
            else:
                # شيك مودع لكن غير محصل - خسارة محتملة
                days_since_deposit = (current_date - self.check_due_date).days
                if days_since_deposit > 0:
                    base_percentage = min(Decimal('0.10'), Decimal(days_since_deposit) / Decimal('365') * Decimal('0.20'))
                    ecl_percentage = base_percentage * customer_risk_factor
                    ecl_amount = self.amount * ecl_percentage
                    self.ecl_calculation_method = f'مودع متأخر {days_since_deposit}يوم'
                else:
                    ecl_amount = Decimal('0.000')
                    self.ecl_calculation_method = 'مودع في الموعد'
                    
        elif self.check_status in ['new', 'deposited']:
            # شيك جديد أو مودع - تقييم أولي للمخاطر
            days_to_due = (self.check_due_date - current_date).days
            
            if days_to_due < 0:
                # شيك متأخر في الاستحقاق
                days_overdue = abs(days_to_due)
                base_percentage = min(Decimal('0.20'), Decimal(days_overdue) / Decimal('365') * Decimal('0.30'))
                ecl_percentage = base_percentage * customer_risk_factor
                ecl_amount = self.amount * ecl_percentage
                self.ecl_calculation_method = f'متأخر {days_overdue}يوم'
            else:
                # شيك في الموعد - خسارة منخفضة مع مراعاة مخاطر العميل
                base_percentage = Decimal('0.01')  # 1% أساسي
                ecl_percentage = base_percentage * customer_risk_factor
                ecl_amount = self.amount * ecl_percentage
                self.ecl_calculation_method = f'في الموعد {ecl_percentage*100:.1f}%'
        
        self.expected_credit_loss = ecl_amount
        self.ecl_calculation_date = timezone.now()
        self.save(update_fields=['expected_credit_loss', 'ecl_calculation_date', 'ecl_calculation_method'])
        
        return ecl_amount, self.ecl_calculation_method
    
    def _calculate_customer_risk_factor(self):
        """
        حساب معامل مخاطر العميل بناءً على سجله الائتماني
        """
        # حساب عدد الشيكات المرتدة للعميل
        bounced_cheques = PaymentReceipt.objects.filter(
            customer=self.customer,
            payment_type='check',
            check_status='bounced'
        ).count()
        
        # حساب إجمالي الشيكات للعميل
        total_cheques = PaymentReceipt.objects.filter(
            customer=self.customer,
            payment_type='check'
        ).count()
        
        if total_cheques == 0:
            return Decimal('1.0')  # عميل جديد
        
        # حساب نسبة الارتداد
        bounce_rate = bounced_cheques / total_cheques
        
        # تحديد معامل المخاطر
        if bounce_rate == 0:
            risk_factor = Decimal('0.8')  # عميل موثوق
        elif bounce_rate <= 0.1:
            risk_factor = Decimal('1.0')  # مخاطر متوسطة
        elif bounce_rate <= 0.25:
            risk_factor = Decimal('1.3')  # مخاطر عالية
        else:
            risk_factor = Decimal('1.5')  # مخاطر عالية جداً
        
        return risk_factor
    
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
