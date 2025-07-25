from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal

User = get_user_model()


class Account(models.Model):
    """دليل الحسابات المحاسبية"""
    ACCOUNT_TYPES = [
        ('asset', _('أصول')),
        ('liability', _('مطلوبات')),
        ('equity', _('حقوق ملكية')),
        ('revenue', _('إيرادات')),
        ('expense', _('مصاريف')),
        ('purchases', _('مشتريات')),
        ('sales', _('مبيعات')),
    ]

    code = models.CharField(_('كود الحساب'), max_length=20, unique=True)
    name = models.CharField(_('اسم الحساب'), max_length=100)
    account_type = models.CharField(_('نوع الحساب'), max_length=20, choices=ACCOUNT_TYPES)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                              verbose_name=_('الحساب الرئيسي'), related_name='children')
    description = models.TextField(_('الوصف'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    balance = models.DecimalField(_('الرصيد'), max_digits=15, decimal_places=3, default=0)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('حساب')
        verbose_name_plural = _('الحسابات')
        ordering = ['code', 'name']

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_balance(self):
        """حساب الرصيد الحالي للحساب"""
        lines = JournalLine.objects.filter(account=self)
        debit_total = lines.aggregate(total=models.Sum('debit'))['total'] or Decimal('0')
        credit_total = lines.aggregate(total=models.Sum('credit'))['total'] or Decimal('0')
        
        # الأصول والمصاريف ترتفع بالمدين
        if self.account_type in ['asset', 'expense', 'purchases']:
            return debit_total - credit_total
        # المطلوبات والإيرادات وحقوق الملكية ترتفع بالدائن
        else:
            return credit_total - debit_total


class JournalEntry(models.Model):
    """قيد محاسبي"""
    REFERENCE_TYPES = [
        ('sales_invoice', _('فاتورة مبيعات')),
        ('purchase_invoice', _('فاتورة مشتريات')),
        ('sales_return', _('مردود مبيعات')),
        ('purchase_return', _('مردود مشتريات')),
        ('receipt_voucher', _('سند قبض')),
        ('payment_voucher', _('سند صرف')),
        ('asset_depreciation', _('استهلاك الأصول')),
        ('manual', _('قيد يدوي')),
        ('adjustment', _('قيد تسوية')),
    ]

    entry_number = models.CharField(_('رقم القيد'), max_length=50, unique=True, blank=True)
    entry_date = models.DateField(_('تاريخ القيد'))
    reference_type = models.CharField(_('نوع العملية'), max_length=20, choices=REFERENCE_TYPES)
    reference_id = models.PositiveIntegerField(_('رقم العملية المرتبطة'), null=True, blank=True)
    description = models.TextField(_('وصف القيد'))
    total_amount = models.DecimalField(_('إجمالي المبلغ'), max_digits=15, decimal_places=3)
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('أنشئ بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('قيد محاسبي')
        verbose_name_plural = _('القيود المحاسبية')
        ordering = ['-entry_date', '-created_at']

    def __str__(self):
        return f"{self.entry_number} - {self.description}"

    def save(self, *args, **kwargs):
        if not self.entry_number:
            self.entry_number = self.generate_entry_number()
        super().save(*args, **kwargs)

    def generate_entry_number(self):
        """توليد رقم القيد"""
        from datetime import datetime
        
        # البحث عن آخر قيد في نفس السنة
        current_year = datetime.now().year
        last_entry = JournalEntry.objects.filter(
            entry_date__year=current_year
        ).order_by('-id').first()
        
        if last_entry and last_entry.entry_number:
            # استخراج الرقم من آخر قيد
            try:
                last_number = int(last_entry.entry_number.split('-')[-1])
                new_number = last_number + 1
            except (ValueError, IndexError):
                new_number = 1
        else:
            new_number = 1
        
        return f"JE-{current_year}-{new_number:04d}"

    def clean(self):
        """التحقق من توازن القيد"""
        if self.pk:  # إذا كان القيد محفوظًا بالفعل
            total_debit = self.lines.aggregate(total=models.Sum('debit'))['total'] or Decimal('0')
            total_credit = self.lines.aggregate(total=models.Sum('credit'))['total'] or Decimal('0')
            
            if total_debit != total_credit:
                raise ValidationError(_('يجب أن يكون مجموع المدين مساوياً لمجموع الدائن'))


class JournalLine(models.Model):
    """بند القيد المحاسبي"""
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, 
                                    verbose_name=_('القيد المحاسبي'), related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, 
                               verbose_name=_('الحساب'), related_name='journal_lines')
    debit = models.DecimalField(_('مدين'), max_digits=15, decimal_places=3, default=0)
    credit = models.DecimalField(_('دائن'), max_digits=15, decimal_places=3, default=0)
    line_description = models.TextField(_('تفاصيل البند'), blank=True)
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('بند قيد')
        verbose_name_plural = _('بنود القيود')

    def __str__(self):
        return f"{self.journal_entry.entry_number} - {self.account.name}"

    def clean(self):
        """التحقق من صحة البيانات"""
        if self.debit < 0 or self.credit < 0:
            raise ValidationError(_('المبالغ يجب أن تكون موجبة'))
        
        if self.debit > 0 and self.credit > 0:
            raise ValidationError(_('لا يمكن أن يكون البند مدين ودائن في نفس الوقت'))
        
        if self.debit == 0 and self.credit == 0:
            raise ValidationError(_('يجب إدخال مبلغ مدين أو دائن'))
