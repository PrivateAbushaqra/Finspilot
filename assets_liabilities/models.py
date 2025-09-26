from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model

User = get_user_model()


class AssetCategory(models.Model):
    """فئات الأصول"""
    ASSET_TYPES = [
        ('current', _('أصول متداولة')),
        ('fixed', _('أصول ثابتة')),
        ('intangible', _('أصول غير ملموسة')),
        ('investment', _('استثمارات')),
    ]
    
    name = models.CharField(max_length=200, verbose_name=_('اسم الفئة'))
    type = models.CharField(max_length=20, choices=ASSET_TYPES, verbose_name=_('نوع الأصل'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Description'))
    # account = models.CharField(max_length=100, verbose_name=_('الحساب'))  # سيتم إضافة ربط الحسابات لاحقاً
    depreciation_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_('معدل الإهلاك %'))
    useful_life_years = models.IntegerField(default=0, verbose_name=_('العمر الافتراضي بالسنوات'))
    is_depreciable = models.BooleanField(default=False, verbose_name=_('قابل للإهلاك'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('فئة الأصل')
        verbose_name_plural = _('فئات الأصول')
        ordering = ['type', 'name']
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.name}"


class Asset(models.Model):
    """الأصول"""
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('maintenance', _('Under Maintenance')),
        ('disposed', _('Disposed')),
        ('sold', _('Sold')),
    ]
    
    asset_number = models.CharField(max_length=50, unique=True, verbose_name=_('رقم الأصل'))
    name = models.CharField(max_length=200, verbose_name=_('اسم الأصل'))
    category = models.ForeignKey(AssetCategory, on_delete=models.CASCADE, verbose_name=_('الفئة'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Description'))
    
    # معلومات مالية
    purchase_cost = models.DecimalField(max_digits=15, decimal_places=3, validators=[MinValueValidator(Decimal('0'))], verbose_name=_('تكلفة الشراء'))
    current_value = models.DecimalField(max_digits=15, decimal_places=3, validators=[MinValueValidator(Decimal('0'))], verbose_name=_('القيمة الحالية'))
    accumulated_depreciation = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name=_('مجمع الإهلاك'))
    salvage_value = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name=_('القيمة التخريدية'))
    
    # إضافة حقل العملة
    currency = models.ForeignKey('settings.Currency', on_delete=models.PROTECT, null=True, blank=True, verbose_name=_('Currency'))
    
    # معلومات الشراء
    purchase_date = models.DateField(verbose_name=_('تاريخ الشراء'))
    supplier = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('Supplier'))
    invoice_number = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('رقم الفاتورة'))
    warranty_expiry = models.DateField(blank=True, null=True, verbose_name=_('انتهاء الضمان'))
    
    # معلومات الموقع والحالة
    location = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('الموقع'))
    responsible_person = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='responsible_assets', verbose_name=_('الشخص المسؤول'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name=_('الحالة'))
    
    # الإهلاك
    depreciation_method = models.CharField(max_length=50, default='straight_line', verbose_name=_('طريقة الإهلاك'))
    last_depreciation_date = models.DateField(blank=True, null=True, verbose_name=_('تاريخ آخر إهلاك'))
    
    # معلومات التتبع
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('أصل')
        verbose_name_plural = _('الأصول')
        ordering = ['-purchase_date']
    
    def __str__(self):
        return f"{self.asset_number} - {self.name}"
    
    @property
    def net_book_value(self):
        """القيمة الدفترية الصافية"""
        return self.purchase_cost - self.accumulated_depreciation
    
    def save(self, *args, **kwargs):
        # إضافة العملة الافتراضية إذا لم تكن محددة
        if not self.currency:
            from settings.models import CompanySettings
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                self.currency = company_settings.base_currency
        
        if not self.asset_number:
            # توليد رقم أصل تلقائي
            last_asset = Asset.objects.order_by('-id').first()
            if last_asset:
                try:
                    last_number = int(last_asset.asset_number.replace('AST', ''))
                    new_number = last_number + 1
                except:
                    new_number = 1
            else:
                new_number = 1
            
            self.asset_number = f"AST{new_number:06d}"
        
        super().save(*args, **kwargs)


