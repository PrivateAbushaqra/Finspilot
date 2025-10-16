# -*- coding: utf-8 -*-
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class CompanySettings(models.Model):
    """إعدادات الشركة"""
    company_name = models.CharField(_('اسم الشركة'), max_length=200, default='FinsPilot')
    logo = models.ImageField(_('شعار الشركة'), upload_to='company/', blank=True, null=True)
    currency = models.CharField(_('Currency'), max_length=10, default='JOD')
    address = models.TextField(_('العنوان'), blank=True)
    phone = models.CharField(_('Phone'), max_length=50, blank=True)
    email = models.EmailField(_('Email'), blank=True)
    tax_number = models.CharField(_('الرقم الضريبي'), max_length=50, blank=True)
    
    # إعدادات الجلسة والأمان
    session_timeout_minutes = models.PositiveIntegerField(
        _('مدة انتهاء الجلسة (بالدقائق)'), 
        default=30,
        help_text=_('مدة عدم النشاط قبل إنهاء الجلسة تلقائياً (بالدقائق)')
    )
    enable_session_timeout = models.BooleanField(
        _('تفعيل انتهاء الجلسة التلقائي'),
        default=True,
        help_text=_('تفعيل إنهاء الجلسة تلقائياً عند عدم النشاط')
    )
    logout_on_browser_close = models.BooleanField(
        _('تسجيل الخروج عند إغلاق المتصفح'),
        default=True,
        help_text=_('إنهاء الجلسة تلقائياً عند إغلاق المتصفح')
    )
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('إعدادات الشركة')
        verbose_name_plural = _('إعدادات الشركة')

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
        ('sales_invoice', _('فاتورة المبيعات')),
        ('pos_invoice', _('فاتورة نقطة البيع')),
        ('sales_return', _('مردود المبيعات')),
        ('credit_note', _('إشعار دائن')),
        ('debit_note', _('إشعار مدين')),
        ('purchase_invoice', _('فاتورة المشتريات')),
        ('purchase_return', _('مردود المشتريات')),
        ('bank_transfer', _('التحويل بين الحسابات البنكية')),
        ('bank_cash_transfer', _('التحويل بين البنوك والصناديق')),
        ('cashbox_transfer', _('التحويل بين الصناديق')),
        ('journal_entry', _('القيود المحاسبية')),
        ('warehouse_transfer', _('Transfer Between Warehouses')),
        ('receipt_voucher', _('سند قبض')),
        ('payment_voucher', _('سند صرف')),
    ]

    document_type = models.CharField(_('نوع المستند'), max_length=50, choices=DOCUMENT_TYPES, unique=True)
    prefix = models.CharField(_('البادئة'), max_length=10, default='')
    digits = models.PositiveIntegerField(_('عدد الخانات'), default=6)
    current_number = models.PositiveIntegerField(_('الرقم الحالي'), default=1)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('تسلسل أرقام المستندات')
        verbose_name_plural = _('تسلسل أرقام المستندات')

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

            # للتحويلات بين الصناديق
            if seq.document_type == 'cashbox_transfer':
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
        except Exception:
            pass

        candidate = self.current_number
        if last_num is not None and last_num + 1 > candidate:
            candidate = last_num + 1
        return f"{self.prefix}{str(candidate).zfill(self.digits)}"


class AuditLog(models.Model):
    """سجل المراجعة"""
    ACTION_TYPES = [
        ('create', _('إنشاء')),
        ('update', _('تحديث')),
        ('delete', _('حذف')),
        ('view', _('View')),
        ('export', _('تصدير')),
        ('import', _('استيراد')),
        ('reset', _('إعادة تعيين')),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('المستخدم'))
    action_type = models.CharField(_('نوع العملية'), max_length=20, choices=ACTION_TYPES)
    content_type = models.CharField(_('نوع المحتوى'), max_length=100)
    object_id = models.PositiveIntegerField(_('معرف الكائن'), null=True, blank=True)
    description = models.TextField(_('Description'))
    ip_address = models.GenericIPAddressField(_('عنوان IP'), null=True, blank=True)
    timestamp = models.DateTimeField(_('الوقت'), auto_now_add=True)

    class Meta:
        verbose_name = _('سجل المراجعة')
        verbose_name_plural = _('سجلات المراجعة')
        ordering = ['-timestamp']
        permissions = [
            ('view_audit_log', _('يمكن عرض سجل الأنشطة')),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_action_type_display()} - {self.content_type}"


class SystemNotification(models.Model):
    """إشعارات النظام"""
    NOTIFICATION_TYPES = [
        ('low_stock', _('انخفاض المخزون')),
        ('system_alert', _('تنبيه النظام')),
        ('user_action', _('إجراء المستخدم')),
    ]

    notification_type = models.CharField(_('نوع الإشعار'), max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(_('العنوان'), max_length=200)
    message = models.TextField(_('الرسالة'))
    is_read = models.BooleanField(_('مقروء'), default=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('المستخدم'), null=True, blank=True)

    class Meta:
        verbose_name = _('إشعار النظام')
        verbose_name_plural = _('إشعارات النظام')
        ordering = ['-created_at']

    def __str__(self):
        return self.title
