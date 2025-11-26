from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from django.core.validators import MinValueValidator

User = settings.AUTH_USER_MODEL


class ProvisionType(models.Model):
    """Provision Types"""
    name = models.CharField(_('Type Name'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Created By'))

    class Meta:
        verbose_name = _('Provision Type')
        verbose_name_plural = _('Provision Types')
        ordering = ['name']

    def __str__(self):
        return self.name


class Provision(models.Model):
    """Accounting Provisions"""
    PROVISION_TYPES = [
        ('bad_debt', _('Bad Debt Provision')),
        ('depreciation', _('Depreciation Provision')),
        ('inventory', _('Inventory Provision')),
        ('warranty', _('Warranty Provision')),
        ('tax', _('Tax Provision')),
        ('other', _('Other Provisions')),
    ]

    provision_type = models.CharField(_('Provision Type'), max_length=20, choices=PROVISION_TYPES)
    custom_type = models.ForeignKey(ProvisionType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Custom Provision Type'))
    name = models.CharField(_('Provision Name'), max_length=200)
    description = models.TextField(_('Description'), blank=True)

    # Link to accounts
    related_account = models.ForeignKey('journal.Account', on_delete=models.CASCADE, verbose_name=_('Related Account'))
    provision_account = models.ForeignKey('journal.Account', on_delete=models.CASCADE, verbose_name=_('Provision Account'), related_name='provisions')

    # Amounts and periods
    amount = models.DecimalField(_('Amount'), max_digits=15, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    accumulated_amount = models.DecimalField(_('Accumulated Amount'), max_digits=15, decimal_places=3, default=0)
    fiscal_year = models.IntegerField(_('Fiscal Year'))
    start_date = models.DateField(_('Start Date'))
    end_date = models.DateField(_('End Date'), null=True, blank=True)

    # Status and approval
    is_active = models.BooleanField(_('Active'), default=True)
    is_approved = models.BooleanField(_('Approved'), default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_provisions', verbose_name=_('Approved By'))
    approved_at = models.DateTimeField(_('Approval Date'), null=True, blank=True)

    # Tracking information
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Created By'))

    class Meta:
        verbose_name = _('Provision')
        verbose_name_plural = _('Provisions')
        ordering = ['-fiscal_year', '-created_at']
        unique_together = ['provision_type', 'related_account', 'fiscal_year']

    def __str__(self):
        return f"{self.get_provision_type_display()} - {self.name} - {self.fiscal_year}"

    def save(self, *args, **kwargs):
        # Update accumulated amount
        if not self.pk:  # New
            self.accumulated_amount = self.amount
        else:  # Update
            # Can add logic to update accumulated amount
            pass
        super().save(*args, **kwargs)


class ProvisionEntry(models.Model):
    """Provision entries"""
    provision = models.ForeignKey(Provision, on_delete=models.CASCADE, verbose_name=_('Provision'))
    date = models.DateField(_('Date'))
    amount = models.DecimalField(_('Amount'), max_digits=15, decimal_places=3)
    description = models.TextField(_('Description'), blank=True)

    # Link to journal entry
    journal_entry = models.ForeignKey('journal.JournalEntry', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Journal Entry'))

    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Created By'))

    class Meta:
        verbose_name = _('Provision Entry')
        verbose_name_plural = _('Provision Entries')
        ordering = ['-date']

    def __str__(self):
        return f"{self.provision.name} - {self.date} - {self.amount}"