class LiabilityCategory(models.Model):
    """فئات الخصوم"""
    LIABILITY_TYPES = [
        ('current', _('خصوم متداولة')),
        ('long_term', _('خصوم طويلة الأجل')),
        ('equity', _('حقوق الملكية')),
    ]
    
    name = models.CharField(max_length=200, verbose_name=_('اسم الفئة'))
    type = models.CharField(max_length=20, choices=LIABILITY_TYPES, verbose_name=_('نوع الخصم'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Description'))
    # account = models.CharField(max_length=100, verbose_name=_('الحساب'))  # سيتم إضافة ربط الحسابات لاحقاً
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('فئة الخصم')
        verbose_name_plural = _('فئات الخصوم')
        ordering = ['type', 'name']
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.name}"


class Liability(models.Model):
    """الخصوم"""
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('paid', _('مسدد')),
        ('overdue', _('متأخر')),
        ('cancelled', _('ملغي')),
    ]
    
    liability_number = models.CharField(max_length=50, unique=True, verbose_name=_('رقم الخصم'))
    name = models.CharField(max_length=200, verbose_name=_('اسم الخصم'))
    category = models.ForeignKey(LiabilityCategory, on_delete=models.CASCADE, verbose_name=_('الفئة'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Description'))
    
    # معلومات مالية
    original_amount = models.DecimalField(max_digits=15, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))], verbose_name=_('المبلغ الأصلي'))
    current_balance = models.DecimalField(max_digits=15, decimal_places=3, validators=[MinValueValidator(Decimal('0'))], verbose_name=_('الرصيد الحالي'))
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_('معدل الفائدة %'))
    
    # إضافة حقل العملة
    currency = models.ForeignKey('settings.Currency', on_delete=models.PROTECT, null=True, blank=True, verbose_name=_('Currency'))
    
    # معلومات التواريخ
    start_date = models.DateField(verbose_name=_('تاريخ البداية'))
    due_date = models.DateField(verbose_name=_('تاريخ الاستحقاق'))
    last_payment_date = models.DateField(blank=True, null=True, verbose_name=_('تاريخ آخر دفعة'))
    
    # معلومات الطرف الآخر
    creditor_name = models.CharField(max_length=200, verbose_name=_('اسم الدائن'))
    creditor_contact = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('معلومات الاتصال'))
    contract_number = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('رقم العقد'))
    
    # معلومات الحالة
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name=_('الحالة'))
    
    # معلومات التتبع
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('خصم')
        verbose_name_plural = _('الخصوم')
        ordering = ['due_date']
    
    def __str__(self):
        return f"{self.liability_number} - {self.name}"
    
    def save(self, *args, **kwargs):
        # إضافة العملة الافتراضية إذا لم تكن محددة
        if not self.currency:
            from settings.models import CompanySettings
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                self.currency = company_settings.base_currency
        
        if not self.liability_number:
            # توليد رقم خصم تلقائي
            last_liability = Liability.objects.order_by('-id').first()
            if last_liability:
                try:
                    last_number = int(last_liability.liability_number.replace('LIB', ''))
                    new_number = last_number + 1
                except:
                    new_number = 1
            else:
                new_number = 1
            
            self.liability_number = f"LIB{new_number:06d}"
        
        super().save(*args, **kwargs)


class DepreciationEntry(models.Model):
    """قيود الإهلاك"""
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, verbose_name=_('الأصل'))
    depreciation_date = models.DateField(verbose_name=_('تاريخ الإهلاك'))
    depreciation_amount = models.DecimalField(max_digits=15, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))], verbose_name=_('مبلغ الإهلاك'))
    accumulated_depreciation_before = models.DecimalField(max_digits=15, decimal_places=3, verbose_name=_('مجمع الإهلاك قبل'))
    accumulated_depreciation_after = models.DecimalField(max_digits=15, decimal_places=3, verbose_name=_('مجمع الإهلاك بعد'))
    net_book_value_after = models.DecimalField(max_digits=15, decimal_places=3, verbose_name=_('القيمة الدفترية بعد'))
    notes = models.TextField(blank=True, null=True, verbose_name=_('Notes'))
    
    # إضافة حقل العملة
    currency = models.ForeignKey('settings.Currency', on_delete=models.PROTECT, null=True, blank=True, verbose_name=_('Currency'))
    
    # معلومات التتبع
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('قيد إهلاك')
        verbose_name_plural = _('قيود الإهلاك')
        ordering = ['-depreciation_date']
    
    def __str__(self):
        return f"{self.asset.name} - {self.depreciation_date} - {self.depreciation_amount}"
    
    def save(self, *args, **kwargs):
        # إضافة العملة الافتراضية إذا لم تكن محددة
        if not self.currency:
            # أخذ العملة من الأصل المرتبط
            if self.asset and self.asset.currency:
                self.currency = self.asset.currency
            else:
                from settings.models import CompanySettings
                company_settings = CompanySettings.objects.first()
                if company_settings and company_settings.base_currency:
                    self.currency = company_settings.base_currency
        
        super().save(*args, **kwargs)
