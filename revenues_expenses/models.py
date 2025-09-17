from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from django.core.validators import MinValueValidator


class RevenueExpenseCategory(models.Model):
    """فئات الإيرادات والمصروفات"""
    CATEGORY_TYPES = [
        ('revenue', _('إيراد')),
        ('expense', _('مصروف')),
    ]
    
    name = models.CharField(max_length=200, verbose_name=_('اسم الفئة'))
    type = models.CharField(max_length=20, choices=CATEGORY_TYPES, verbose_name=_('نوع الفئة'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Description'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('فئة الإيرادات والمصروفات')
        verbose_name_plural = _('فئات الإيرادات والمصروفات')
        ordering = ['type', 'name']
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.name}"


class RevenueExpenseEntry(models.Model):
    """قيود الإيرادات والمصروفات"""
    ENTRY_TYPES = [
        ('revenue', _('إيراد')),
        ('expense', _('مصروف')),
    ]
    
    PAYMENT_METHODS = [
        ('cash', _('نقدي')),
        ('bank', _('بنكي')),
        ('cheque', _('شيك')),
        ('transfer', _('تحويل')),
    ]
    
    entry_number = models.CharField(max_length=50, unique=True, verbose_name=_('رقم القيد'))
    type = models.CharField(max_length=20, choices=ENTRY_TYPES, verbose_name=_('نوع القيد'))
    category = models.ForeignKey(RevenueExpenseCategory, on_delete=models.CASCADE, verbose_name=_('الفئة'))
    amount = models.DecimalField(max_digits=15, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))], verbose_name=_('Amount'))
    
    # إضافة حقل العملة
    currency = models.ForeignKey('settings.Currency', on_delete=models.PROTECT, null=True, blank=True, verbose_name=_('Currency'))
    
    description = models.TextField(verbose_name=_('Description'))
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash', verbose_name=_('طريقة الدفع'))
    reference_number = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('رقم المرجع'))
    date = models.DateField(verbose_name=_('Date'))
    
    # الحسابات المرتبطة - سيتم إضافتها لاحقاً
    # debit_account = models.CharField(max_length=100, verbose_name=_('حساب المدين'))
    # credit_account = models.CharField(max_length=100, verbose_name=_('حساب الدائن'))
    
    # معلومات إضافية
    is_approved = models.BooleanField(default=False, verbose_name=_('معتمد'))
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_revenue_expenses', verbose_name=_('اعتمد بواسطة'))
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name=_('تاريخ الاعتماد'))
    
    # معلومات التتبع
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('قيد الإيرادات والمصروفات')
        verbose_name_plural = _('قيود الإيرادات والمصروفات')
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.entry_number} - {self.get_type_display()} - {self.amount}"
    
    def save(self, *args, **kwargs):
        # إضافة العملة الافتراضية إذا لم تكن محددة
        if not self.currency:
            from settings.models import CompanySettings
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                self.currency = company_settings.base_currency
        
        if not self.entry_number:
            # توليد رقم قيد تلقائي
            prefix = 'RE' if self.type == 'revenue' else 'EX'
            last_entry = RevenueExpenseEntry.objects.filter(
                type=self.type,
                entry_number__startswith=prefix
            ).order_by('-id').first()
            
            if last_entry:
                try:
                    last_number = int(last_entry.entry_number.replace(prefix, ''))
                    new_number = last_number + 1
                except:
                    new_number = 1
            else:
                new_number = 1
            
            self.entry_number = f"{prefix}{new_number:06d}"
        
        super().save(*args, **kwargs)
    
    def generate_entry_number(self):
        """توليد رقم قيد جديد"""
        prefix = 'RE' if self.type == 'revenue' else 'EX'
        last_entry = RevenueExpenseEntry.objects.filter(
            type=self.type,
            entry_number__startswith=prefix
        ).order_by('-id').first()
        
        if last_entry:
            try:
                last_number = int(last_entry.entry_number.replace(prefix, ''))
                new_number = last_number + 1
            except:
                new_number = 1
        else:
            new_number = 1
        
        return f"{prefix}{new_number:06d}"


class RecurringRevenueExpense(models.Model):
    """الإيرادات والمصروفات المتكررة"""
    FREQUENCY_CHOICES = [
        ('daily', _('يومي')),
        ('weekly', _('أسبوعي')),
        ('monthly', _('شهري')),
        ('quarterly', _('ربع سنوي')),
        ('semi_annual', _('نصف سنوي')),
        ('annual', _('سنوي')),
    ]
    
    name = models.CharField(max_length=200, verbose_name=_('اسم الإيراد/المصروف المتكرر'))
    category = models.ForeignKey(RevenueExpenseCategory, on_delete=models.CASCADE, verbose_name=_('الفئة'))
    amount = models.DecimalField(max_digits=15, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))], verbose_name=_('Amount'))
    
    # إضافة حقل العملة
    currency = models.ForeignKey('settings.Currency', on_delete=models.PROTECT, null=True, blank=True, verbose_name=_('Currency'))
    
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, verbose_name=_('التكرار'))
    start_date = models.DateField(verbose_name=_('تاريخ البداية'))
    end_date = models.DateField(null=True, blank=True, verbose_name=_('تاريخ النهاية'))
    last_generated = models.DateField(null=True, blank=True, verbose_name=_('آخر تاريخ توليد'))
    next_due_date = models.DateField(verbose_name=_('التاريخ المستحق التالي'))
    description = models.TextField(verbose_name=_('Description'))
    payment_method = models.CharField(max_length=20, choices=RevenueExpenseEntry.PAYMENT_METHODS, default='cash', verbose_name=_('طريقة الدفع'))
    
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    auto_generate = models.BooleanField(default=True, verbose_name=_('توليد تلقائي'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('الإيراد/المصروف المتكرر')
        verbose_name_plural = _('Recurring revenues and expenses')
        ordering = ['next_due_date']
    
    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()}"
    
    def save(self, *args, **kwargs):
        # إضافة العملة الافتراضية إذا لم تكن محددة
        if not self.currency:
            from settings.models import CompanySettings
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                self.currency = company_settings.base_currency
        
        super().save(*args, **kwargs)
