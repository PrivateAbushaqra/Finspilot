from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()


class Currency(models.Model):
    """نموذج العملات"""
    CURRENCY_CHOICES = [
        ('SAR', _('الريال السعودي')),
        ('USD', _('الدولار الأمريكي')),
        ('EUR', _('اليورو')),
        ('GBP', _('الجنيه الإسترليني')),
        ('JOD', _('الدينار الأردني')),
        ('AED', _('الدرهم الإماراتي')),
        ('KWD', _('الدينار الكويتي')),
        ('QAR', _('الريال القطري')),
        ('BHD', _('الدينار البحريني')),
        ('OMR', _('الريال العماني')),
        ('EGP', _('الجنيه المصري')),
        ('LBP', _('الليرة اللبنانية')),
        ('SYP', _('الليرة السورية')),
        ('IQD', _('الدينار العراقي')),
        ('LYD', _('الدينار الليبي')),
        ('TND', _('الدينار التونسي')),
        ('DZD', _('الدينار الجزائري')),
        ('MAD', _('الدرهم المغربي')),
        ('SDG', _('الجنيه السوداني')),
        ('YER', _('الريال اليمني')),
        ('JPY', _('الين الياباني')),
        ('CHF', _('الفرنك السويسري')),
        ('CAD', _('الدولار الكندي')),
        ('AUD', _('الدولار الأسترالي')),
        ('CNY', _('اليوان الصيني')),
        ('INR', _('الروبية الهندية')),
        ('TRY', _('الليرة التركية')),
        ('IRR', _('الريال الإيراني')),
        ('PKR', _('الروبية الباكستانية')),
        ('AFN', _('الأفغاني')),
    ]

    code = models.CharField(_('رمز العملة'), max_length=3, unique=True, choices=CURRENCY_CHOICES)
    name = models.CharField(_('اسم العملة'), max_length=100)
    symbol = models.CharField(_('رمز العملة'), max_length=10, blank=True)
    exchange_rate = models.DecimalField(_('سعر الصرف'), max_digits=10, decimal_places=4, default=1.0000,
                                      help_text=_('سعر الصرف مقابل العملة الأساسية'))
    is_base_currency = models.BooleanField(_('عملة أساسية'), default=False,
                                         help_text=_('العملة الأساسية للنظام'))
    is_active = models.BooleanField(_('نشط'), default=True)
    decimal_places = models.PositiveIntegerField(_('عدد الخانات العشرية'), default=2)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('عملة')
        verbose_name_plural = _('العملات')
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        # إذا تم تحديد هذه العملة كعملة أساسية، قم بإلغاء العملة الأساسية السابقة
        if self.is_base_currency:
            Currency.objects.filter(is_base_currency=True).exclude(pk=self.pk).update(is_base_currency=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_base_currency(cls):
        """الحصول على العملة الأساسية"""
        return cls.objects.filter(is_base_currency=True).first()

    @classmethod
    def get_active_currencies(cls):
        """الحصول على العملات النشطة"""
        return cls.objects.filter(is_active=True)


class CompanySettings(models.Model):
    """إعدادات الشركة"""
    company_name = models.CharField(_('اسم الشركة'), max_length=200)
    company_name_en = models.CharField(_('اسم الشركة بالإنجليزية'), max_length=200, blank=True)
    tax_number = models.CharField(_('الرقم الضريبي'), max_length=50, blank=True)
    commercial_registration = models.CharField(_('السجل التجاري'), max_length=50, blank=True)
    phone = models.CharField(_('الهاتف'), max_length=20, blank=True)
    email = models.EmailField(_('البريد الإلكتروني'), blank=True)
    address = models.TextField(_('العنوان'), blank=True)
    website = models.URLField(_('الموقع الإلكتروني'), blank=True)
    logo = models.ImageField(_('الشعار'), upload_to='company/', blank=True)
    
    # إعدادات العملة
    base_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, 
                                    verbose_name=_('العملة الأساسية'),
                                    help_text=_('العملة الأساسية للنظام'))
    show_currency_symbol = models.BooleanField(_('إظهار رمز العملة'), default=True)
    
    # إعدادات التاريخ والوقت
    date_format = models.CharField(_('تنسيق التاريخ'), max_length=20, default='Y-m-d')
    time_format = models.CharField(_('تنسيق الوقت'), max_length=20, default='H:i')
    
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
    
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('إعدادات الشركة')
        verbose_name_plural = _('إعدادات الشركة')

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        # إذا لم توجد إعدادات شركة أخرى، قم بإنشاء واحدة فقط
        if not self.pk and CompanySettings.objects.exists():
            return
        super().save(*args, **kwargs)
