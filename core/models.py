from django.db import models
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
        ('purchase_invoice', _('فاتورة المشتريات')),
        ('purchase_return', _('مردود المشتريات')),
        ('bank_transfer', _('التحويل بين الحسابات البنكية')),
        ('bank_cash_transfer', _('التحويل بين البنوك والصناديق')),
        ('cashbox_transfer', _('التحويل بين الصناديق')),
        ('journal_entry', _('القيود المحاسبية')),
        ('warehouse_transfer', _('التحويل بين المستودعات')),
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
        """الحصول على الرقم التالي مع التحقق من آخر رقم مُستخدم فعلياً"""
        # للتحويلات بين الصناديق، تحقق من آخر رقم مُستخدم فعلياً
        if self.document_type == 'cashbox_transfer':
            from cashboxes.models import CashboxTransfer
            
            # البحث عن آخر تحويل بنفس البادئة
            last_transfer = CashboxTransfer.objects.filter(
                transfer_number__startswith=self.prefix
            ).order_by('-transfer_number').first()
            
            if last_transfer:
                try:
                    # استخراج الرقم من آخر تحويل
                    last_number_str = last_transfer.transfer_number[len(self.prefix):]
                    last_number = int(last_number_str)
                    
                    # تحديد الرقم التالي
                    next_number = last_number + 1
                    
                    # تحديث current_number إذا كان أقل من الرقم الفعلي
                    if self.current_number <= last_number:
                        self.current_number = next_number
                    else:
                        next_number = self.current_number
                    
                except (ValueError, IndexError):
                    # في حالة فشل تحليل الرقم، استخدم current_number
                    next_number = self.current_number
            else:
                # لا توجد تحويلات، استخدم current_number
                next_number = self.current_number
        
        # لمردود المبيعات، تحقق من آخر رقم مُستخدم فعلياً
        elif self.document_type == 'sales_return':
            from sales.models import SalesReturn
            
            # البحث عن آخر مردود بنفس البادئة
            last_return = SalesReturn.objects.filter(
                return_number__startswith=self.prefix
            ).order_by('-return_number').first()
            
            if last_return:
                try:
                    # استخراج الرقم من آخر مردود
                    last_number_str = last_return.return_number[len(self.prefix):]
                    last_number = int(last_number_str)
                    
                    # تحديد الرقم التالي
                    next_number = last_number + 1
                    
                    # تحديث current_number إذا كان أقل من الرقم الفعلي
                    if self.current_number <= last_number:
                        self.current_number = next_number
                    else:
                        next_number = self.current_number
                    
                except (ValueError, IndexError):
                    # في حالة فشل تحليل الرقم، استخدم current_number
                    next_number = self.current_number
            else:
                # لا توجد مرتجعات، استخدم current_number
                next_number = self.current_number
        
        else:
            # للأنواع الأخرى، استخدم الطريقة العادية
            next_number = self.current_number
        
        number = str(next_number).zfill(self.digits)
        self.current_number = next_number + 1
        self.save()
        return f"{self.prefix}{number}"

    def get_formatted_number(self, number=None):
        """تنسيق الرقم"""
        if number is None:
            number = self.current_number
        return f"{self.prefix}{str(number).zfill(self.digits)}"


class AuditLog(models.Model):
    """سجل المراجعة"""
    ACTION_TYPES = [
        ('create', _('إنشاء')),
        ('update', _('تحديث')),
        ('delete', _('حذف')),
        ('view', _('عرض')),
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
