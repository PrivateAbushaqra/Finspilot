from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal

User = get_user_model()


class Account(models.Model):
    """دليل الحسابات المحاسبية"""
    ACCOUNT_TYPES = [
        ('asset', _('أصول')),
        ('liability', _('مطلوبات')),
        ('equity', _('حقوق ملكية')),
        ('revenue', _('إيرادات')),
        ('expense', _('مصاريف')),
        ('purchases', _('مشتريات')),
        ('sales', _('مبيعات')),
    ]

    code = models.CharField(_('كود الحساب'), max_length=20, unique=True)
    name = models.CharField(_('Account Name'), max_length=100)
    account_type = models.CharField(_('نوع الحساب'), max_length=20, choices=ACCOUNT_TYPES)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                              verbose_name=_('الحساب الرئيسي'), related_name='children')
    description = models.TextField(_('Description'), blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    balance = models.DecimalField(_('Balance'), max_digits=15, decimal_places=3, default=0)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('حساب')
        verbose_name_plural = _('الحسابات')
        ordering = ['code', 'name']
        default_permissions = ('add', 'change', 'delete', 'view')
        permissions = [
            ('view_journalaccount', _('Can view حساب')),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_balance(self, as_of_date=None):
        """حساب الرصيد الحالي للحساب حتى تاريخ معين"""
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


class JournalEntry(models.Model):
    """قيد محاسبي"""
    REFERENCE_TYPES = [
        ('sales_invoice', _('Sales Invoice')),
        ('purchase_invoice', _('Purchase Invoice')),
        ('sales_return', _('Sales Return')),
        ('purchase_return', _('Purchase Return')),
        ('receipt_voucher', _('Receipt Voucher')),
        ('payment_voucher', _('Payment Voucher')),
        ('revenue_expense', _('Revenue/Expense Entry')),
        ('asset_depreciation', _('Asset Depreciation')),
        ('provision', _('Provision')),
        ('provision_entry', _('Provision Entry')),
        ('manual', _('Manual Entry')),
        ('adjustment', _('Adjustment Entry')),
    ]

    entry_number = models.CharField(_('رقم القيد'), max_length=50, unique=True, blank=True)
    entry_date = models.DateField(_('تاريخ القيد'))
    reference_type = models.CharField(_('نوع العملية'), max_length=20, choices=REFERENCE_TYPES)
    reference_id = models.PositiveIntegerField(_('رقم العملية المرتبطة'), null=True, blank=True)
    sales_invoice = models.ForeignKey('sales.SalesInvoice', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('فاتورة المبيعات'))
    purchase_invoice = models.ForeignKey('purchases.PurchaseInvoice', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('فاتورة المشتريات'))
    description = models.TextField(_('وصف القيد'))
    total_amount = models.DecimalField(_('إجمالي المبلغ'), max_digits=15, decimal_places=3)
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('قيد محاسبي')
        verbose_name_plural = _('القيود المحاسبية')
        ordering = ['-entry_date', '-created_at']

    def __str__(self):
        return f"{self.entry_number} - {self.description}"

    def save(self, *args, **kwargs):
        if not self.entry_number:
            self.entry_number = self.generate_entry_number()
        
        # تحديث الحقول المرتبطة بالفواتير
        if self.reference_type == 'sales_invoice' and self.reference_id:
            try:
                from sales.models import SalesInvoice
                self.sales_invoice = SalesInvoice.objects.get(id=self.reference_id)
            except SalesInvoice.DoesNotExist:
                pass
        elif self.reference_type == 'purchase_invoice' and self.reference_id:
            try:
                from purchases.models import PurchaseInvoice
                self.purchase_invoice = PurchaseInvoice.objects.get(id=self.reference_id)
            except PurchaseInvoice.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)

    def generate_entry_number(self):
        """توليد رقم القيد"""
        from datetime import datetime
        
        # البحث عن آخر قيد في نفس السنة
        current_year = datetime.now().year
        last_entry = JournalEntry.objects.filter(
            entry_date__year=current_year
        ).order_by('-id').first()
        
        if last_entry and last_entry.entry_number:
            # استخراج الرقم من آخر قيد
            try:
                last_number = int(last_entry.entry_number.split('-')[-1])
                new_number = last_number + 1
            except (ValueError, IndexError):
                new_number = 1
        else:
            new_number = 1
        
        return f"JE-{current_year}-{new_number:04d}"

    def clean(self):
        """التحقق من توازن القيد"""
        if self.pk:  # إذا كان القيد محفوظًا بالفعل
            total_debit = self.lines.aggregate(total=models.Sum('debit'))['total'] or Decimal('0')
            total_credit = self.lines.aggregate(total=models.Sum('credit'))['total'] or Decimal('0')
            
            if total_debit != total_credit:
                raise ValidationError(_('يجب أن يكون مجموع المدين مساوياً لمجموع الدائن'))


class JournalLine(models.Model):
    """بند القيد المحاسبي"""
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, 
                                    verbose_name=_('القيد المحاسبي'), related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, 
                               verbose_name=_('الحساب'), related_name='journal_lines')
    debit = models.DecimalField(_('مدين'), max_digits=15, decimal_places=3, default=0)
    credit = models.DecimalField(_('creditor'), max_digits=15, decimal_places=3, default=0)
    line_description = models.TextField(_('تفاصيل البند'), blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('بند قيد')
        verbose_name_plural = _('بنود القيود')

    def __str__(self):
        return f"{self.journal_entry.entry_number} - {self.account.name}"

    def clean(self):
        """التحقق من صحة البيانات"""
        if self.debit < 0 or self.credit < 0:
            raise ValidationError(_('المبالغ يجب أن تكون موجبة'))
        
        if self.debit > 0 and self.credit > 0:
            raise ValidationError(_('لا يمكن أن يكون البند مدين ودائن في نفس الوقت'))
        
        if self.debit == 0 and self.credit == 0:
            raise ValidationError(_('يجب إدخال مبلغ مدين أو دائن'))


class YearEndClosing(models.Model):
    """إقفال السنة المالية"""
    STATUS_CHOICES = [
        ('pending', _('في الانتظار')),
        ('completed', _('مكتمل')),
        ('cancelled', _('ملغي')),
    ]
    
    year = models.IntegerField(_('السنة المالية'))
    closing_date = models.DateField(_('تاريخ الإقفال'))
    net_profit = models.DecimalField(_('صافي الربح/الخسارة'), max_digits=15, decimal_places=3, default=0)
    status = models.CharField(_('الحالة'), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # القيود المرتبطة
    closing_entry = models.OneToOneField(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True,
                                        verbose_name=_('قيد الإقفال'), related_name='year_end_closing')
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('أنشئ بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)
    
    notes = models.TextField(_('ملاحظات'), blank=True)

    class Meta:
        verbose_name = _('إقفال سنوي')
        verbose_name_plural = _('الإقفالات السنوية')
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
            return False, _("الإقفال مكتمل مسبقاً")
        
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
        
        return True, _("تم إجراء الإقفال السنوي بنجاح")
