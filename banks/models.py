from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()


class BankAccount(models.Model):
    """الحساب البنكي"""
    name = models.CharField(_('اسم الحساب'), max_length=200)
    bank_name = models.CharField(_('اسم البنك'), max_length=200)
    account_number = models.CharField(_('رقم الحساب'), max_length=50)
    iban = models.CharField(_('IBAN'), max_length=50, blank=True)
    swift_code = models.CharField(_('رمز SWIFT'), max_length=20, blank=True)
    balance = models.DecimalField(_('الرصيد'), max_digits=15, decimal_places=3, default=0)
    initial_balance = models.DecimalField(_('الرصيد الأولي'), max_digits=15, decimal_places=3, default=0, help_text="الرصيد الأولي للحساب عند بداية التشغيل")
    currency = models.CharField(_('العملة'), max_length=10, blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('حساب بنكي')
        verbose_name_plural = _('الحسابات البنكية')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.bank_name}"
    
    def save(self, *args, **kwargs):
        """إذا لم يتم تحديد العملة، استخدم العملة الأساسية من إعدادات الشركة"""
        # تحديد الرصيد الأولي تلقائياً إذا لم يكن محدداً
        if not self.pk and self.initial_balance == 0:  # حساب جديد وليس له رصيد أولي
            self.initial_balance = self.balance  # استخدم الرصيد المدخل كرصيد أولي
        
        if not self.currency:
            from settings.models import Currency, CompanySettings
            # أولاً: البحث في إعدادات الشركة
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                self.currency = company_settings.base_currency.code
            else:
                # ثانياً: البحث عن العملة الأساسية في النظام
                base_currency = Currency.get_base_currency()
                if base_currency:
                    self.currency = base_currency.code
                # إذا لم توجد عملة، لا نضع أي عملة افتراضية
        super().save(*args, **kwargs)
    
    def get_currency_symbol(self):
        """الحصول على رمز العملة"""
        from settings.models import Currency
        currency = Currency.objects.filter(code=self.currency).first()
        if currency:
            return currency.symbol if currency.symbol else currency.code
        return self.currency
    
    def calculate_actual_balance(self):
        """حساب الرصيد الفعلي من جميع المعاملات"""
        from decimal import Decimal
        
        # استخدام الرصيد الأولي المحفوظ في قاعدة البيانات
        initial_balance = self.initial_balance or Decimal('0')
        
        # حساب مجموع الإيداعات
        deposits = self.transactions.filter(
            transaction_type='deposit'
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        
        # حساب مجموع السحوبات
        withdrawals = self.transactions.filter(
            transaction_type='withdrawal'
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        
        # الرصيد الفعلي = الرصيد الأولي + الإيداعات - السحوبات
        actual_balance = initial_balance + deposits - withdrawals
        return actual_balance
    
    def sync_balance(self):
        """مزامنة الرصيد المحفوظ مع الرصيد الفعلي"""
        from decimal import Decimal
        
        actual_balance = self.calculate_actual_balance()
        if self.balance != actual_balance:
            self.balance = actual_balance
            self.save(update_fields=['balance'])
        return actual_balance


class BankTransfer(models.Model):
    """التحويل البنكي"""
    transfer_number = models.CharField(_('رقم التحويل'), max_length=50, unique=True)
    date = models.DateField(_('التاريخ'))
    from_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, 
                                   verbose_name=_('من الحساب'), related_name='transfers_from')
    to_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, 
                                 verbose_name=_('إلى الحساب'), related_name='transfers_to')
    amount = models.DecimalField(_('المبلغ'), max_digits=15, decimal_places=3)
    fees = models.DecimalField(_('الرسوم'), max_digits=15, decimal_places=3, default=0)
    exchange_rate = models.DecimalField(_('سعر الصرف'), max_digits=10, decimal_places=4, default=1)
    description = models.TextField(_('الوصف'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('أنشئ بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('تحويل بنكي')
        verbose_name_plural = _('التحويلات البنكية')
        ordering = ['-date', '-transfer_number']

    def __str__(self):
        return f"{self.transfer_number} - {self.from_account.name} -> {self.to_account.name}"


class BankTransaction(models.Model):
    """حركة الحساب البنكي"""
    TRANSACTION_TYPES = [
        ('deposit', _('إيداع')),
        ('withdrawal', _('سحب')),
    ]
    
    bank = models.ForeignKey(BankAccount, on_delete=models.PROTECT, 
                           verbose_name=_('الحساب البنكي'), related_name='transactions')
    transaction_type = models.CharField(_('نوع الحركة'), max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(_('المبلغ'), max_digits=15, decimal_places=3)
    description = models.TextField(_('الوصف'))
    reference_number = models.CharField(_('الرقم المرجعي'), max_length=100, blank=True)
    date = models.DateField(_('التاريخ'))
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('أنشئ بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('حركة بنكية')
        verbose_name_plural = _('الحركات البنكية')
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.bank.name} - {self.get_transaction_type_display()} - {self.amount}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # تحديث رصيد البنك
        self.update_bank_balance()
    
    def update_bank_balance(self):
        """تحديث رصيد الحساب البنكي"""
        # استخدام sync_balance بدلاً من الحساب اليدوي
        self.bank.sync_balance()
