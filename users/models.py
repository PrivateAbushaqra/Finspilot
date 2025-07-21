from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """مستخدم مخصص"""
    USER_TYPES = [
        ('superadmin', _('مدير عام')),
        ('admin', _('مدير')),
        ('user', _('مستخدم')),
    ]

    user_type = models.CharField(_('نوع المستخدم'), max_length=20, choices=USER_TYPES, default='user')
    phone = models.CharField(_('الهاتف'), max_length=20, blank=True)
    department = models.CharField(_('القسم'), max_length=100, blank=True)
    can_access_sales = models.BooleanField(_('الوصول للمبيعات'), default=False)
    can_access_purchases = models.BooleanField(_('الوصول للمشتريات'), default=False)
    can_access_inventory = models.BooleanField(_('الوصول للمخزون'), default=False)
    can_access_banks = models.BooleanField(_('الوصول للبنوك'), default=False)
    can_access_cashboxes = models.BooleanField(_('الوصول للصناديق النقدية'), default=False)
    can_access_receipts = models.BooleanField(_('الوصول لسندات القبض'), default=False)
    can_access_reports = models.BooleanField(_('الوصول للتقارير'), default=False)
    can_delete_invoices = models.BooleanField(_('حذف الفواتير'), default=False)
    can_edit_dates = models.BooleanField(_('تعديل التواريخ'), default=False)
    can_edit_invoice_numbers = models.BooleanField(_('تعديل أرقام الفواتير'), default=False)
    cash_only = models.BooleanField(_('كاش فقط'), default=False)
    credit_only = models.BooleanField(_('ذمم فقط'), default=False)
    can_see_low_stock_alerts = models.BooleanField(_('تنبيهات انخفاض المخزون'), default=False)
    can_access_pos = models.BooleanField(_('الوصول لنقطة البيع'), default=False)
    pos_only = models.BooleanField(_('نقطة البيع فقط'), default=False)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('مستخدم')
        verbose_name_plural = _('المستخدمون')

    def __str__(self):
        return f"{self.get_full_name()} ({self.username})"

    @property
    def is_superadmin(self):
        return self.user_type == 'superadmin' or self.is_superuser

    @property
    def is_admin(self):
        return self.user_type in ['superadmin', 'admin'] or self.is_superuser

    def has_sales_permission(self):
        return self.is_admin or self.can_access_sales

    def has_purchases_permission(self):
        return self.is_admin or self.can_access_purchases

    def has_inventory_permission(self):
        return self.is_admin or self.can_access_inventory

    def has_banks_permission(self):
        return self.is_admin or self.can_access_banks

    def has_cashboxes_permission(self):
        return self.is_admin or self.can_access_cashboxes

    def has_receipts_permission(self):
        return self.is_admin or self.can_access_receipts

    def has_reports_permission(self):
        return self.is_admin or self.can_access_reports

    def can_delete_invoice(self):
        return self.is_admin or self.can_delete_invoices

    def can_edit_invoice_date(self):
        return self.is_admin or self.can_edit_dates

    def can_edit_invoice_number(self):
        return self.is_admin or self.can_edit_invoice_numbers

    def has_pos_permission(self):
        return self.is_admin or self.can_access_pos

    def is_pos_only_user(self):
        return self.pos_only


class UserGroup(models.Model):
    """مجموعة المستخدمين"""
    name = models.CharField(_('اسم المجموعة'), max_length=100, unique=True)
    description = models.TextField(_('الوصف'), blank=True)
    permissions = models.JSONField(_('الصلاحيات'), default=dict)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('مجموعة المستخدمين')
        verbose_name_plural = _('مجموعات المستخدمين')

    def __str__(self):
        return self.name


class UserGroupMembership(models.Model):
    """عضوية المستخدم في المجموعة"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('المستخدم'))
    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE, verbose_name=_('المجموعة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('عضوية المجموعة')
        verbose_name_plural = _('عضويات المجموعات')
        unique_together = ('user', 'group')

    def __str__(self):
        return f"{self.user.username} - {self.group.name}"
