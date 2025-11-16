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
        ('current', _('Current Assets')),
        ('fixed', _('Fixed Assets')),
        ('intangible', _('Intangible Assets')),
        ('investment', _('Investments')),
    ]
    
    name = models.CharField(max_length=200, verbose_name=_('Category Name'))
    type = models.CharField(max_length=20, choices=ASSET_TYPES, verbose_name=_('Asset Type'))
    account = models.ForeignKey('journal.Account', on_delete=models.PROTECT, verbose_name=_('Accounting Account'), 
                               limit_choices_to={'account_type': 'asset'}, null=True, blank=True)
    description = models.TextField(blank=True, null=True, verbose_name=_('Description'))
    depreciation_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_('Depreciation Rate %'))
    useful_life_years = models.IntegerField(default=0, verbose_name=_('Useful Life Years'))
    is_depreciable = models.BooleanField(default=False, verbose_name=_('Depreciable'))
    depreciation_expense_account = models.ForeignKey('journal.Account', on_delete=models.SET_NULL, null=True, blank=True, 
                                                   verbose_name=_('Depreciation Expense Account'), 
                                                   limit_choices_to={'account_type': 'expense'},
                                                   related_name='depreciation_expense_categories')
    accumulated_depreciation_account = models.ForeignKey('journal.Account', on_delete=models.SET_NULL, null=True, blank=True, 
                                                       verbose_name=_('Accumulated Depreciation Account'), 
                                                       limit_choices_to={'account_type': 'asset'},
                                                       related_name='accumulated_depreciation_categories')
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('Asset Category')
        verbose_name_plural = _('Asset Categories')
        ordering = ['type', 'name']
        default_permissions = []  # No default permissions
        permissions = [
            ("can_view_asset_categories", _("View Asset Categories")),
            ("can_add_asset_categories", _("Add Asset Categories")),
            ("can_edit_asset_categories", _("Edit Asset Categories")),
            ("can_delete_asset_categories", _("Delete Asset Categories")),
        ]
    
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
    
    asset_number = models.CharField(max_length=50, unique=True, verbose_name=_('Asset Number'))
    name = models.CharField(max_length=200, verbose_name=_('Asset Name'))
    category = models.ForeignKey(AssetCategory, on_delete=models.CASCADE, verbose_name=_('Category'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Description'))
    
    # معلومات مالية
    purchase_cost = models.DecimalField(max_digits=15, decimal_places=3, validators=[MinValueValidator(Decimal('0'))], verbose_name=_('Purchase Cost'))
    current_value = models.DecimalField(max_digits=15, decimal_places=3, validators=[MinValueValidator(Decimal('0'))], verbose_name=_('Current Value'))
    accumulated_depreciation = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name=_('Accumulated Depreciation'))
    salvage_value = models.DecimalField(max_digits=15, decimal_places=3, default=0, verbose_name=_('Salvage Value'))
    
    # إضافة حقل العملة
    currency = models.ForeignKey('settings.Currency', on_delete=models.PROTECT, null=True, blank=True, verbose_name=_('Currency'))
    
    # معلومات الشراء
    purchase_date = models.DateField(verbose_name=_('Purchase Date'))
    supplier = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('Supplier'))
    invoice_number = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Invoice Number'))
    warranty_expiry = models.DateField(blank=True, null=True, verbose_name=_('Warranty Expiry'))
    
    # معلومات الموقع والحالة
    location = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('Location'))
    responsible_person = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='responsible_assets', verbose_name=_('Responsible Person'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name=_('Status'))
    
    # الإهلاك
    depreciation_method = models.CharField(max_length=50, default='straight_line', verbose_name=_('Depreciation Method'))
    last_depreciation_date = models.DateField(blank=True, null=True, verbose_name=_('Last Depreciation Date'))
    
    # معلومات التتبع
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('Asset')
        verbose_name_plural = _('Assets')
        ordering = ['-purchase_date']
        default_permissions = []  # No default permissions
        permissions = [
            ("can_view_assets", _("View Assets")),
            ("can_add_assets", _("Add Assets")),
            ("can_edit_assets", _("Edit Assets")),
            ("can_delete_assets", _("Delete Assets")),
        ]
    
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
        ('current', _('Current Liabilities')),
        ('long_term', _('Long-term Liabilities')),
        ('equity', _('Equity')),
    ]
    
    name = models.CharField(max_length=200, verbose_name=_('Category Name'))
    type = models.CharField(max_length=20, choices=LIABILITY_TYPES, verbose_name=_('Liability Type'))
    account = models.ForeignKey('journal.Account', on_delete=models.PROTECT, verbose_name=_('Accounting Account'), 
                               limit_choices_to={'account_type__in': ['liability', 'equity']}, null=True, blank=True)
    description = models.TextField(blank=True, null=True, verbose_name=_('Description'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('Liability Category')
        verbose_name_plural = _('Liability Categories')
        ordering = ['type', 'name']
        default_permissions = []  # No default permissions
        permissions = [
            ("can_view_liability_categories", _("View Liability Categories")),
            ("can_add_liability_categories", _("Add Liability Categories")),
            ("can_edit_liability_categories", _("Edit Liability Categories")),
            ("can_delete_liability_categories", _("Delete Liability Categories")),
        ]
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.name}"


class Liability(models.Model):
    """الخصوم"""
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('paid', _('Paid')),
        ('overdue', _('Overdue')),
        ('cancelled', _('Cancelled')),
    ]
    
    liability_number = models.CharField(max_length=50, unique=True, verbose_name=_('Liability Number'))
    name = models.CharField(max_length=200, verbose_name=_('Liability Name'))
    category = models.ForeignKey(LiabilityCategory, on_delete=models.CASCADE, verbose_name=_('Category'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Description'))
    
    # معلومات مالية
    original_amount = models.DecimalField(max_digits=15, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))], verbose_name=_('Original Amount'))
    current_balance = models.DecimalField(max_digits=15, decimal_places=3, validators=[MinValueValidator(Decimal('0'))], verbose_name=_('Current Balance'))
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_('Interest Rate %'))
    
    # إضافة حقل العملة
    currency = models.ForeignKey('settings.Currency', on_delete=models.PROTECT, null=True, blank=True, verbose_name=_('Currency'))
    
    # معلومات التواريخ
    start_date = models.DateField(verbose_name=_('Start Date'))
    due_date = models.DateField(verbose_name=_('Due Date'))
    last_payment_date = models.DateField(blank=True, null=True, verbose_name=_('Last Payment Date'))
    
    # معلومات الطرف الآخر
    creditor_name = models.CharField(max_length=200, verbose_name=_('Creditor Name'))
    creditor_contact = models.CharField(max_length=200, blank=True, null=True, verbose_name=_('Contact Information'))
    contract_number = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Contract Number'))
    
    # معلومات الحالة
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name=_('Status'))
    
    # معلومات التتبع
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('Liability')
        verbose_name_plural = _('Liabilities')
        ordering = ['due_date']
        default_permissions = []  # No default permissions
        permissions = [
            ("can_view_liabilities", _("View Liabilities")),
            ("can_add_liabilities", _("Add Liabilities")),
            ("can_edit_liabilities", _("Edit Liabilities")),
            ("can_delete_liabilities", _("Delete Liabilities")),
        ]
    
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
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, verbose_name=_('Asset'))
    depreciation_date = models.DateField(verbose_name=_('Depreciation Date'))
    depreciation_amount = models.DecimalField(max_digits=15, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))], verbose_name=_('Depreciation Amount'))
    accumulated_depreciation_before = models.DecimalField(max_digits=15, decimal_places=3, verbose_name=_('Accumulated Depreciation Before'))
    accumulated_depreciation_after = models.DecimalField(max_digits=15, decimal_places=3, verbose_name=_('Accumulated Depreciation After'))
    net_book_value_after = models.DecimalField(max_digits=15, decimal_places=3, verbose_name=_('Net Book Value After'))
    notes = models.TextField(blank=True, null=True, verbose_name=_('Notes'))
    
    # إضافة حقل العملة
    currency = models.ForeignKey('settings.Currency', on_delete=models.PROTECT, null=True, blank=True, verbose_name=_('Currency'))
    
    # معلومات التتبع
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('Depreciation Entry')
        verbose_name_plural = _('Depreciation Entries')
        ordering = ['-depreciation_date']
        default_permissions = []
        permissions = [
            ('can_view_depreciation_entries', _('View Depreciation Entries')),
            ('can_add_depreciation_entries', _('Add Depreciation Entries')),
            ('can_edit_depreciation_entries', _('Edit Depreciation Entries')),
            ('can_delete_depreciation_entries', _('Delete Depreciation Entries')),
        ]
    
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
