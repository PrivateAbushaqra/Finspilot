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
        # ('sales', _('Sales')),  # تم إزالة نوع sales للتوافق مع IFRS - المبيعات هي إيرادات
    ]

    code = models.CharField(_('Account Code'), max_length=20, unique=True)
    name = models.CharField(_('Account Name'), max_length=100)
    account_type = models.CharField(_('Account Type'), max_length=20, choices=ACCOUNT_TYPES)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                              verbose_name=_('Parent Account'), related_name='children')
    bank_account = models.ForeignKey('banks.BankAccount', on_delete=models.SET_NULL, null=True, blank=True,
                                    verbose_name=_('Linked Bank Account'), related_name='journal_accounts')
    description = models.TextField(_('Description'), blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    balance = models.DecimalField(_('Balance'), max_digits=15, decimal_places=3, default=0)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Chart of Accounts')
        verbose_name_plural = _('Chart of Accounts')
        ordering = ['code', 'name']
        default_permissions = []  # No default permissions
        permissions = [
            ("can_view_accounts", _("View Chart of Accounts")),
            ("can_add_accounts", _("Add Account")),
            ("can_edit_accounts", _("Edit Account")),
            ("can_delete_accounts", _("Delete Account")),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        """
        حفظ الحساب مع الربط التلقائي بالحساب الأب
        """
        # إذا لم يكن هناك حساب أب محدد، حاول ربطه تلقائياً
        if not self.parent:
            self.parent = self.get_auto_parent()
        
        super().save(*args, **kwargs)
    
    def get_auto_parent(self):
        """
        تحديد الحساب الأب تلقائياً بناءً على كود الحساب
        
        قواعد الربط:
        1. إذا كان الكود يحتوي على نقاط (مثل 101.01)، فالحساب قبل النقطة الأخيرة هو الأب
        2. إذا كان الكود يبدأ بأرقام متتالية (مثل 10101)، فالأرقام الأولى تشكل حساب الأب
        3. البحث عن أقرب حساب أب محتمل بنفس نوع الحساب
        """
        if not self.code:
            return None
            
        code = self.code.strip()
        
        # قاعدة 1: كود يحتوي على نقاط (مثل 101.01 -> 101)
        if '.' in code:
            parent_code = code.rsplit('.', 1)[0]
            try:
                parent = Account.objects.get(code=parent_code, is_active=True)
                # التحقق من أن نوع الحساب متطابق أو متوافق
                if parent.account_type == self.account_type or self._is_compatible_account_type(parent.account_type, self.account_type):
                    return parent
            except Account.DoesNotExist:
                pass
        
        # قاعدة 2: كود هرمي (مثل 10101 -> 101, 1010101 -> 10101)
        # ابحث عن أقصر كود أب محتمل بنفس نوع الحساب
        for i in range(len(code) - 1, 0, -1):
            potential_parent_code = code[:i]
            try:
                parent = Account.objects.get(
                    code=potential_parent_code, 
                    is_active=True,
                    account_type__in=self._get_compatible_account_types()
                )
                return parent
            except Account.DoesNotExist:
                continue
        
        return None
    
    def _is_compatible_account_type(self, parent_type, child_type):
        """
        التحقق من توافق أنواع الحسابات بين الأب والابن
        """
        # قواعد التوافق الأساسية
        compatibility_rules = {
            'asset': ['asset'],  # الأصول تحت الأصول
            'liability': ['liability'],  # المطلوبات تحت المطلوبات
            'equity': ['equity'],  # حقوق الملكية تحت حقوق الملكية
            'revenue': ['revenue'],  # الإيرادات تحت الإيرادات
            'expense': ['expense'],  # المصاريف تحت المصاريف
            'purchases': ['purchases', 'expense'],  # المشتريات تحت المشتريات أو المصاريف
        }
        
        return child_type in compatibility_rules.get(parent_type, [])
    
    def _get_compatible_account_types(self):
        """
        الحصول على أنواع الحسابات المتوافقة مع نوع هذا الحساب
        """
        if not self.account_type:
            return []
            
        compatibility_rules = {
            'asset': ['asset'],
            'liability': ['liability'], 
            'equity': ['equity'],
            'revenue': ['revenue'],
            'expense': ['expense'],
            'purchases': ['purchases', 'expense'],
        }
        
        return compatibility_rules.get(self.account_type, [self.account_type])

    def clean(self):
        # التحقق من عدم تكرار الاسم
        if Account.objects.filter(name=self.name).exclude(pk=self.pk).exists():
            raise ValidationError(_('Account name must be unique.'))
        
        # التحقق من صحة كود الحساب
        if self.code:
            # التحقق من عدم وجود حلقة مفرغة (حساب أب لنفسه)
            if self.parent and self.parent.pk == self.pk:
                raise ValidationError(_('Account cannot be parent of itself.'))
            
            # التحقق من عدم وجود حلقة مفرغة في التسلسل الهرمي
            if self.parent:
                current = self.parent
                visited = set()
                while current:
                    if current.pk in visited:
                        raise ValidationError(_('Circular reference detected in account hierarchy.'))
                    visited.add(current.pk)
                    current = current.parent

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

    def has_parent(self):
        """
        التحقق من وجود حساب أب
        """
        return self.parent is not None
    
    def is_child_account(self):
        """
        التحقق من أن الحساب فرعي (له حساب أب)
        """
        return self.parent is not None
    
    def get_hierarchy_path(self):
        """
        الحصول على المسار الهرمي الكامل للحساب
        مثال: الأصول > الأصول المتداولة > النقد وما شابهه
        """
        path = []
        current = self
        while current:
            path.insert(0, current.name)
            current = current.parent
        return " > ".join(path)
    
    def get_hierarchy_codes(self):
        """
        الحصول على أكواد المسار الهرمي
        مثال: 1 > 11 > 111
        """
        codes = []
        current = self
        while current:
            codes.insert(0, current.code)
            current = current.parent
        return " > ".join(codes)

    def update_account_balance(self):
        """تحديث رصيد الحساب بناءً على جميع القيود"""
        self.balance = self.get_balance()
        self.save(update_fields=['balance'])

    def validate_hierarchy(self):
        """
        التحقق من صحة الهرمية للحساب وإصلاح أي مشاكل
        
        يتحقق من:
        1. عدم وجود حلقات مفرغة
        2. توافق أنواع الحسابات
        3. صحة الربط التلقائي
        """
        errors = []
        
        # التحقق من عدم وجود حلقات مفرغة
        if self.parent:
            visited = set()
            current = self.parent
            while current:
                if current.id in visited:
                    errors.append("تم اكتشاف حلقة مفرغة في الهرمية")
                    break
                visited.add(current.id)
                current = current.parent
        
        # التحقق من توافق أنواع الحسابات
        if self.parent and not self._is_compatible_account_type(self.parent.account_type, self.account_type):
            errors.append(f"نوع الحساب ({self.account_type}) غير متوافق مع نوع حساب الأب ({self.parent.account_type})")
        
        # التحقق من الربط التلقائي
        auto_parent = self.get_auto_parent()
        if auto_parent and auto_parent != self.parent:
            # اقتراح الربط التلقائي
            self.parent = auto_parent
            self.save(update_fields=['parent'])
        
        return errors
    
    @staticmethod
    def fix_broken_hierarchy():
        """
        إصلاح الهرمية المكسورة لجميع الحسابات
        
        يقوم بـ:
        1. إعادة ربط الحسابات الفرعية تلقائياً
        2. إصلاح الحسابات غير المربوطة
        3. التحقق من عدم وجود حلقات مفرغة
        """
        accounts = Account.objects.filter(is_active=True).order_by('code')
        fixed_count = 0
        
        for account in accounts:
            if account.is_child_account() and not account.has_parent():
                auto_parent = account.get_auto_parent()
                if auto_parent:
                    account.parent = auto_parent
                    account.save(update_fields=['parent'])
                    fixed_count += 1
        
        return fixed_count


class JournalEntry(models.Model):
    """قيد محاسبي"""
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
    reference_type = models.CharField(_('Reference Type'), max_length=20, blank=True)
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
        default_permissions = []  # No default permissions
        permissions = [
            ("can_view_journal_entries", _("View Journal Entries")),
            ("can_add_journal_entries", _("Add Journal Entry")),
            ("can_edit_journal_entries", _("Edit Journal Entry")),
            ("can_delete_journal_entries", _("Delete Journal Entry")),
        ]

    def __str__(self):
        return f"{self.entry_number} - {self.description}"

    def save(self, *args, **kwargs):
        if not self.entry_number:
            self.entry_number = self.generate_entry_number()
        
        # تحديث الحقول المرتبطة بالفواتير
        # إزالة منطق reference_type بسبب إزالة الحقل
        
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
        default_permissions = []  # No permissions needed

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
        
        # IFRS Compliance: Prevent entries on parent accounts
        # All entries must be recorded at the leaf (child) account level
        if self.account:
            has_active_children = self.account.children.filter(is_active=True).exists()
            if has_active_children:
                raise ValidationError(
                    _('Cannot record entries on parent account "%(account)s". '
                      'All entries must be recorded on leaf (child) accounts only '
                      'to ensure IFRS compliance.') 
                    % {'account': self.account.name}
                )

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
        default_permissions = []  # No default permissions
        permissions = [
            ("can_perform_year_end_closing", _("Perform Year End Closing")),
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
        
        # الحصول على جميع حسابات الإيرادات والمصروفات النشطة
        revenue_accounts = Account.objects.filter(
            account_type__in=['revenue', 'sales'], 
            is_active=True
        )
        expense_accounts = Account.objects.filter(
            account_type__in=['expense', 'purchases'], 
            is_active=True
        )
        
        # إقفال حسابات الإيرادات (مدين)
        # نقفل فقط الحسابات التي لها رصيد فعلي
        for account in revenue_accounts:
            balance = account.get_balance(as_of_date=self.closing_date)
            # تجاهل الحسابات التي ليس لها رصيد أو التي هي حسابات رئيسية بدون حركات مباشرة
            if balance > 0:
                # التحقق من وجود حركات مباشرة على الحساب
                has_direct_lines = JournalLine.objects.filter(
                    account=account,
                    journal_entry__entry_date__year=self.year
                ).exists()
                
                if has_direct_lines:
                    JournalLine.objects.create(
                        journal_entry=closing_entry,
                        account=account,
                        debit=balance,
                        credit=Decimal('0'),
                        line_description=f"إقفال حساب {account.name}"
                    )
        
        # إقفال حسابات المصروفات (دائن)
        for account in expense_accounts:
            balance = account.get_balance(as_of_date=self.closing_date)
            if balance > 0:
                # التحقق من وجود حركات مباشرة على الحساب
                has_direct_lines = JournalLine.objects.filter(
                    account=account,
                    journal_entry__entry_date__year=self.year
                ).exists()
                
                if has_direct_lines:
                    JournalLine.objects.create(
                        journal_entry=closing_entry,
                        account=account,
                        debit=Decimal('0'),
                        credit=balance,
                        line_description=f"إقفال حساب {account.name}"
                    )
        
        # نقل صافي الربح أو الخسارة إلى رأس المال
        retained_earnings = Account.objects.filter(account_type='equity', name__icontains='رأس المال').first()
        if retained_earnings:
            if self.net_profit > 0:
                # ربح: دائن في رأس المال
                JournalLine.objects.create(
                    journal_entry=closing_entry,
                    account=retained_earnings,
                    debit=Decimal('0'),
                    credit=self.net_profit,
                    line_description="نقل صافي الربح إلى رأس المال"
                )
            elif self.net_profit < 0:
                # خسارة: مدين في رأس المال
                loss = abs(self.net_profit)
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


class FiscalYear(models.Model):
    """السنة المالية"""
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('closed', _('Closed')),
    ]
    
    year = models.IntegerField(_('Fiscal Year'), unique=True)
    start_date = models.DateField(_('Start Date'))
    end_date = models.DateField(_('End Date'))
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='active')
    is_current = models.BooleanField(_('Current Year'), default=False)
    
    # الأرصدة الافتتاحية
    opening_entry = models.OneToOneField(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True,
                                        verbose_name=_('Opening Entry'), related_name='fiscal_year_opening')
    
    # مرتبط بالإقفال (إن وجد)
    closing = models.OneToOneField(YearEndClosing, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name=_('Year End Closing'), related_name='fiscal_year')
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Fiscal Year')
        verbose_name_plural = _('Fiscal Years')
        ordering = ['-year']
        default_permissions = []  # No default permissions
        permissions = [
            ("can_open_fiscal_year", _("Open Fiscal Year")),
            ("can_access_closed_years", _("Access Closed Fiscal Years")),
        ]
    
    def __str__(self):
        return f"{_('Fiscal Year')} {self.year}"
    
    def save(self, *args, **kwargs):
        # إذا تم تعيين هذه السنة كالسنة الحالية، إلغاء التعيين من السنوات الأخرى
        if self.is_current:
            FiscalYear.objects.filter(is_current=True).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)
    
    def create_opening_balances(self, previous_year=None):
        """
        إنشاء الأرصدة الافتتاحية للسنة الجديدة
        ينقل أرصدة الأصول والخصوم وحقوق الملكية من السنة السابقة
        """
        from datetime import datetime
        
        # إذا لم يتم تحديد السنة السابقة، استخدم السنة التي قبلها
        if previous_year is None:
            try:
                previous_year = FiscalYear.objects.get(year=self.year - 1)
            except FiscalYear.DoesNotExist:
                return False, _("Previous fiscal year not found")
        
        # التأكد من أن السنة السابقة مقفلة
        if previous_year.status != 'closed':
            return False, _("Previous fiscal year must be closed first")
        
        # إنشاء قيد الأرصدة الافتتاحية
        opening_entry = JournalEntry.objects.create(
            entry_date=self.start_date,
            description=f"الأرصدة الافتتاحية للسنة المالية {self.year}",
            reference_type='opening_balance',
            total_amount=Decimal('0'),
            created_by=self.created_by
        )
        
        # الحسابات التي تنتقل أرصدتها (الميزانية العمومية فقط - لا تنتقل الإيرادات والمصروفات)
        balance_sheet_types = ['asset', 'liability', 'equity']
        accounts = Account.objects.filter(
            account_type__in=balance_sheet_types,
            is_active=True
        )
        
        total_debits = Decimal('0')
        total_credits = Decimal('0')
        
        for account in accounts:
            # حساب الرصيد في نهاية السنة السابقة
            balance = account.get_balance(as_of_date=previous_year.end_date)
            
            if balance != 0:
                # التحقق من وجود حركات على الحساب في السنة السابقة
                has_movements = JournalLine.objects.filter(
                    account=account,
                    journal_entry__entry_date__range=[previous_year.start_date, previous_year.end_date]
                ).exists()
                
                if has_movements or balance != 0:
                    # حسابات الأصول والمصروفات طبيعتها مدينة
                    # حسابات الخصوم والإيرادات وحقوق الملكية طبيعتها دائنة
                    if account.account_type in ['asset']:
                        # رصيد موجب = مدين
                        debit = abs(balance) if balance > 0 else Decimal('0')
                        credit = abs(balance) if balance < 0 else Decimal('0')
                    else:  # liability, equity
                        # رصيد موجب = دائن
                        credit = abs(balance) if balance > 0 else Decimal('0')
                        debit = abs(balance) if balance < 0 else Decimal('0')
                    
                    if debit > 0 or credit > 0:
                        JournalLine.objects.create(
                            journal_entry=opening_entry,
                            account=account,
                            debit=debit,
                            credit=credit,
                            line_description=f"رصيد افتتاحي من سنة {previous_year.year}"
                        )
                        
                        total_debits += debit
                        total_credits += credit
        
        # تحديث إجمالي القيد
        opening_entry.total_amount = max(total_debits, total_credits)
        opening_entry.save()
        
        # ربط القيد بالسنة المالية
        self.opening_entry = opening_entry
        self.save()
        
        return True, _("Opening balances created successfully")
