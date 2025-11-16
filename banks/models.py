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
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'), null=True, blank=True)

    class Meta:
        verbose_name = _('Bank Account')
        verbose_name_plural = _('Bank Accounts')
        ordering = ['name']
        default_permissions = []  # No default permissions
        permissions = [
            ("can_view_bank_accounts", "Can View Bank Accounts"),
            ("can_add_bank_accounts", "Can Add Bank Accounts"),
            ("can_edit_bank_accounts", "Can Edit Bank Accounts"),
            ("can_delete_bank_accounts", "Can Delete Bank Accounts"),
        ]

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
        
        # Calculate total deposits (exclude opening balance transactions)
        deposits = self.transactions.filter(
            transaction_type='deposit',
            is_opening_balance=False
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        
        # Calculate total withdrawals (exclude opening balance transactions)
        withdrawals = self.transactions.filter(
            transaction_type='withdrawal',
            is_opening_balance=False
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        
        # Actual balance = initial balance + deposits - withdrawals
        # Opening balance transactions are not counted as they represent the initial balance
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
        default_permissions = []  # No permissions needed - available to everyone

    def __str__(self):
        return f"{self.transfer_number} - {self.from_account.name} -> {self.to_account.name}"


class BankTransaction(models.Model):
    """Bank Account Transaction"""
    TRANSACTION_TYPES = [
        ('deposit', _('Deposit')),
        ('withdrawal', _('Withdrawal')),
    ]
    
    ADJUSTMENT_TYPES = [
        ('capital', _('Capital Contribution')),
        ('error_correction', _('Error Correction')),
        ('bank_interest', _('Bank Interest')),
        ('bank_charges', _('Bank Charges')),
        ('reconciliation', _('Bank Reconciliation')),
        ('exchange_difference', _('Exchange Difference')),
        ('other', _('Other')),
    ]
    
    bank = models.ForeignKey(BankAccount, on_delete=models.PROTECT, 
                           verbose_name=_('Bank Account'), related_name='transactions')
    transaction_type = models.CharField(_('Transaction Type'), max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(_('Amount'), max_digits=15, decimal_places=3)
    description = models.TextField(_('Description'))
    reference_number = models.CharField(_('Reference Number'), max_length=100, blank=True)
    date = models.DateField(_('Date'))
    
    # حقول جديدة لتصنيف التعديلات - متوافقة مع IFRS
    adjustment_type = models.CharField(
        _('Adjustment Type'),
        max_length=50,
        choices=ADJUSTMENT_TYPES,
        blank=True,
        null=True,
        help_text=_('Type of manual adjustment (IFRS compliant)')
    )
    is_manual_adjustment = models.BooleanField(
        _('Manual Adjustment'),
        default=False,
        help_text=_('Is this a manual balance adjustment?')
    )
    is_opening_balance = models.BooleanField(
        _('Opening Balance'),
        default=False,
        help_text=_('Is this an opening balance transaction?')
    )
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Bank Transaction')
        verbose_name_plural = _('Bank Transactions')
        ordering = ['-date', '-created_at']
        default_permissions = []  # No permissions needed - available to everyone
    
    def __str__(self):
        return f"{self.bank.name} - {self.get_transaction_type_display()} - {self.amount}"
    
    def save(self, *args, **kwargs):
        """
        حفظ المعاملة البنكية
        
        ملاحظة: تحديث الرصيد يتم تلقائياً عبر الإشارة (signal) update_bank_balance_on_transaction
        في ملف banks/signals.py، لذا لا حاجة لاستدعاء update_bank_balance هنا
        
        هذا يمنع التكرار في تحديث الرصيد ويضمن التوافق مع IFRS
        """
        super().save(*args, **kwargs)
    
    def update_bank_balance(self):
        """
        تحديث رصيد الحساب البنكي
        
        ملاحظة: هذه الطريقة متاحة للاستدعاء اليدوي عند الحاجة فقط،
        لكن التحديث التلقائي يتم عبر الإشارة في signals.py
        """
        self.bank.sync_balance()


class BankStatement(models.Model):
    """Bank Statement Entry"""
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, 
                                   verbose_name=_('Bank Account'), related_name='statements')
    date = models.DateField(_('Statement Date'))
    description = models.CharField(_('Description'), max_length=255)
    reference = models.CharField(_('Reference Number'), max_length=100, blank=True)
    debit = models.DecimalField(_('Debit'), max_digits=15, decimal_places=3, default=0)
    credit = models.DecimalField(_('Credit'), max_digits=15, decimal_places=3, default=0)
    balance = models.DecimalField(_('Balance'), max_digits=15, decimal_places=3)
    is_reconciled = models.BooleanField(_('Reconciled'), default=False)
    reconciled_date = models.DateTimeField(_('Reconciled Date'), null=True, blank=True)
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Bank Statement')
        verbose_name_plural = _('Bank Statements')
        ordering = ['-date', '-created_at']
        unique_together = ['bank_account', 'date', 'reference']
        default_permissions = []  # No permissions needed - available to everyone

    def __str__(self):
        return f"{self.bank_account.name} - {self.date} - {self.description}"

    @property
    def amount(self):
        """Net amount (credit - debit)"""
        return self.credit - self.debit


class BankReconciliation(models.Model):
    """Bank Reconciliation"""
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, 
                                   verbose_name=_('Bank Account'), related_name='reconciliations')
    statement_date = models.DateField(_('Statement Date'))
    book_balance = models.DecimalField(_('Book Balance'), max_digits=15, decimal_places=3)
    statement_balance = models.DecimalField(_('Statement Balance'), max_digits=15, decimal_places=3)
    reconciled_balance = models.DecimalField(_('Reconciled Balance'), max_digits=15, decimal_places=3)
    difference = models.DecimalField(_('Difference'), max_digits=15, decimal_places=3)
    status = models.CharField(_('Status'), max_length=20, choices=[
        ('draft', _('Draft')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled'))
    ], default='draft')
    
    # Reconciliation details
    deposits_in_transit = models.DecimalField(_('Deposits in Transit'), max_digits=15, decimal_places=3, default=0)
    outstanding_checks = models.DecimalField(_('Outstanding Checks'), max_digits=15, decimal_places=3, default=0)
    bank_charges = models.DecimalField(_('Bank Charges'), max_digits=15, decimal_places=3, default=0)
    interest_earned = models.DecimalField(_('Interest Earned'), max_digits=15, decimal_places=3, default=0)
    other_adjustments = models.DecimalField(_('Other Adjustments'), max_digits=15, decimal_places=3, default=0)
    
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Bank Reconciliation')
        verbose_name_plural = _('Bank Reconciliations')
        ordering = ['-statement_date', '-created_at']
        default_permissions = []  # No permissions needed - available to everyone

    def __str__(self):
        return f"{self.bank_account.name} - {self.statement_date}"

    def save(self, *args, **kwargs):
        # Calculate reconciled balance and difference
        self.reconciled_balance = self.book_balance + self.deposits_in_transit - self.outstanding_checks + self.bank_charges + self.interest_earned + self.other_adjustments
        self.difference = self.statement_balance - self.reconciled_balance
        super().save(*args, **kwargs)
