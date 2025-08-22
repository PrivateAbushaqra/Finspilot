from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()


class BankAccount(models.Model):
    """Bank Account"""
    name = models.CharField(_('Account Name'), max_length=200)
    bank_name = models.CharField(_('Bank Name'), max_length=200)
    account_number = models.CharField(_('Account Number'), max_length=50)
    iban = models.CharField(_('IBAN'), max_length=50, blank=True)
    swift_code = models.CharField(_('SWIFT Code'), max_length=20, blank=True)
    balance = models.DecimalField(_('Balance'), max_digits=15, decimal_places=3, default=0)
    initial_balance = models.DecimalField(_('Initial Balance'), max_digits=15, decimal_places=3, default=0, help_text=_("Initial account balance at the start of operations"))
    currency = models.CharField(_('Currency'), max_length=10, blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    notes = models.TextField(_('Notes'), blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Bank Account')
        verbose_name_plural = _('Bank Accounts')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.bank_name}"
    
    def save(self, *args, **kwargs):
        """If currency is not set, use the base currency from company settings"""
        # Set initial balance automatically if not specified
        if not self.pk and self.initial_balance == 0:  # New account with no initial balance
            self.initial_balance = self.balance  # Use entered balance as initial balance
        
        if not self.currency:
            from core.models import CompanySettings
            # Get currency from company settings
            company_settings = CompanySettings.get_settings()
            if company_settings and company_settings.currency:
                self.currency = company_settings.currency
            else:
                # If no currency found, use default currency
                self.currency = 'JOD'
        super().save(*args, **kwargs)
    
    def get_currency_symbol(self):
        """Get currency symbol"""
        from settings.models import Currency
        currency = Currency.objects.filter(code=self.currency).first()
        if currency:
            return currency.symbol if currency.symbol else currency.code
        return self.currency
    
    def calculate_actual_balance(self):
        """Calculate actual balance from all transactions"""
        from decimal import Decimal
        
        # Use initial balance saved in database
        initial_balance = self.initial_balance or Decimal('0')
        
        # Calculate total deposits
        deposits = self.transactions.filter(
            transaction_type='deposit'
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        
        # Calculate total withdrawals
        withdrawals = self.transactions.filter(
            transaction_type='withdrawal'
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        
        # Actual balance = initial balance + deposits - withdrawals
        actual_balance = initial_balance + deposits - withdrawals
        return actual_balance
    
    def sync_balance(self):
        """Sync saved balance with actual balance"""
        from decimal import Decimal
        
        actual_balance = self.calculate_actual_balance()
        if self.balance != actual_balance:
            self.balance = actual_balance
            self.save(update_fields=['balance'])
        return actual_balance


class BankTransfer(models.Model):
    """Bank Transfer"""
    transfer_number = models.CharField(_('Transfer Number'), max_length=50, unique=True)
    date = models.DateField(_('Date'))
    from_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, 
                                   verbose_name=_('From Account'), related_name='transfers_from')
    to_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, 
                                 verbose_name=_('To Account'), related_name='transfers_to')
    amount = models.DecimalField(_('Amount'), max_digits=15, decimal_places=3)
    fees = models.DecimalField(_('Fees'), max_digits=15, decimal_places=3, default=0)
    exchange_rate = models.DecimalField(_('Exchange Rate'), max_digits=10, decimal_places=4, default=1)
    description = models.TextField(_('Description'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Bank Transfer')
        verbose_name_plural = _('Bank Transfers')
        ordering = ['-date', '-transfer_number']

    def __str__(self):
        return f"{self.transfer_number} - {self.from_account.name} -> {self.to_account.name}"


class BankTransaction(models.Model):
    """Bank Account Transaction"""
    TRANSACTION_TYPES = [
        ('deposit', _('Deposit')),
        ('withdrawal', _('Withdrawal')),
    ]
    
    bank = models.ForeignKey(BankAccount, on_delete=models.PROTECT, 
                           verbose_name=_('Bank Account'), related_name='transactions')
    transaction_type = models.CharField(_('Transaction Type'), max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(_('Amount'), max_digits=15, decimal_places=3)
    description = models.TextField(_('Description'))
    reference_number = models.CharField(_('Reference Number'), max_length=100, blank=True)
    date = models.DateField(_('Date'))
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Bank Transaction')
        verbose_name_plural = _('Bank Transactions')
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.bank.name} - {self.get_transaction_type_display()} - {self.amount}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update bank balance
        self.update_bank_balance()
    
    def update_bank_balance(self):
        """Update bank account balance"""
        # Use sync_balance instead of manual calculation
        self.bank.sync_balance()
