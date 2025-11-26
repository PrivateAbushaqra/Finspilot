from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from customers.models import CustomerSupplier
from cashboxes.models import Cashbox
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone

User = get_user_model()


class PaymentReceipt(models.Model):
    """Customer Payment Receipt"""
    PAYMENT_TYPES = [
        ('cash', _('Cash')),
        ('check', _('Check')),
        ('bank_transfer', _('Bank Transfer')),
    ]
    
    CHECK_STATUS = [
        ('pending', _('Pending')),
        ('collected', _('Collected')),
        ('bounced', _('Bounced')),
        ('cancelled', _('Cancelled')),
    ]
    
    receipt_number = models.CharField(_('Receipt Number'), max_length=50, unique=True)
    date = models.DateField(_('Receipt Date'))
    customer = models.ForeignKey(CustomerSupplier, on_delete=models.PROTECT, 
                               verbose_name=_('Customer'), related_name='payment_receipts')
    payment_type = models.CharField(_('Payment Type'), max_length=20, choices=PAYMENT_TYPES)
    amount = models.DecimalField(_('Amount'), max_digits=15, decimal_places=3)
    
    # For cash payments
    cashbox = models.ForeignKey(Cashbox, on_delete=models.PROTECT, null=True, blank=True,
                              verbose_name=_('Cashbox'), related_name='payment_receipts')
    
    # For bank transfers
    bank_account = models.ForeignKey('banks.BankAccount', on_delete=models.PROTECT, null=True, blank=True,
                                   verbose_name=_('Bank Account'), related_name='payment_receipts')
    bank_transfer_reference = models.CharField(_('Bank Transfer Reference'), max_length=100, blank=True,
                                             help_text=_('Bank transfer reference or transaction id'))
    bank_transfer_date = models.DateField(_('Bank Transfer Date'), null=True, blank=True)
    bank_transfer_notes = models.TextField(_('Bank Transfer Notes'), blank=True)
    
    # For checks
    check_number = models.CharField(_('Check Number'), max_length=50, blank=True)
    check_date = models.DateField(_('Check Date'), null=True, blank=True)
    check_due_date = models.DateField(_('Check Due Date'), null=True, blank=True)
    bank_name = models.CharField(_('Bank Name'), max_length=200, blank=True)
    check_cashbox = models.ForeignKey(Cashbox, on_delete=models.PROTECT, null=True, blank=True,
                                    verbose_name=_('Check Cashbox'), related_name='check_receipts')
    check_status = models.CharField(_('Check Status'), max_length=20, choices=CHECK_STATUS, 
                                  default='pending', blank=True)
    bounce_reason = models.CharField(_('Bounce Reason'), max_length=100, blank=True, 
                                   help_text=_('Reason for cheque bounce (insufficient funds, signature mismatch, bank stop payment...)'))
    
    # IFRS 9 - Expected Credit Loss (ECL)
    expected_credit_loss = models.DecimalField(_('Expected Credit Loss (ECL)'), max_digits=15, decimal_places=3, 
                                            default=0, help_text=_('Value of expected credit loss (ECL)'))
    ecl_calculation_date = models.DateTimeField(_('ECL Calculation Date'), null=True, blank=True)
    ecl_calculation_method = models.CharField(_('ECL Calculation Method'), max_length=50, blank=True,
                                           help_text=_('Method used to calculate expected credit loss (reversal, overdue, etc)'))
    
    # General information
    description = models.TextField(_('Description'), blank=True)
    notes = models.TextField(_('Notes'), blank=True)
    
    # System information
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    # Voucher status
    is_active = models.BooleanField(_('Active'), default=True)
    is_reversed = models.BooleanField(_('Reversed'), default=False)
    reversed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name=_('Reversed By'), related_name='reversed_receipts')
    reversed_at = models.DateTimeField(_('Reversal Date'), null=True, blank=True)
    reversal_reason = models.TextField(_('Reversal Reason'), blank=True)

    class Meta:
        verbose_name = _('Receipt Voucher')
        verbose_name_plural = _('Receipt Vouchers')
        ordering = ['-date', '-receipt_number']
        default_permissions = []  # No default permissions
        permissions = [
            ("can_view_receipts", _("Can View Receipt Vouchers")),
            ("can_add_receipts", _("Can Add Receipt Vouchers")),
            ("can_edit_receipts", _("Can Edit Receipt Vouchers")),
            ("can_delete_receipts", _("Can Delete Receipt Vouchers")),
            ("can_view_check_management", _("Can View Cheque Management")),
            ("can_collect_checks", _("Can Collect Cheques")),
            ("can_view_check_balance_forecast", _("Can View Check Balance Forecast")),
        ]

    def __str__(self):
        return f"{self.receipt_number} - {self.customer.name} - {self.amount}"
    
    def clean(self):
        """Validate basic data"""
        if self.payment_type == 'cash' and not self.cashbox:
            raise ValidationError(_('Cashbox must be specified for cash payment'))
        
        if self.payment_type == 'bank_transfer':
            if not self.bank_account:
                raise ValidationError(_('Bank account must be specified for bank transfer'))
            if not self.bank_transfer_reference:
                raise ValidationError(_('Bank transfer reference is required'))
            if not self.bank_transfer_date:
                raise ValidationError(_('Bank transfer date is required'))
        
        if self.payment_type == 'check':
            if not self.check_number:
                raise ValidationError(_('Check number is required'))
            if not self.check_date:
                raise ValidationError(_('Check date is required'))
            if not self.check_due_date:
                raise ValidationError(_('Check due date is required'))
            if not self.bank_name:
                raise ValidationError(_('Bank name is required'))
    
    def save(self, *args, **kwargs):
        # Set default check_status for checks
        if self.payment_type == 'check' and not self.check_status:
            self.check_status = 'pending'
        
        self.clean()
        super().save(*args, **kwargs)
    
    @property
    def can_be_reversed(self):
        """Check if voucher can be reversed"""
        return self.is_active and not self.is_reversed
    
    def calculate_expected_credit_loss(self):
        """
        Calculate expected credit loss according to IFRS 9
        Enhanced to include customer risk evaluation and credit history
        """
        from datetime import datetime, timedelta
        
        if self.payment_type != 'check':
            return Decimal('0.000'), ''
        
        current_date = datetime.now().date()
        ecl_amount = Decimal('0.000')
        
        # Assess customer risk based on payment records
        customer_risk_factor = self._calculate_customer_risk_factor()
        
        if self.check_status == 'bounced':
            # bounced cheque - full loss
            ecl_amount = self.amount
            self.ecl_calculation_method = 'Bounced check - full loss'
            
        elif self.check_status == 'collected':
            # Cheque collected - check delay
            collection = self.collections.filter(status='collected').first()
            if collection:
                days_late = (collection.collection_date - self.check_due_date).days
                
                if days_late > 0:
                    # Late cheque - partial loss calculation based on delay and customer risk
                    base_percentage = Decimal('0.05')  # base 5%
                    
                    if days_late <= 30:
                        ecl_percentage = base_percentage
                    elif days_late <= 90:
                        ecl_percentage = Decimal('0.15')
                    elif days_late <= 180:
                        ecl_percentage = Decimal('0.30')
                    else:
                        ecl_percentage = Decimal('0.50')
                    
                    # Apply customer risk factor
                    ecl_percentage *= customer_risk_factor
                    
                    ecl_amount = self.amount * ecl_percentage
                    self.ecl_calculation_method = f'Late {days_late} days - {ecl_percentage*100:.1f}%'
                else:
                    # cheque collected on time or earlier - no loss
                    ecl_amount = Decimal('0.000')
                    self.ecl_calculation_method = 'Collected on time'
            else:
                # cheque deposited but not collected - potential loss
                days_since_deposit = (current_date - self.check_due_date).days
                if days_since_deposit > 0:
                    base_percentage = min(Decimal('0.10'), Decimal(days_since_deposit) / Decimal('365') * Decimal('0.20'))
                    ecl_percentage = base_percentage * customer_risk_factor
                    ecl_amount = self.amount * ecl_percentage
                    self.ecl_calculation_method = f'Deposited late {days_since_deposit} days'
                else:
                    ecl_amount = Decimal('0.000')
                    self.ecl_calculation_method = 'Deposited on time'
                    
        elif self.check_status in ['new', 'deposited']:
            # New or deposited cheque - initial risk assessment
            days_to_due = (self.check_due_date - current_date).days

            if days_to_due < 0:
                # Overdue cheque at due date
                days_overdue = abs(days_to_due)
                base_percentage = min(Decimal('0.20'), Decimal(days_overdue) / Decimal('365') * Decimal('0.30'))
                ecl_percentage = base_percentage * customer_risk_factor
                ecl_amount = self.amount * ecl_percentage
                self.ecl_calculation_method = f'Overdue {days_overdue} days'
            else:
                # Cheque on time - low loss considering customer risk
                base_percentage = Decimal('0.01')  # base 1%
                ecl_percentage = base_percentage * customer_risk_factor
                ecl_amount = self.amount * ecl_percentage
                self.ecl_calculation_method = f'On-time {ecl_percentage*100:.1f}%'
        
        self.expected_credit_loss = ecl_amount
        self.ecl_calculation_date = timezone.now()
        self.save(update_fields=['expected_credit_loss', 'ecl_calculation_date', 'ecl_calculation_method'])
        
        return ecl_amount, self.ecl_calculation_method
    
    def _calculate_customer_risk_factor(self):
        """
        Calculate customer risk factor based on credit history
        """
        # Count bounced cheques for the customer
        bounced_cheques = PaymentReceipt.objects.filter(
            customer=self.customer,
            payment_type='check',
            check_status='bounced'
        ).count()
        
        # Count total cheques for the customer
        total_cheques = PaymentReceipt.objects.filter(
            customer=self.customer,
            payment_type='check'
        ).count()
        
        if total_cheques == 0:
            return Decimal('1.0')  # New customer
        
        # Calculate bounce rate
        bounce_rate = bounced_cheques / total_cheques
        
        # Determine risk factor
        if bounce_rate == 0:
            risk_factor = Decimal('0.8')  # Trusted customer
        elif bounce_rate <= 0.1:
            risk_factor = Decimal('1.0')  # Medium risk
        elif bounce_rate <= 0.25:
            risk_factor = Decimal('1.3')  # High risk
        else:
            risk_factor = Decimal('1.5')  # Very high risk
        
        return risk_factor
    
    @property
    def effective_amount(self):
        """Effective amount (negative if reversed)"""
        return -self.amount if self.is_reversed else self.amount


