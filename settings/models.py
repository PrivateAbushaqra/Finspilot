from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

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
    exchange_rate = models.DecimalField(_('Exchange Rate'), max_digits=10, decimal_places=4, default=1.0000,
                                      help_text=_('سعر الصرف مقابل العملة الأساسية'))
    is_base_currency = models.BooleanField(_('عملة أساسية'), default=False,
                                         help_text=_('العملة الأساسية للنظام'))
    is_active = models.BooleanField(_('Active'), default=True)
    decimal_places = models.PositiveIntegerField(_('عدد الخانات العشرية'), default=2)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

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
    phone = models.CharField(_('Phone'), max_length=20, blank=True)
    email = models.EmailField(_('Email'), blank=True)
    address = models.TextField(_('العنوان'), blank=True)
    website = models.URLField(_('الموقع الإلكتروني'), blank=True)
    logo = models.ImageField(_('شعار الشركة للطباعة'), upload_to='company/', blank=True,
                           help_text=_('شعار الشركة الذي يظهر في المستندات المطبوعة'))
    
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
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('إعدادات الشركة')
        verbose_name_plural = _('إعدادات الشركة')

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        # منع إنشاء إعدادات شركة متعددة - السماح فقط بإعداد واحد
        if not self.pk and CompanySettings.objects.exists():
            return  # منع إنشاء record جديد إذا كان هناك record موجود
        
        # التحقق من صحة قيم الجلسة
        if self.session_timeout_minutes is not None:
            if self.session_timeout_minutes < 5:
                self.session_timeout_minutes = 5
            elif self.session_timeout_minutes > 1440:
                self.session_timeout_minutes = 1440
                
        super().save(*args, **kwargs)


class SuperadminSettings(models.Model):
    """إعدادات متقدمة خاصة بالسوبر أدمين فقط"""
    
    # إعدادات واجهة النظام
    app_logo = models.ImageField(_('شعار النظام'), upload_to='system/', blank=True,
                               help_text=_('الشعار الذي يظهر في واجهة النظام'))
    background_image = models.ImageField(_('صورة الخلفية'), upload_to='system/', blank=True,
                                       help_text=_('صورة خلفية النظام'))
    background_opacity = models.DecimalField(_('شفافية الخلفية'), max_digits=3, decimal_places=2,
                               default=0.8, validators=[MinValueValidator(0.1), MaxValueValidator(1.0)],
                               help_text=_('مستوى شفافية صورة الخلفية (0.1 - 1.0)'))
    
    # إعدادات الألوان
    primary_color = models.CharField(_('اللون الأساسي'), max_length=7, default='#007bff',
                                   help_text=_('اللون الأساسي للنظام (Hex Code)'))
    secondary_color = models.CharField(_('اللون الثانوي'), max_length=7, default='#6c757d',
                                     help_text=_('اللون الثانوي للنظام (Hex Code)'))
    accent_color = models.CharField(_('لون التمييز'), max_length=7, default='#28a745',
                                  help_text=_('لون التمييز للنظام (Hex Code)'))
    
    # إعدادات عامة للنظام
    system_title = models.CharField(_('عنوان النظام'), max_length=100, 
                                  default='نظام إدارة الأعمال',
                                  help_text=_('العنوان الذي يظهر في النظام'))
    system_subtitle = models.CharField(_('العنوان الفرعي'), max_length=200, blank=True,
                                     help_text=_('العنوان الفرعي للنظام'))
    show_company_info = models.BooleanField(_('إظهار معلومات الشركة'), default=True,
                                          help_text=_('إظهار معلومات الشركة في الواجهة'))
    
    # معلومات النظام
    last_updated = models.DateTimeField(_('آخر تحديث'), auto_now=True)
    updated_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, 
                                 null=True, blank=True, verbose_name=_('تم التحديث بواسطة'))
    
    class Meta:
        verbose_name = _('إعدادات السوبر أدمين')
        verbose_name_plural = _('إعدادات السوبر أدمين')
        db_table = 'superadmin_settings'
    
    def __str__(self):
        return f"إعدادات النظام - {self.system_title}"
    
    @classmethod
    def get_settings(cls):
        """الحصول على إعدادات النظام أو إنشاؤها إذا لم تكن موجودة"""
        settings, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'system_title': 'نظام إدارة الأعمال',
                'primary_color': '#007bff',
                'secondary_color': '#6c757d',
                'accent_color': '#28a745',
                'background_opacity': 0.8,
            }
        )
        return settings
    
    def save(self, *args, **kwargs):
        # التأكد من وجود إعداد واحد فقط
        self.pk = 1
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # منع حذف الإعدادات
        pass


