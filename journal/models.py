from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal

User = get_user_model()


class Account(models.Model):
    """دليل الحسابات المحاسبية"""
    ACCOUNT_TYPES = [
        ('asset', _('Assets')),
        ('liability', _('Liabilities')),
        ('equity', _('Equity')),
        ('revenue', _('Revenues')),
        ('expense', _('Expenses')),
        ('purchases', _('Purchases')),
        ('sales', _('Sales')),
    ]

    code = models.CharField(_('Account Code'), max_length=20, unique=True)
    name = models.CharField(_('Account Name'), max_length=100)
    account_type = models.CharField(_('Account Type'), max_length=20, choices=ACCOUNT_TYPES)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                              verbose_name=_('Parent Account'), related_name='children')
    description = models.TextField(_('Description'), blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    balance = models.DecimalField(_('Balance'), max_digits=15, decimal_places=3, default=0)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Account')
        verbose_name_plural = _('Accounts')
        ordering = ['code', 'name']
        default_permissions = ('add', 'change', 'delete', 'view')
        permissions = [
            ('view_journalaccount', _('Can view Account')),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_balance(self, as_of_date=None):
        """حساب الرصيد الحالي للحساب حتى تاريخ معين
        
        للحسابات الرئيسية (التي لها حسابات فرعية): يجمع أرصدة الحسابات الفرعية النشطة
        للحسابات الفرعية: يحسب من قيوده الخاصة
        """
        # إذا كان الحساب له حسابات فرعية، اجمع أرصدة الحسابات الفرعية النشطة
        if self.children.filter(is_active=True).exists():
            balance = Decimal('0')
            for child in self.children.filter(is_active=True):
                balance += child.get_balance(as_of_date)
            return balance
        
        # إلا إذا كان حساب فرعي، احسب من قيوده الخاصة
        lines = JournalLine.objects.filter(account=self)
        if as_of_date:
            lines = lines.filter(journal_entry__entry_date__lte=as_of_date)
        debit_total = lines.aggregate(total=models.Sum('debit'))['total'] or Decimal('0')
        credit_total = lines.aggregate(total=models.Sum('credit'))['total'] or Decimal('0')
        
        # الأصول والمصاريف ترتفع بالمدين
        if self.account_type in ['asset', 'expense', 'purchases']:
            return debit_total - credit_total
        # المطلوبات والإيرادات وحقوق الملكية ترتفع بالدائن
        else:
            return credit_total - debit_total

    def update_account_balance(self):
        """تحديث رصيد الحساب بناءً على جميع القيود"""
        self.balance = self.get_balance()
        self.save(update_fields=['balance'])


class JournalEntry(models.Model):
    """قيد محاسبي"""
    REFERENCE_TYPES = [
        ('asset_depreciation', _('Asset Depreciation')),
        ('manual', _('Manual Entry')),
        ('adjustment', _('Adjustment Entry')),
        ('customer_supplier_adjustment', _('Customer/Supplier Balance Adjustment')),
        ('warehouse_transfer', _('Warehouse Transfer')),
        ('sales_return', _('Sales Return')),
        ('sales_return_cogs', _('Sales Return COGS')),
    ]

    # أنواع القيود
    ENTRY_TYPES = [
        ('receipt', _('Receipt')),
        ('payment', _('Payment')),
        ('transfer', _('Transfer')),
        ('adjustment', _('Adjustment')),
        ('daily', _('Daily')),
        ('other', _('Other')),
    ]
    entry_number = models.CharField(_('Entry Number'), max_length=50, unique=True, blank=True)
    entry_date = models.DateField(_('Entry Date'))
    entry_type = models.CharField(_('Entry Type'), max_length=20, choices=ENTRY_TYPES, default='daily')
    reference_type = models.CharField(_('Reference Type'), max_length=30, choices=REFERENCE_TYPES)
    reference_id = models.PositiveIntegerField(_('Reference ID'), null=True, blank=True)
    sales_invoice = models.ForeignKey('sales.SalesInvoice', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Sales Invoice'))
    sales_return = models.ForeignKey('sales.SalesReturn', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Sales Return'))
    purchase_invoice = models.ForeignKey('purchases.PurchaseInvoice', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Purchase Invoice'))
    purchase_return = models.ForeignKey('purchases.PurchaseReturn', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Purchase Return'))
    cashbox_transfer = models.ForeignKey('cashboxes.CashboxTransfer', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Cashbox Transfer'))
    bank_transfer = models.ForeignKey('banks.BankTransfer', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Bank Transfer'))
    description = models.TextField(_('Entry Description'))
    total_amount = models.DecimalField(_('Total Amount'), max_digits=15, decimal_places=3)
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Journal Entry')
        verbose_name_plural = _('Journal Entries')
        ordering = ['-entry_date', '-created_at']
        default_permissions = ('add', 'change', 'delete', 'view')
        permissions = [
            ('change_entry_number', _('Change Entry Number')),
        ]

    def __str__(self):
        return f"{self.entry_number} - {self.description}"

    def save(self, *args, **kwargs):
        if not self.entry_number:
            self.entry_number = self.generate_entry_number()
        
        # تحديث الحقول المرتبطة بالفواتير
        if self.reference_type in ['sales_invoice', 'sales_invoice_cogs'] and self.reference_id:
            try:
                from sales.models import SalesInvoice
                self.sales_invoice = SalesInvoice.objects.get(id=self.reference_id)
            except SalesInvoice.DoesNotExist:
                pass
        elif self.reference_type in ['sales_return', 'sales_return_cogs'] and self.reference_id:
            try:
                from sales.models import SalesReturn
                self.sales_return = SalesReturn.objects.get(id=self.reference_id)
            except SalesReturn.DoesNotExist:
                pass
        elif self.reference_type == 'purchase_invoice' and self.reference_id:
            try:
                from purchases.models import PurchaseInvoice
                self.purchase_invoice = PurchaseInvoice.objects.get(id=self.reference_id)
            except PurchaseInvoice.DoesNotExist:
                pass
        elif self.reference_type == 'purchase_return' and self.reference_id:
            try:
                from purchases.models import PurchaseReturn
                self.purchase_return = PurchaseReturn.objects.get(id=self.reference_id)
            except PurchaseReturn.DoesNotExist:
                pass
        elif self.reference_type == 'cashbox_transfer' and self.reference_id:
            try:
                from cashboxes.models import CashboxTransfer
                self.cashbox_transfer = CashboxTransfer.objects.get(id=self.reference_id)
            except CashboxTransfer.DoesNotExist:
                pass
        elif self.reference_type == 'bank_transfer' and self.reference_id:
            try:
                from banks.models import BankTransfer
                self.bank_transfer = BankTransfer.objects.get(id=self.reference_id)
            except BankTransfer.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)

    def generate_entry_number(self):
        """توليد رقم القيد من تسلسل المستندات"""
        try:
            from core.models import DocumentSequence
            seq = DocumentSequence.objects.get(document_type='journal_entry')
            return seq.get_next_number()
        except DocumentSequence.DoesNotExist:
            # إذا لم يكن هناك تسلسل، استخدم الطريقة القديمة
            from datetime import datetime
            
            current_year = datetime.now().year
            base_pattern = f"JE-{current_year}-"
            
            # محاولة عدة مرات لتجنب السباق
            max_attempts = 10
            for attempt in range(max_attempts):
                try:
                    # البحث عن جميع الأرقام المستخدمة في نفس السنة
                    existing_entries = JournalEntry.objects.filter(
                        entry_date__year=current_year,
                        entry_number__startswith=base_pattern
                    ).values_list('entry_number', flat=True)
                    
                    # استخراج الأرقام المستخدمة
                    used_numbers = set()
                    for entry_num in existing_entries:
                        try:
                            num_part = entry_num.split('-')[-1]
                            if num_part.isdigit():
                                used_numbers.add(int(num_part))
                        except (ValueError, IndexError):
                            continue
                    
                    # البحث عن أصغر رقم متاح
                    new_number = 1
                    while new_number in used_numbers:
                        new_number += 1
                    
                    # التحقق من أن الرقم لا يزال متاحاً (قد يكون تم استخدامه في سباق)
                    candidate_number = f"{base_pattern}{new_number:04d}"
                    if not JournalEntry.objects.filter(entry_number=candidate_number).exists():
                        return candidate_number
                        
                except Exception:
                    continue
            
            # إذا فشلت جميع المحاولات، استخدم timestamp مع UUID
            import time
            import uuid
            timestamp = str(int(time.time() * 1000000))[-8:]  # microsecond precision
            unique_part = str(uuid.uuid4().hex)[:4].upper()
            return f"{base_pattern}{timestamp}-{unique_part}"

    def clean(self):
        """التحقق من توازن القيد"""
        if self.pk:  # إذا كان القيد محفوظًا بالفعل
            total_debit = self.lines.aggregate(total=models.Sum('debit'))['total'] or Decimal('0')
            total_credit = self.lines.aggregate(total=models.Sum('credit'))['total'] or Decimal('0')
            
            if total_debit != total_credit:
                raise ValidationError(_('Debit and credit totals must be equal'))


class JournalLine(models.Model):
    """بند القيد المحاسبي"""
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, 
                                    verbose_name=_('Journal Entry'), related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, 
                               verbose_name=_('Account'), related_name='journal_lines')
    debit = models.DecimalField(_('Debit'), max_digits=15, decimal_places=3, default=0)
    credit = models.DecimalField(_('Credit'), max_digits=15, decimal_places=3, default=0)
    line_description = models.TextField(_('Line Description'), blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Journal Line')
        verbose_name_plural = _('Journal Lines')

    def __str__(self):
        return f"{self.journal_entry.entry_number} - {self.account.name}"

    def clean(self):
        """التحقق من صحة البيانات"""
        if self.debit < 0 or self.credit < 0:
            raise ValidationError(_('Amounts must be positive'))
        
        if self.debit > 0 and self.credit > 0:
            raise ValidationError(_('Line cannot be both debit and credit'))
        
        if self.debit == 0 and self.credit == 0:
            raise ValidationError(_('Must enter debit or credit amount'))

    @property
    def get_running_balance(self):
        """حساب الرصيد التراكمي حتى هذا البند"""
        from django.db.models import Sum
        
        # الحصول على جميع الحركات للحساب حتى تاريخ هذا البند
        lines = JournalLine.objects.filter(
            account=self.account,
            journal_entry__entry_date__lte=self.journal_entry.entry_date
        ).exclude(
            journal_entry__entry_date=self.journal_entry.entry_date,
            created_at__gt=self.created_at
        ).order_by('journal_entry__entry_date', 'created_at')
        
        debit_total = lines.aggregate(total=Sum('debit'))['total'] or Decimal('0')
        credit_total = lines.aggregate(total=Sum('credit'))['total'] or Decimal('0')
        
        # حسب نوع الحساب
        if self.account.account_type in ['asset', 'expense', 'purchases']:
            return debit_total - credit_total
        else:
            return credit_total - debit_total


class YearEndClosing(models.Model):
    """إقفال السنة المالية"""
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    ]
    
    year = models.IntegerField(_('Fiscal Year'))
    closing_date = models.DateField(_('Closing Date'))
    net_profit = models.DecimalField(_('Net Profit/Loss'), max_digits=15, decimal_places=3, default=0)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # القيود المرتبطة
    closing_entry = models.OneToOneField(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True,
                                        verbose_name=_('Closing Entry'), related_name='year_end_closing')
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    notes = models.TextField(_('Notes'), blank=True)

    class Meta:
        verbose_name = _('Year End Closing')
        verbose_name_plural = _('Year End Closings')
        ordering = ['-year', '-closing_date']
        unique_together = ['year']
        default_permissions = ('add', 'change', 'delete', 'view')
        permissions = [
            ('can_perform_year_end_closing', _('Can perform year end closing')),
        ]

    def __str__(self):
        return f"إقفال السنة {self.year} - {self.net_profit}"

    def calculate_net_profit(self):
        """حساب صافي الربح أو الخسارة للسنة"""
        from django.db.models import Sum, Q
        
        # حساب إجمالي الإيرادات
        revenue_accounts = Account.objects.filter(account_type__in=['revenue', 'sales'])
        total_revenue = JournalLine.objects.filter(
            account__in=revenue_accounts,
            journal_entry__entry_date__year=self.year
        ).aggregate(total=Sum('credit') - Sum('debit'))['total'] or Decimal('0')
        
        # حساب إجمالي المصروفات
        expense_accounts = Account.objects.filter(account_type__in=['expense', 'purchases'])
        total_expenses = JournalLine.objects.filter(
            account__in=expense_accounts,
            journal_entry__entry_date__year=self.year
        ).aggregate(total=Sum('debit') - Sum('credit'))['total'] or Decimal('0')
        
        # صافي الربح = الإيرادات - المصروفات
        self.net_profit = total_revenue - total_expenses
        return self.net_profit

    def perform_closing(self):
        """إجراء الإقفال السنوي"""
        if self.status == 'completed':
            return False, _("Closing already completed")
        
        # حساب صافي الربح
        self.calculate_net_profit()
        
        # إنشاء قيد الإقفال
        closing_entry = JournalEntry.objects.create(
            entry_date=self.closing_date,
            description=f"إقفال السنة المالية {self.year}",
            reference_type='year_end_closing',
            total_amount=abs(self.net_profit),
            created_by=self.created_by
        )
        
        # إذا كان هناك ربح
        if self.net_profit > 0:
            # إقفال حسابات الإيرادات والمصروفات
            revenue_accounts = Account.objects.filter(account_type__in=['revenue', 'sales'])
            expense_accounts = Account.objects.filter(account_type__in=['expense', 'purchases'])
            
            # إقفال الإيرادات
            for account in revenue_accounts:
                balance = account.get_balance(as_of_date=self.closing_date.replace(month=12, day=31))
                if balance > 0:
                    JournalLine.objects.create(
                        journal_entry=closing_entry,
                        account=account,
                        debit=balance,
                        credit=Decimal('0'),
                        line_description=f"إقفال حساب {account.name}"
                    )
            
            # إقفال المصروفات
            for account in expense_accounts:
                balance = account.get_balance(as_of_date=self.closing_date.replace(month=12, day=31))
                if balance > 0:
                    JournalLine.objects.create(
                        journal_entry=closing_entry,
                        account=account,
                        debit=Decimal('0'),
                        credit=balance,
                        line_description=f"إقفال حساب {account.name}"
                    )
            
            # نقل الربح إلى رأس المال
            retained_earnings = Account.objects.filter(account_type='equity', name__icontains='رأس المال').first()
            if retained_earnings:
                JournalLine.objects.create(
                    journal_entry=closing_entry,
                    account=retained_earnings,
                    debit=Decimal('0'),
                    credit=self.net_profit,
                    line_description="نقل صافي الربح إلى رأس المال"
                )
        
        # إذا كان هناك خسارة
        elif self.net_profit < 0:
            # نفس المنطق لكن عكسي
            loss = abs(self.net_profit)
            retained_earnings = Account.objects.filter(account_type='equity', name__icontains='رأس المال').first()
            if retained_earnings:
                JournalLine.objects.create(
                    journal_entry=closing_entry,
                    account=retained_earnings,
                    debit=loss,
                    credit=Decimal('0'),
                    line_description="نقل صافي الخسارة من رأس المال"
                )
        
        self.closing_entry = closing_entry
        self.status = 'completed'
        self.save()
        
        return True, _("Year end closing performed successfully")
