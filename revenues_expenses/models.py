from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from django.core.validators import MinValueValidator


class Sector(models.Model):
    """Sectors or packages for classifying revenues and expenses"""
    name = models.CharField(max_length=200, verbose_name=_('Sector Name'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Description'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('Sector')
        verbose_name_plural = _('Sectors')
        ordering = ['name']
        default_permissions = []  # No default permissions
        permissions = [
            ("can_view_sectors", _("View Sectors")),
            ("can_add_sectors", _("Add Sectors")),
            ("can_edit_sectors", _("Edit Sectors")),
            ("can_delete_sectors", _("Delete Sectors")),
        ]
    
    def __str__(self):
        return self.name


class RevenueExpenseCategory(models.Model):
    """Revenue and Expense Categories"""
    CATEGORY_TYPES = [
        ('revenue', _('Revenue')),
        ('expense', _('Expense')),
    ]
    
    name = models.CharField(max_length=200, verbose_name=_('Category Name'))
    type = models.CharField(max_length=20, choices=CATEGORY_TYPES, verbose_name=_('Category Type'))
    account = models.ForeignKey('journal.Account', on_delete=models.PROTECT, verbose_name=_('Accounting Account'), 
                               limit_choices_to={'account_type__in': ['revenue', 'expense']}, null=True, blank=True)
    description = models.TextField(blank=True, null=True, verbose_name=_('Description'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('Revenue/Expense Category')
        verbose_name_plural = _('Revenue/Expense Categories')
        ordering = ['type', 'name']
        default_permissions = []  # No default permissions
        permissions = [
            ("can_view_categories", _("View Revenue/Expense Categories")),
            ("can_add_categories", _("Add Revenue/Expense Categories")),
            ("can_edit_categories", _("Edit Revenue/Expense Categories")),
            ("can_delete_categories", _("Delete Revenue/Expense Categories")),
        ]
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.name}"


class RevenueExpenseEntry(models.Model):
    """Revenue and Expense Entries"""
    ENTRY_TYPES = [
        ('revenue', _('Revenue')),
        ('expense', _('Expense')),
    ]
    
    PAYMENT_METHODS = [
        ('cash', _('Cash')),
        ('bank', _('Bank')),
        ('cheque', _('Cheque')),
        ('transfer', _('Transfer')),
    ]
    
    entry_number = models.CharField(max_length=50, unique=True, verbose_name=_('Entry Number'))
    type = models.CharField(max_length=20, choices=ENTRY_TYPES, verbose_name=_('Entry Type'))
    category = models.ForeignKey(RevenueExpenseCategory, on_delete=models.CASCADE, verbose_name=_('Category'))
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Sector'))
    amount = models.DecimalField(max_digits=15, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))], verbose_name=_('Amount'))
    
    # Add currency field
    currency = models.ForeignKey('settings.Currency', on_delete=models.PROTECT, null=True, blank=True, verbose_name=_('Currency'))
    
    description = models.TextField(verbose_name=_('Description'))
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash', verbose_name=_('Payment Method'))
    reference_number = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Reference Number'))
    date = models.DateField(verbose_name=_('Date'))
    
    # Related accounts - will be added later
    # debit_account = models.CharField(max_length=100, verbose_name=_('Debit Account'))
    # credit_account = models.CharField(max_length=100, verbose_name=_('Credit Account'))
    
    # Additional information
    is_approved = models.BooleanField(default=False, verbose_name=_('Approved'))
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_revenue_expenses', verbose_name=_('Approved By'))
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Approval Date'))
    
    # Tracking information
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('Revenue/Expense Entry')
        verbose_name_plural = _('Revenue/Expense Entries')
        ordering = ['-date', '-created_at']
        default_permissions = []  # No default permissions
        permissions = [
            ("can_view_entries", _("View Revenue/Expense Entries")),
            ("can_add_entries", _("Add Revenue/Expense Entries")),
            ("can_edit_entries", _("Edit Revenue/Expense Entries")),
            ("can_delete_entries", _("Delete Revenue/Expense Entries")),
        ]
    
    def __str__(self):
        return f"{self.entry_number} - {self.get_type_display()} - {self.amount}"
    
    def save(self, *args, **kwargs):
        # Add default currency if not specified
        if not self.currency:
            from settings.models import CompanySettings
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                self.currency = company_settings.base_currency
        
        if not self.entry_number:
            # Generate automatic entry number
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
        """Generate new entry number"""
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
    """Recurring Revenues and Expenses"""
    FREQUENCY_CHOICES = [
        ('daily', _('Daily')),
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
        ('quarterly', _('Quarterly')),
        ('semi_annual', _('Semi-Annual')),
        ('annual', _('Annual')),
    ]
    
    name = models.CharField(max_length=200, verbose_name=_('Recurring Revenue/Expense Name'))
    category = models.ForeignKey(RevenueExpenseCategory, on_delete=models.CASCADE, verbose_name=_('Category'))
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Sector'))
    amount = models.DecimalField(max_digits=15, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))], verbose_name=_('Amount'))
    
    # Add currency field
    currency = models.ForeignKey('settings.Currency', on_delete=models.PROTECT, null=True, blank=True, verbose_name=_('Currency'))
    
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, verbose_name=_('Frequency'))
    start_date = models.DateField(verbose_name=_('Start Date'))
    end_date = models.DateField(null=True, blank=True, verbose_name=_('End Date'))
    last_generated = models.DateField(null=True, blank=True, verbose_name=_('Last Generation Date'))
    next_due_date = models.DateField(verbose_name=_('Next Due Date'))
    description = models.TextField(verbose_name=_('Description'))
    payment_method = models.CharField(max_length=20, choices=RevenueExpenseEntry.PAYMENT_METHODS, default='cash', verbose_name=_('Payment Method'))
    
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    auto_generate = models.BooleanField(default=True, verbose_name=_('Auto Generate'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('Recurring Revenue/Expense')
        verbose_name_plural = _('Recurring revenues and expenses')
        ordering = ['next_due_date']
        default_permissions = []  # No default permissions
        permissions = [
            ("can_view_recurring", _("View Recurring Revenue/Expense")),
            ("can_add_recurring", _("Add Recurring Revenue/Expense")),
            ("can_edit_recurring", _("Edit Recurring Revenue/Expense")),
            ("can_delete_recurring", _("Delete Recurring Revenue/Expense")),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()}"
    
    def save(self, *args, **kwargs):
        # Add default currency if not specified
        if not self.currency:
            from settings.models import CompanySettings
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                self.currency = company_settings.base_currency
        
        super().save(*args, **kwargs)
