from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from customers.models import CustomerSupplier
from cashboxes.models import Cashbox
from banks.models import BankAccount
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone as django_timezone

User = get_user_model()


class PaymentVoucher(models.Model):
    """Payment voucher for suppliers or expenses"""
    PAYMENT_TYPES = [
        ('cash', _('Cash')),
        ('check', _('Check')),
        ('bank_transfer', _('Bank Transfer')),
    ]
    
    VOUCHER_TYPES = [
        ('supplier', _('Supplier Payment')),
        ('expense', _('Expenses')),
        ('salary', _('Salary')),
        ('other', _('Other')),
    ]
    
    CHECK_STATUS = [
        ('pending', _('Pending')),
        ('cleared', _('Cleared')),
        ('cancelled', _('Cancelled')),
    ]
    
    # Basic information
    voucher_number = models.CharField(_('Voucher Number'), max_length=50, unique=True)
    date = models.DateField(_('Voucher Date'))
    voucher_type = models.CharField(_('Voucher Type'), max_length=20, choices=VOUCHER_TYPES)
    payment_type = models.CharField(_('Payment Type'), max_length=15, choices=PAYMENT_TYPES)
    amount = models.DecimalField(_('Amount'), max_digits=15, decimal_places=3)
    
    # Beneficiary
    supplier = models.ForeignKey(CustomerSupplier, on_delete=models.PROTECT, null=True, blank=True,
                               verbose_name=_('Supplier'), related_name='payment_vouchers')
    beneficiary_name = models.CharField(_('Beneficiary Name'), max_length=200, blank=True,
                                      help_text=_('In case the beneficiary is not a registered supplier'))
    
    # For cash payment
    cashbox = models.ForeignKey(Cashbox, on_delete=models.PROTECT, null=True, blank=True,
                              verbose_name=_('Cashbox'), related_name='payment_vouchers')
    
    # For bank transfer
    bank = models.ForeignKey(BankAccount, on_delete=models.PROTECT, null=True, blank=True,
                           verbose_name=_('Bank'), related_name='payment_vouchers')
    bank_reference = models.CharField(_('Transfer Reference'), max_length=100, blank=True)
    
    # For checks
    check_number = models.CharField(_('Check Number'), max_length=50, blank=True)
    check_date = models.DateField(_('Check Date'), null=True, blank=True)
    check_due_date = models.DateField(_('Check Due Date'), null=True, blank=True)
    check_bank_name = models.CharField(_('Bank Name'), max_length=200, blank=True)
    check_status = models.CharField(_('Check Status'), max_length=20, choices=CHECK_STATUS, 
                                  default='pending', blank=True)
    
    # Additional information
    description = models.TextField(_('Description'))
    notes = models.TextField(_('Notes'), blank=True)
    
    # System information
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    # Voucher status
    is_active = models.BooleanField(_('Active'), default=True)
    is_reversed = models.BooleanField(_('Reversed'), default=False)
    reversed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name=_('Reversed By'), related_name='reversed_payments')
    reversed_at = models.DateTimeField(_('Reversal Date'), null=True, blank=True)
    reversal_reason = models.TextField(_('Reversal Reason'), blank=True)

    class Meta:
        verbose_name = _('Payment Voucher')
        verbose_name_plural = _('Payment Vouchers')
        ordering = ['-date', '-voucher_number']
        default_permissions = []  # No default permissions
        permissions = [
            ("can_view_payments", "Can View Payment Vouchers"),
            ("can_add_payments", "Can Add Payment Vouchers"),
            ("can_edit_payments", "Can Edit Payment Vouchers"),
            ("can_delete_payments", "Can Delete Payment Vouchers"),
        ]

    def __str__(self):
        beneficiary = self.supplier.name if self.supplier else self.beneficiary_name
        return f"{self.voucher_number} - {beneficiary} - {self.amount}"
    
    def clean(self):
        """Validate basic data"""
        # Basic validation only - detailed validation is done in Form
        pass
    
    def save(self, *args, **kwargs):
        self.clean()
        
        # Generate voucher number automatically if not present
        if not self.voucher_number:
            self.voucher_number = self.generate_voucher_number()
        
        super().save(*args, **kwargs)
    
    def generate_voucher_number(self):
        """Generate automatic payment voucher number"""
        from django.db.models import Max
        
        # Get last voucher number in same year
        current_year = django_timezone.now().year
        last_voucher = PaymentVoucher.objects.filter(
            voucher_number__startswith=f'PV{current_year}'
        ).aggregate(Max('voucher_number'))['voucher_number__max']
        
        if last_voucher:
            # Extract sequential number
            try:
                last_number = int(last_voucher.split('-')[-1])
                new_number = last_number + 1
            except (ValueError, IndexError):
                new_number = 1
        else:
            new_number = 1
        
        return f'PV{current_year}-{new_number:06d}'
    
    @property
    def can_be_reversed(self):
        """Check if voucher can be reversed"""
        return self.is_active and not self.is_reversed
    
    @property
    def effective_amount(self):
        """Effective amount (negative if reversed)"""
        return -self.amount if self.is_reversed else self.amount
    
    @property
    def beneficiary_display(self):
        """Display beneficiary name"""
        return self.supplier.name if self.supplier else self.beneficiary_name


# PaymentVoucherItem will be added later in future version
# class PaymentVoucherItem(models.Model):
#     """Payment voucher items (in case of detailed expenses)"""
#     voucher = models.ForeignKey(PaymentVoucher, on_delete=models.CASCADE, 
#                                related_name='items', verbose_name=_('Payment Voucher'))
#     description = models.CharField(_('Description'), max_length=200)
#     amount = models.DecimalField(_('Amount'), max_digits=15, decimal_places=3)
#     account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT, null=True, blank=True,
#                                verbose_name=_('Account'), related_name='payment_items')
#     
#     class Meta:
#         verbose_name = _('Payment Voucher Item')
#         verbose_name_plural = _('Payment Voucher Items')
#     
#     def __str__(self):
#         return f"{self.voucher.voucher_number} - {self.description} - {self.amount}"
