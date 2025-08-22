from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()


class Cashbox(models.Model):
    """الصندوق النقدي"""
    name = models.CharField(_('اسم الصندوق'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    balance = models.DecimalField(_('Balance'), max_digits=15, decimal_places=3, default=0)
    currency = models.CharField(_('Currency'), max_length=10, blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    location = models.CharField(_('الموقع'), max_length=200, blank=True)
    responsible_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                       verbose_name=_('المسؤول عن الصندوق'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('صندوق نقدي')
        verbose_name_plural = _('الصناديق النقدية')
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """إذا لم يتم تحديد العملة، استخدم العملة الأساسية من إعدادات الشركة"""
        if not self.currency:
            from core.models import CompanySettings
            # الحصول على العملة من إعدادات الشركة
            company_settings = CompanySettings.get_settings()
            if company_settings and company_settings.currency:
                self.currency = company_settings.currency
            else:
                # إذا لم توجد عملة، استخدم العملة الافتراضية
                self.currency = 'JOD'
        super().save(*args, **kwargs)
    
    def get_currency_symbol(self):
        """الحصول على رمز العملة"""
        from settings.models import Currency
        currency = Currency.objects.filter(code=self.currency).first()
        if currency:
            return currency.symbol if currency.symbol else currency.code
        return self.currency
    
    def sync_balance(self):
        """مزامنة رصيد الصندوق مع المعاملات الفعلية"""
        from decimal import Decimal
        from django.db.models import Sum
        
        # حساب إجمالي الإيداعات والتحويلات الواردة
        deposits = CashboxTransaction.objects.filter(
            cashbox=self,
            transaction_type__in=['deposit', 'transfer_in', 'initial_balance']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # حساب إجمالي السحوبات والتحويلات الصادرة
        withdrawals = CashboxTransaction.objects.filter(
            cashbox=self,
            transaction_type__in=['withdrawal', 'transfer_out']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # حساب الرصيد الجديد
        new_balance = deposits - withdrawals
        
        # تحديث الرصيد إذا كان مختلفاً
        if self.balance != new_balance:
            self.balance = new_balance
            self.save(update_fields=['balance'])
        
        return new_balance
    
    def calculate_actual_balance(self):
        """حساب الرصيد الفعلي دون حفظ التغييرات"""
        from decimal import Decimal
        from django.db.models import Sum
        
        deposits = CashboxTransaction.objects.filter(
            cashbox=self,
            transaction_type__in=['deposit', 'transfer_in', 'initial_balance']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        withdrawals = CashboxTransaction.objects.filter(
            cashbox=self,
            transaction_type__in=['withdrawal', 'transfer_out']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        return deposits - withdrawals


class CashboxTransfer(models.Model):
    """التحويل بين الصناديق أو بين الصناديق والبنوك"""
    TRANSFER_TYPES = [
        ('cashbox_to_cashbox', _('من صندوق إلى صندوق')),
        ('cashbox_to_bank', _('من صندوق إلى بنك')),
        ('bank_to_cashbox', _('من بنك إلى صندوق')),
    ]
    
    transfer_number = models.CharField(_('Transfer Number'), max_length=50, unique=True)
    transfer_type = models.CharField(_('نوع التحويل'), max_length=20, choices=TRANSFER_TYPES)
    date = models.DateField(_('Date'))
    
    # الصناديق
    from_cashbox = models.ForeignKey(Cashbox, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name=_('من الصندوق'), related_name='transfers_from')
    to_cashbox = models.ForeignKey(Cashbox, on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name=_('إلى الصندوق'), related_name='transfers_to')
    
    # البنوك
    from_bank = models.ForeignKey('banks.BankAccount', on_delete=models.PROTECT, null=True, blank=True,
                                verbose_name=_('من البنك'), related_name='cashbox_transfers_from')
    to_bank = models.ForeignKey('banks.BankAccount', on_delete=models.PROTECT, null=True, blank=True,
                              verbose_name=_('إلى البنك'), related_name='cashbox_transfers_to')
    
    # حفظ أسماء الصناديق والبنوك في حالة الحذف
    from_cashbox_name = models.CharField(_('اسم الصندوق المرسل'), max_length=200, blank=True)
    to_cashbox_name = models.CharField(_('اسم الصندوق المستقبل'), max_length=200, blank=True)
    from_bank_name = models.CharField(_('اسم البنك المرسل'), max_length=200, blank=True)
    to_bank_name = models.CharField(_('اسم البنك المستقبل'), max_length=200, blank=True)
    
    # معلومات الإيداع للتحويل من الصندوق إلى البنك
    DEPOSIT_TYPES = [
        ('cash', _('نقداً')),
        ('check', _('شيك')),
    ]
    
    deposit_document_number = models.CharField(_('رقم مستند الإيداع'), max_length=50, blank=True)
    deposit_type = models.CharField(_('نوع الإيداع'), max_length=10, choices=DEPOSIT_TYPES, blank=True)
    check_number = models.CharField(_('رقم الشيك'), max_length=50, blank=True)
    check_date = models.DateField(_('تاريخ الشيك'), null=True, blank=True)
    check_bank_name = models.CharField(_('اسم بنك الشيك'), max_length=200, blank=True)
    
    amount = models.DecimalField(_('Amount'), max_digits=15, decimal_places=3)
    fees = models.DecimalField(_('Fees'), max_digits=15, decimal_places=3, default=0)
    exchange_rate = models.DecimalField(_('Exchange Rate'), max_digits=10, decimal_places=4, default=1)
    description = models.TextField(_('Description'), blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('تحويل صندوق')
        verbose_name_plural = _('تحويلات الصناديق')
        ordering = ['-date', '-transfer_number']

    def __str__(self):
        from_name = self.get_from_display_name()
        to_name = self.get_to_display_name()
        
        if from_name and to_name:
            return f"{self.transfer_number} - {from_name} -> {to_name}"
        return f"{self.transfer_number}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # التحقق من صحة نوع التحويل
        if self.transfer_type == 'cashbox_to_cashbox':
            if not self.from_cashbox or not self.to_cashbox:
                raise ValidationError(_('يجب تحديد الصندوق المرسل والمستقبل'))
            if self.from_cashbox == self.to_cashbox:
                raise ValidationError(_('لا يمكن التحويل من الصندوق إلى نفسه'))
        elif self.transfer_type == 'cashbox_to_bank':
            if not self.from_cashbox or not self.to_bank:
                raise ValidationError(_('يجب تحديد الصندوق المرسل والبنك المستقبل'))
            # التحقق من معلومات الإيداع
            if not self.deposit_document_number:
                raise ValidationError(_('رقم مستند الإيداع مطلوب للتحويل إلى البنك'))
            if not self.deposit_type:
                raise ValidationError(_('نوع الإيداع مطلوب'))
            # التحقق من معلومات الشيك
            if self.deposit_type == 'check':
                if not self.check_number:
                    raise ValidationError(_('رقم الشيك مطلوب عند اختيار نوع الإيداع "شيك"'))
                if not self.check_date:
                    raise ValidationError(_('تاريخ الشيك مطلوب'))
                if not self.check_bank_name:
                    raise ValidationError(_('اسم بنك الشيك مطلوب'))
        elif self.transfer_type == 'bank_to_cashbox':
            if not self.from_bank or not self.to_cashbox:
                raise ValidationError(_('يجب تحديد البنك المرسل والصندوق المستقبل'))
    
    def save(self, *args, **kwargs):
        # حفظ أسماء الصناديق والبنوك قبل الحفظ
        if self.from_cashbox:
            self.from_cashbox_name = self.from_cashbox.name
        if self.to_cashbox:
            self.to_cashbox_name = self.to_cashbox.name
        if self.from_bank:
            self.from_bank_name = self.from_bank.name
        if self.to_bank:
            self.to_bank_name = self.to_bank.name
            
        self.clean()
        # توليد رقم التحويل فقط إذا لم يكن موجوداً
        if not self.transfer_number:
            self.transfer_number = self.generate_transfer_number()
        super().save(*args, **kwargs)
    
    def generate_transfer_number(self):
        """توليد رقم التحويل باستخدام نظام تسلسل المستندات"""
        try:
            from core.models import DocumentSequence
            sequence = DocumentSequence.objects.get(document_type='cashbox_transfer')
            return sequence.get_next_number()
        except DocumentSequence.DoesNotExist:
            # في حالة عدم وجود تسلسل، استخدم الطريقة القديمة
            from django.utils import timezone
            prefix = 'CT'  # Cashbox Transfer
            date_str = timezone.now().strftime('%Y%m%d')
            
            # البحث عن آخر رقم في نفس اليوم
            last_transfer = CashboxTransfer.objects.filter(
                transfer_number__startswith=f'{prefix}{date_str}'
            ).order_by('-transfer_number').first()
            
            if last_transfer:
                last_number = int(last_transfer.transfer_number[-4:])
                new_number = last_number + 1
            else:
                new_number = 1
            
            return f'{prefix}{date_str}{new_number:04d}'

    def get_from_display_name(self):
        """الحصول على اسم المرسل للعرض"""
        if self.from_cashbox:
            return self.from_cashbox.name
        elif self.from_cashbox_name:
            return f"{self.from_cashbox_name} (محذوف)"
        elif self.from_bank:
            return self.from_bank.name
        elif self.from_bank_name:
            return f"{self.from_bank_name} (محذوف)"
        return ""
    
    def get_to_display_name(self):
        """الحصول على اسم المستقبل للعرض"""
        if self.to_cashbox:
            return self.to_cashbox.name
        elif self.to_cashbox_name:
            return f"{self.to_cashbox_name} (محذوف)"
        elif self.to_bank:
            return self.to_bank.name
        elif self.to_bank_name:
            return f"{self.to_bank_name} (محذوف)"
        return ""
    
    def get_from_icon(self):
        """الحصول على أيقونة المرسل"""
        if self.from_cashbox or self.from_cashbox_name:
            return "fas fa-box"
        elif self.from_bank or self.from_bank_name:
            return "fas fa-university"
        return ""
    
    def get_to_icon(self):
        """الحصول على أيقونة المستقبل"""
        if self.to_cashbox or self.to_cashbox_name:
            return "fas fa-box"
        elif self.to_bank or self.to_bank_name:
            return "fas fa-university"
        return ""


class CashboxTransaction(models.Model):
    """حركة الصندوق"""
    TRANSACTION_TYPES = [
        ('deposit', _('Deposit')),
        ('withdrawal', _('Withdrawal')),
        ('transfer_in', _('تحويل وارد')),
        ('transfer_out', _('تحويل صادر')),
        ('initial_balance', _('رصيد افتتاحي')),
        ('adjustment', _('تسوية')),
    ]
    
    cashbox = models.ForeignKey(Cashbox, on_delete=models.PROTECT, verbose_name=_('الصندوق'))
    transaction_type = models.CharField(_('Transaction Type'), max_length=20, choices=TRANSACTION_TYPES)
    date = models.DateField(_('Date'))
    amount = models.DecimalField(_('Amount'), max_digits=15, decimal_places=3)
    description = models.TextField(_('Description'), blank=True)
    
    # ربط بالتحويل إذا كانت الحركة من تحويل
    related_transfer = models.ForeignKey(CashboxTransfer, on_delete=models.CASCADE, 
                                       null=True, blank=True, verbose_name=_('التحويل المرتبط'))
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('حركة صندوق')
        verbose_name_plural = _('حركات الصناديق')
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.cashbox.name} - {self.get_transaction_type_display()} - {self.amount}"
