from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """مستخدم مخصص"""
    USER_TYPES = [
        ('superadmin', _('Super Admin')),
        ('admin', _('Manager')),
        ('user', _('User')),
        ('pos_user', _('POS User')),
    ]

    user_type = models.CharField(_('User Type'), max_length=20, choices=USER_TYPES, default='user')
    phone = models.CharField(_('Phone'), max_length=20, blank=True)
    department = models.CharField(_('Department'), max_length=100, blank=True)
    pos_warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.SET_NULL, 
                                    null=True, blank=True, verbose_name=_('POS Warehouse'),
                                    help_text=_('Dedicated warehouse for POS user to issue invoices from'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        permissions = [
            # إدارة النظام
            ('can_access_system_management', _('Can access system management')),
            ('can_manage_users', _('Manage users')),
            ('can_view_audit_logs', _('View audit logs')),
            ('can_backup_system', _('System backup')),
            
            # صلاحيات الوصول للأقسام
            ('can_access_sales', _('Can access sales')),
            ('can_access_purchases', _('Can access purchases')),
            ('can_access_inventory', _('Can access inventory')),
            ('can_access_banks', _('Can access banks')),
            ('can_access_cashboxes', _('Can access cashboxes')),
            ('can_access_receipts', _('Can access receipts')),
            ('can_access_reports', _('Can access reports')),
            ('can_access_pos', _('Can access POS')),
            ('can_access_company_settings', _('Can access company settings')),
            
            # صلاحيات التحرير والحذف
            ('can_delete_invoices', _('Can delete invoices')),
            ('can_delete_accounts', _('Can delete accounts')),
            ('can_edit_dates', _('Can edit dates')),
            ('can_edit_invoice_numbers', _('Can edit invoice numbers')),
            
            # صلاحيات خاصة
            ('can_see_low_stock_alerts', _('Can see low stock alerts')),
            ('cash_only', _('Cash only')),
            ('credit_only', _('Credit only')),
            ('pos_only', _('POS only')),
        ]

    def __str__(self):
        return f"{self.get_full_name()} ({self.username})"

    @property
    def is_superadmin(self):
        return self.user_type == 'superadmin' or self.is_superuser

    @property
    def is_admin(self):
        return self.user_type in ['superadmin', 'admin', 'manager'] or self.is_superuser

    def has_sales_permission(self):
        return self.is_admin or self.has_perm('users.can_access_sales')

    def has_purchases_permission(self):
        return self.is_admin or self.has_perm('users.can_access_purchases')

    def has_inventory_permission(self):
        return self.is_admin or self.has_perm('users.can_access_inventory')

    def has_banks_permission(self):
        return (
            self.is_admin
            or self.has_perm('users.can_access_banks')
            or self.has_perm('banks.can_view_banks_account')
        )

    def has_cashboxes_permission(self):
        return self.is_admin or self.has_perm('users.can_access_cashboxes')

    def has_receipts_permission(self):
        return self.is_admin or self.has_perm('users.can_access_receipts')

    def has_reports_permission(self):
        return self.is_admin or self.has_perm('users.can_access_reports')

    def can_delete_invoice(self):
        return self.is_admin or self.has_perm('users.can_delete_invoices')

    def can_edit_invoice_date(self):
        return self.is_admin or self.has_perm('users.can_edit_dates')

    def can_edit_invoice_number(self):
        return self.is_admin or self.has_perm('users.can_edit_invoice_numbers')

    def has_pos_permission(self):
        return self.is_admin or self.user_type == 'pos_user' or self.has_perm('users.can_access_pos')

    def is_pos_only_user(self):
        return self.has_perm('users.pos_only_access')

    def has_company_settings_permission(self):
        return (self.user_type in ['superadmin', 'user'] or 
                self.is_superuser or 
                self.has_perm('users.can_access_company_settings'))

    def has_system_management_permission(self):
        return self.is_admin or self.has_perm('users.can_access_system_management')

    def save(self, *args, **kwargs):
        """حفظ المستخدم مع تعيين الصلاحيات حسب النوع"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # إذا كان مستخدم جديد من نوع نقطة البيع، قم بتعيين الصلاحيات المناسبة
        if is_new and self.user_type == 'pos_user':
            self.setup_pos_user_permissions()
    
    def setup_pos_user_permissions(self):
        """تعيين صلاحيات محددة لمستخدم نقطة البيع"""
        # منح صلاحية الوصول لنقطة البيع فقط
        from django.contrib.auth.models import Permission
        
        try:
            # الصلاحيات المطلوبة لمستخدم نقطة البيع
            pos_permissions = [
                'can_access_pos',
                'can_access_sales',
            ]
            
            for perm_codename in pos_permissions:
                try:
                    permission = Permission.objects.get(codename=perm_codename)
                    self.user_permissions.add(permission)
                except Permission.DoesNotExist:
                    pass
                    
        except Exception as e:
            pass  # تجاهل الأخطاء في حالة عدم وجود الصلاحيات


class UserGroup(models.Model):
    """مجموعة المستخدمين"""
    name = models.CharField(_('Group Name'), max_length=100, unique=True)
    description = models.TextField(_('Description'), blank=True)
    permissions = models.JSONField(_('Permissions'), default=dict)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('User Group')
        verbose_name_plural = _('User Groups')

    def __str__(self):
        return self.name


class UserGroupMembership(models.Model):
    """عضوية المستخدم في المجموعة"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('المستخدم'))
    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE, verbose_name=_('المجموعة'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('عضوية المجموعة')
        verbose_name_plural = _('عضويات المجموعات')
        unique_together = ('user', 'group')

    def __str__(self):
        return f"{self.user.username} - {self.group.name}"
