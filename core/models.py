# -*- coding: utf-8 -*-
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class CompanySettings(models.Model):
    """إعدادات الشركة"""
    company_name = models.CharField(_('Company Name'), max_length=200, default='FinsPilot')
    logo = models.ImageField(_('Company Logo'), upload_to='company/', blank=True, null=True)
    currency = models.CharField(_('Currency'), max_length=10, default='JOD')
    address = models.TextField(_('Address'), blank=True)
    phone = models.CharField(_('Phone'), max_length=50, blank=True)
    email = models.EmailField(_('Email'), blank=True)
    tax_number = models.CharField(_('Tax Number'), max_length=50, blank=True)
    default_tax_rate = models.DecimalField(_('Default Tax Rate'), max_digits=5, decimal_places=2, 
                                         validators=[MinValueValidator(0), MaxValueValidator(100)], default=0)
    
    # إعدادات الجلسة والأمان
    session_timeout_minutes = models.PositiveIntegerField(
        _('Session Timeout (Minutes)'), 
        default=30,
        help_text=_('مدة عدم النشاط قبل إنهاء الجلسة تلقائياً (بالدقائق)')
    )
    enable_session_timeout = models.BooleanField(
        _('Enable Automatic Session Timeout'),
        default=True,
        help_text=_('تفعيل إنهاء الجلسة تلقائياً عند عدم النشاط')
    )
    logout_on_browser_close = models.BooleanField(
        _('Logout on Browser Close'),
        default=True,
        help_text=_('إنهاء الجلسة تلقائياً عند إغلاق المتصفح')
    )
    
    # إعدادات سلامة البيانات
    enable_integrity_checks = models.BooleanField(
        _('Enable Data Integrity Checks'),
        default=True,
        help_text=_('تفعيل الفحوصات التلقائية لسلامة البيانات المحاسبية')
    )
    integrity_check_frequency = models.PositiveIntegerField(
        _('Integrity Check Frequency (Hours)'),
        default=24,
        help_text=_('عدد الساعات بين كل فحص لسلامة البيانات')
    )
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Company Settings')
        verbose_name_plural = _('Company Settings')

    def __str__(self):
        return self.company_name

    @classmethod
    def get_settings(cls):
        """الحصول على إعدادات الشركة"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings


class DocumentSequence(models.Model):
    """تسلسل أرقام المستندات"""
    DOCUMENT_TYPES = [
        ('sales_invoice', _('Sales Invoice')),
        ('pos_invoice', _('POS Invoice')),
        ('sales_return', _('Sales Return')),
        ('credit_note', _('Credit Note')),
        ('debit_note', _('Debit Note')),
        ('purchase_invoice', _('Purchase Invoice')),
        ('purchase_return', _('Purchase Return')),
        ('bank_transfer', _('Bank Account Transfer')),
        ('bank_cash_transfer', _('Bank to Cashbox Transfer')),
        ('cashbox_transfer', _('Cashbox Transfer')),
        ('journal_entry', _('Journal Entries')),
        ('warehouse_transfer', _('Transfer Between Warehouses')),
        ('receipt_voucher', _('Receipt Voucher')),
        ('payment_voucher', _('Payment Voucher')),
    ]

    document_type = models.CharField(_('Document Type'), max_length=50, choices=DOCUMENT_TYPES, unique=True)
    prefix = models.CharField(_('Prefix'), max_length=10, default='')
    digits = models.PositiveIntegerField(_('Number of Digits'), default=6)
    current_number = models.PositiveIntegerField(_('Current Number'), default=1)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Document Sequences')
        verbose_name_plural = _('Document Sequences')

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.prefix}"

    def get_next_number(self):
        """الحصول على الرقم التالي مع قفل ذرّي ومزامنة مع آخر رقم مُستخدم فعلياً.

        يعالج حالات التعارض والتوازي لضمان فريدة رقم المستند.
        """
        # نعيد قفل سجل التسلسل ذاته داخل معاملة ذرّية لتفادي السباقات
        with transaction.atomic():
            seq = type(self).objects.select_for_update().get(pk=self.pk)

            def _sync_with_last_used(last_number: int | None) -> int:
                """أعد اختيار الرقم التالي بناءً على آخر رقم مُستخدم والـ current_number."""
                if last_number is not None and last_number >= seq.current_number:
                    return last_number + 1
                return seq.current_number

            # للتحويلات بين البنوك والصناديق
            if seq.document_type == 'bank_cash_transfer':
                from cashboxes.models import CashboxTransfer
                last_transfer = (
                    CashboxTransfer.objects
                    .filter(transfer_number__startswith=seq.prefix)
                    .order_by('-transfer_number')
                    .first()
                )
                last_num = None
                if last_transfer:
                    try:
                        last_num = int(str(last_transfer.transfer_number)[len(seq.prefix):])
                    except Exception:
                        last_num = None
                next_number = _sync_with_last_used(last_num)

            # مردود المبيعات
            elif seq.document_type == 'sales_return':
                from sales.models import SalesReturn
                last_return = (
                    SalesReturn.objects
                    .filter(return_number__startswith=seq.prefix)
                    .order_by('-return_number')
                    .first()
                )
                last_num = None
                if last_return:
                    try:
                        last_num = int(str(last_return.return_number)[len(seq.prefix):])
                    except Exception:
                        last_num = None
                next_number = _sync_with_last_used(last_num)

            # فواتير المبيعات (بما فيها POS عند استخدام نفس النموذج)
            elif seq.document_type in ('sales_invoice', 'pos_invoice'):
                from sales.models import SalesInvoice
                existing_numbers = (
                    SalesInvoice.objects
                    .filter(invoice_number__startswith=seq.prefix)
                    .values_list('invoice_number', flat=True)
                )
                last_num = None
                max_found = -1
                for inv in existing_numbers:
                    tail = str(inv)[len(seq.prefix):]
                    if tail.isdigit():
                        try:
                            num = int(tail)
                            if num > max_found:
                                max_found = num
                        except Exception:
                            continue
                if max_found >= 0:
                    last_num = max_found
                next_number = _sync_with_last_used(last_num)

            # القيود المحاسبية
            elif seq.document_type == 'journal_entry':
                from journal.models import JournalEntry
                existing_numbers = (
                    JournalEntry.objects
                    .filter(entry_number__startswith=seq.prefix)
                    .values_list('entry_number', flat=True)
                )
                last_num = None
                max_found = -1
                for entry in existing_numbers:
                    tail = str(entry)[len(seq.prefix):]
                    if tail.isdigit():
                        try:
                            num = int(tail)
                            if num > max_found:
                                max_found = num
                        except Exception:
                            continue
                if max_found >= 0:
                    last_num = max_found
                next_number = _sync_with_last_used(last_num)

            else:
                # الأنواع الأخرى: استخدم current_number كما هو
                next_number = seq.current_number

            number = str(next_number).zfill(seq.digits)
            seq.current_number = next_number + 1
            seq.save(update_fields=['current_number', 'updated_at'])
            return f"{seq.prefix}{number}"

    def get_formatted_number(self, number=None):
        """تنسيق الرقم"""
        if number is None:
            number = self.current_number
        return f"{self.prefix}{str(number).zfill(self.digits)}"

    def _extract_tail_number(self, full_number: str):
        """استخراج الجزء الرقمي بعد البادئة إن أمكن."""
        try:
            if not isinstance(full_number, str):
                return None
            if not full_number.startswith(self.prefix):
                return None
            tail = full_number[len(self.prefix):]
            if tail.isdigit():
                return int(tail)
        except Exception:
            return None
        return None

    def advance_to_at_least(self, absolute_tail_number: int):
        """تقديم current_number بحيث يصبح على الأقل tail+1 بشكل ذرّي."""
        with transaction.atomic():
            seq = type(self).objects.select_for_update().get(pk=self.pk)
            target = int(absolute_tail_number) + 1
            if target > seq.current_number:
                seq.current_number = target
                seq.save(update_fields=['current_number', 'updated_at'])

    def peek_next_number(self):
        """معاينة الرقم التالي دون حفظ أو قفل: يحسب بالاعتماد على أعلى رقم مستخدم فعلياً وcurrent_number."""
        last_num = None
        try:
            if self.document_type in ('sales_invoice', 'pos_invoice'):
                from sales.models import SalesInvoice
                existing_numbers = (
                    SalesInvoice.objects
                    .filter(invoice_number__startswith=self.prefix)
                    .values_list('invoice_number', flat=True)
                )
                max_found = -1
                for inv in existing_numbers:
                    tail = str(inv)[len(self.prefix):]
                    if tail.isdigit():
                        try:
                            num = int(tail)
                            if num > max_found:
                                max_found = num
                        except Exception:
                            continue
                if max_found >= 0:
                    last_num = max_found
            elif self.document_type == 'sales_return':
                from sales.models import SalesReturn
                last = (
                    SalesReturn.objects
                    .filter(return_number__startswith=self.prefix)
                    .order_by('-return_number')
                    .first()
                )
                if last:
                    n = str(last.return_number)[len(self.prefix):]
                    last_num = int(n) if n.isdigit() else None
            elif self.document_type == 'cashbox_transfer':
                from cashboxes.models import CashboxTransfer
                last = (
                    CashboxTransfer.objects
                    .filter(transfer_number__startswith=self.prefix)
                    .order_by('-transfer_number')
                    .first()
                )
                if last:
                    n = str(last.transfer_number)[len(self.prefix):]
                    last_num = int(n) if n.isdigit() else None
            elif self.document_type == 'bank_cash_transfer':
                from cashboxes.models import CashboxTransfer
                last = (
                    CashboxTransfer.objects
                    .filter(transfer_number__startswith=self.prefix)
                    .order_by('-transfer_number')
                    .first()
                )
                if last:
                    n = str(last.transfer_number)[len(self.prefix):]
                    last_num = int(n) if n.isdigit() else None
            elif self.document_type == 'journal_entry':
                from journal.models import JournalEntry
                last = (
                    JournalEntry.objects
                    .filter(entry_number__startswith=self.prefix)
                    .order_by('-entry_number')
                    .first()
                )
                if last:
                    n = str(last.entry_number)[len(self.prefix):]
                    last_num = int(n) if n.isdigit() else None
            elif self.document_type == 'warehouse_transfer':
                from inventory.models import WarehouseTransfer
                last = (
                    WarehouseTransfer.objects
                    .filter(transfer_number__startswith=self.prefix)
                    .order_by('-transfer_number')
                    .first()
                )
                if last:
                    n = str(last.transfer_number)[len(self.prefix):]
                    last_num = int(n) if n.isdigit() else None
        except Exception:
            pass

        candidate = self.current_number
        if last_num is not None and last_num + 1 > candidate:
            candidate = last_num + 1
        return f"{self.prefix}{str(candidate).zfill(self.digits)}"


class AuditLog(models.Model):
    """سجل المراجعة"""
    ACTION_TYPES = [
        ('create', _('Create')),
        ('update', _('Update')),
        ('delete', _('Delete')),
        ('view', _('View')),
        ('access', _('Access')),
        ('export', _('Export')),
        ('import', _('Import')),
        ('reset', _('Reset')),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('User'))
    action_type = models.CharField(_('Action Type'), max_length=20, choices=ACTION_TYPES)
    content_type = models.CharField(_('Content Type'), max_length=100)
    object_id = models.PositiveIntegerField(_('Object ID'), null=True, blank=True)
    description = models.TextField(_('Description'))
    ip_address = models.GenericIPAddressField(_('IP Address'), null=True, blank=True)
    timestamp = models.DateTimeField(_('Time'), auto_now_add=True)

    class Meta:
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        ordering = ['-timestamp']
        permissions = [
            ('view_audit_log', _('Can view audit log')),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_action_type_display()} - {self.content_type}"


class SystemNotification(models.Model):
    """إشعارات النظام"""
    NOTIFICATION_TYPES = [
        ('low_stock', _('Low Stock')),
        ('system_alert', _('System Alert')),
        ('user_action', _('User Action')),
    ]

    notification_type = models.CharField(_('Notification Type'), max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(_('Title'), max_length=200)
    message = models.TextField(_('Message'))
    is_read = models.BooleanField(_('Read'), default=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('User'), null=True, blank=True)

    class Meta:
        verbose_name = _('System Notification')
        verbose_name_plural = _('System Notifications')
        ordering = ['-created_at']

    def __str__(self):
        return self.title
