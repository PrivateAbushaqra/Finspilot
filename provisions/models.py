from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from django.core.validators import MinValueValidator

User = settings.AUTH_USER_MODEL


class ProvisionType(models.Model):
    """أنواع المخصصات"""
    name = models.CharField(_('اسم النوع'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Created By'))

    class Meta:
        verbose_name = _('نوع المخصص')
        verbose_name_plural = _('أنواع المخصصات')
        ordering = ['name']

    def __str__(self):
        return self.name


class Provision(models.Model):
    """المخصصات المحاسبية"""
    PROVISION_TYPES = [
        ('bad_debt', _('مخصص الديون المشكوك في تحصيلها')),
        ('depreciation', _('مخصص الاهلاك')),
        ('inventory', _('مخصص المخزون')),
        ('warranty', _('مخصص الضمان')),
        ('tax', _('مخصص الضرائب')),
        ('other', _('مخصصات أخرى')),
    ]

    provision_type = models.CharField(_('نوع المخصص'), max_length=20, choices=PROVISION_TYPES)
    custom_type = models.ForeignKey(ProvisionType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('نوع مخصص مخصص'))
    name = models.CharField(_('اسم المخصص'), max_length=200)
    description = models.TextField(_('Description'), blank=True)

    # الربط بالحسابات
    related_account = models.ForeignKey('journal.Account', on_delete=models.CASCADE, verbose_name=_('الحساب المرتبط'))
    provision_account = models.ForeignKey('journal.Account', on_delete=models.CASCADE, verbose_name=_('حساب المخصص'), related_name='provisions')

    # المبالغ والفترات
    amount = models.DecimalField(_('المبلغ'), max_digits=15, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    accumulated_amount = models.DecimalField(_('المبلغ المتراكم'), max_digits=15, decimal_places=3, default=0)
    fiscal_year = models.IntegerField(_('السنة المالية'))
    start_date = models.DateField(_('تاريخ البداية'))
    end_date = models.DateField(_('تاريخ النهاية'), null=True, blank=True)

    # الحالة والاعتماد
    is_active = models.BooleanField(_('Active'), default=True)
    is_approved = models.BooleanField(_('معتمد'), default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_provisions', verbose_name=_('اعتمد بواسطة'))
    approved_at = models.DateTimeField(_('تاريخ الاعتماد'), null=True, blank=True)

    # معلومات التتبع
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Created By'))

    class Meta:
        verbose_name = _('مخصص')
        verbose_name_plural = _('المخصصات')
        ordering = ['-fiscal_year', '-created_at']
        unique_together = ['provision_type', 'related_account', 'fiscal_year']

    def __str__(self):
        return f"{self.get_provision_type_display()} - {self.name} - {self.fiscal_year}"

    def save(self, *args, **kwargs):
        # تحديث المبلغ المتراكم
        if not self.pk:  # جديد
            self.accumulated_amount = self.amount
        else:  # تعديل
            # يمكن إضافة منطق لتحديث المبلغ المتراكم
            pass
        super().save(*args, **kwargs)


class ProvisionEntry(models.Model):
    """قيود المخصصات"""
    provision = models.ForeignKey(Provision, on_delete=models.CASCADE, verbose_name=_('المخصص'))
    date = models.DateField(_('Date'))
    amount = models.DecimalField(_('المبلغ'), max_digits=15, decimal_places=3)
    description = models.TextField(_('Description'), blank=True)

    # الربط بالقيد المحاسبي
    journal_entry = models.ForeignKey('journal.JournalEntry', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('القيد المحاسبي'))

    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Created By'))

    class Meta:
        verbose_name = _('قيد مخصص')
        verbose_name_plural = _('قيود المخصصات')
        ordering = ['-date']

    def __str__(self):
        return f"{self.provision.name} - {self.date} - {self.amount}"