class CheckCollection(models.Model):
    """Check Collection"""
    COLLECTION_STATUS = [
        ('collected', _('Collected')),
        ('bounced', _('Bounced')),
    ]
    
    receipt = models.ForeignKey(PaymentReceipt, on_delete=models.PROTECT, 
                              verbose_name=_('Receipt Voucher'), related_name='collections')
    collection_date = models.DateField(_('Collection Date'))
    status = models.CharField(_('Collection Status'), max_length=20, choices=COLLECTION_STATUS)
    cashbox = models.ForeignKey(Cashbox, on_delete=models.PROTECT, null=True, blank=True,
                              verbose_name=_('Cashbox'))
    notes = models.TextField(_('Notes'), blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Check Collection')
        verbose_name_plural = _('Check Collections')
        ordering = ['-collection_date']
        default_permissions = []  # No default permissions

    def __str__(self):
        return f"Check collection {self.receipt.receipt_number} - {self.get_status_display()}"


class ReceiptReversal(models.Model):
    """Receipt Reversal"""
    original_receipt = models.OneToOneField(PaymentReceipt, on_delete=models.PROTECT,
                                          verbose_name=_('Original Receipt'), related_name='reversal')
    reversal_date = models.DateField(_('Reversal Date'))
    reason = models.TextField(_('Reversal Reason'))
    notes = models.TextField(_('Notes'), blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Receipt Reversal')
        verbose_name_plural = _('Receipt Reversals')
        ordering = ['-reversal_date']
        default_permissions = []  # No default permissions

    def __str__(self):
        return f"Reversal {self.original_receipt.receipt_number}"