class DocumentPrintSettings(models.Model):
    """إعدادات طباعة المستندات"""
    
    PAPER_SIZE_CHOICES = [
        ('A4', 'A4'),
        ('A5', 'A5'),
    ]
    
    POSITION_CHOICES = [
        ('left', _('يسار')),
        ('center', _('وسط')),
        ('right', _('يمين')),
    ]
    
    ORIENTATION_CHOICES = [
        ('portrait', _('عمودي')),
        ('landscape', _('أفقي')),
    ]
    
    document_type = models.CharField(_("نوع المستند"), max_length=100, unique=True, help_text=_("مثال: invoice, receipt, purchase_order"))
    document_name_ar = models.CharField(_("اسم المستند بالعربية"), max_length=200)
    document_name_en = models.CharField(_("اسم المستند بالإنجليزية"), max_length=200)
    
    # إعدادات الورقة
    paper_size = models.CharField(_("حجم الورقة"), max_length=2, choices=PAPER_SIZE_CHOICES, default='A4')
    orientation = models.CharField(_("اتجاه الورقة"), max_length=10, choices=ORIENTATION_CHOICES, default='portrait')
    margins = models.IntegerField(_("الهوامش"), default=20, 
                                 help_text=_("هوامش الصفحة بالبكسل (قيمة موحدة لجميع الجهات)"))
    
    # إعدادات الرأس
    header_left_content = models.TextField(_("محتوى يسار الرأس"), blank=True, null=True)
    header_center_content = models.TextField(_("محتوى وسط الرأس"), blank=True, null=True)
    header_right_content = models.TextField(_("محتوى يمين الرأس"), blank=True, null=True)
    
    # إعدادات موقع الشعار
    logo_position = models.CharField(_("موقع الشعار"), max_length=10, choices=POSITION_CHOICES, default='center')
    show_logo = models.BooleanField(_("إظهار الشعار"), default=True)
    
    # إعدادات التذييل
    footer_left_content = models.TextField(_("محتوى يسار التذييل"), blank=True, null=True)
    footer_center_content = models.TextField(_("محتوى وسط التذييل"), blank=True, null=True)
    footer_right_content = models.TextField(_("محتوى يمين التذييل"), blank=True, null=True)
    
    # معلومات إضافية
    show_company_info = models.BooleanField(_("إظهار معلومات الشركة"), default=True)
    show_date_time = models.BooleanField(_("إظهار التاريخ والوقت"), default=True)
    show_page_numbers = models.BooleanField(_("إظهار أرقام الصفحات"), default=True)
    
    # معلومات النظام
    is_default = models.BooleanField(_("افتراضي"), default=False, help_text=_("هل هذا هو التصميم الافتراضي لهذا النوع من المستندات"))
    is_active = models.BooleanField(_("نشط"), default=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("تاريخ التحديث"), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_print_settings', verbose_name=_("أنشئ بواسطة"))
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_print_settings', verbose_name=_("حُدث بواسطة"))
    
    class Meta:
        verbose_name = _("إعدادات طباعة المستند")
        verbose_name_plural = _("إعدادات طباعة المستندات")
        ordering = ['document_name_ar']
    
    def __str__(self):
        return f"{self.document_name_ar} ({self.document_type})"

    @classmethod
    def get_document_settings(cls, document_type):
        """الحصول على إعدادات مستند محدد"""
        try:
            return cls.objects.get(document_type=document_type, is_active=True)
        except cls.DoesNotExist:
            # إنشاء إعدادات افتراضية للمستند
            return cls.objects.create(
                document_type=document_type,
                document_name_ar=document_type.replace('_', ' ').title(),
                document_name_en=document_type.replace('_', ' ').title(),
                paper_size='A4',
                orientation='portrait',
                margins=20,
                show_logo=True,
                logo_position='center',
                show_company_info=True,
                show_date_time=True,
                show_page_numbers=True,
                is_default=True
            )


class JoFotaraSettings(models.Model):
    """إعدادات الربط الإلكتروني مع دائرة ضريبة الدخل والمبيعات (JoFotara)"""
    api_url = models.URLField(_('API URL'), blank=True, null=True, default='', help_text=_('رابط API لنظام JoFotara'))
    client_id = models.CharField(_('Client ID'), max_length=255, blank=True, default='', help_text=_('معرف العميل'))
    client_secret = models.CharField(_('Client Secret'), max_length=255, blank=True, default='', help_text=_('سر العميل'))
    is_active = models.BooleanField(_('نشط'), default=False, help_text=_('تفعيل الربط مع JoFotara'))
    use_mock_api = models.BooleanField(_('استخدام Mock API'), default=True, help_text=_('استخدام API وهمي للاختبار'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('إعدادات JoFotara')
        verbose_name_plural = _('إعدادات JoFotara')

    def __str__(self):
        return f"JoFotara Settings - {'Active' if self.is_active else 'Inactive'}"


class SettingsPermissionManager(models.Model):
    """نموذج إدارة الصلاحيات لتطبيق الإعدادات"""
    
    class Meta:
        managed = False  # هذا النموذج لن ينشئ جدول في قاعدة البيانات
        permissions = [
            ('can_access_print_design', _('Can access print design settings')),
        ]
        verbose_name = _('Settings Permission Manager')
        verbose_name_plural = _('Settings Permission Managers')
        default_permissions = ()  # لا نريد الصلاحيات الافتراضية

    def __str__(self):
        return "Settings Permission Manager"
