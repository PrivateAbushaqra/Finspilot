# -*- coding: utf-8 -*-
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    def has_revenueexpenseentry_view_permission(self):
        """
        تعيد True إذا كان لدى المستخدم صلاحية عرض قيد إيراد/مصروف
        سواء من دجانغو أو من الclass UserGroup(models.Model):
    
    name = models.CharField(_('Group Name'), max_length=100, unique=True)
    description = models.TextField(_('Description'), blank=True)
    permissions = models.JSONField(_('Permissions'), default=dict)
    dashboard_sections = models.JSONField(_('Dashboard Sections'), default=list, help_text=_('List of dashboard sections to display for this group'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True) المخصصة
        """
        if self.is_admin:
            return True
        # تحقق من صلاحية دجانغو الافتراضية
        if self.has_perm('revenues_expenses.view_revenueexpenseentry'):
            return True
        # تحقق من صلاحيات المجموعات المخصصة
        try:
            from users.models import UserGroupMembership
            group_ids = UserGroupMembership.objects.filter(user=self).values_list('group_id', flat=True)
            from users.models import UserGroup
            for group in UserGroup.objects.filter(id__in=group_ids):
                group_perms = group.permissions or {}
                for perms_list in group_perms.values():
                    if 'view_revenueexpenseentry' in perms_list:
                        return True
        except Exception:
            pass
        return False
    def has_revenueexpensecategory_view_permission(self):
        """
        تعيد True إذا كان لدى المستخدم صلاحية عرض فئة إيراد/مصروف
        سواء من دجانغو أو من المجموعات المخصصة
        """
        if self.is_admin:
            return True
        # تحقق من صلاحية دجانغو الافتراضية
        if self.has_perm('revenues_expenses.view_revenueexpensecategory'):
            return True
        # تحقق من صلاحيات المجموعات المخصصة
        try:
            from users.models import UserGroupMembership
            group_ids = UserGroupMembership.objects.filter(user=self).values_list('group_id', flat=True)
            from users.models import UserGroup
            for group in UserGroup.objects.filter(id__in=group_ids):
                group_perms = group.permissions or {}
                for perms_list in group_perms.values():
                    if 'view_revenueexpensecategory' in perms_list:
                        return True
        except Exception:
            pass
        return False
    def has_revenueexpensecategory_add_permission(self):
        """
        تعيد True إذا كان لدى المستخدم صلاحية إضافة فئة إيراد/مصروف
        سواء من دجانغو أو من المجموعات المخصصة
        """
        if self.is_admin:
            return True
        # تحقق من صلاحية دجانغو الافتراضية
        if self.has_perm('revenues_expenses.add_revenueexpensecategory'):
            return True
        # تحقق من صلاحيات المجموعات المخصصة
        try:
            from users.models import UserGroupMembership
            group_ids = UserGroupMembership.objects.filter(user=self).values_list('group_id', flat=True)
            from users.models import UserGroup
            for group in UserGroup.objects.filter(id__in=group_ids):
                group_perms = group.permissions or {}
                for perms_list in group_perms.values():
                    if 'add_revenueexpensecategory' in perms_list:
                        return True
        except Exception:
            pass
        return False
    def has_revenueexpenseentry_add_permission(self):
        """
        تعيد True إذا كان لدى المستخدم صلاحية إضافة قيد إيراد/مصروف
        سواء من دجانغو أو من المجموعات المخصصة
        """
        if self.is_admin:
            return True
        # تحقق من صلاحية دجانغو الافتراضية
        if self.has_perm('revenues_expenses.add_revenueexpenseentry'):
            return True
        # تحقق من صلاحيات المجموعات المخصصة
        try:
            from users.models import UserGroupMembership
            group_ids = UserGroupMembership.objects.filter(user=self).values_list('group_id', flat=True)
            from users.models import UserGroup
            for group in UserGroup.objects.filter(id__in=group_ids):
                group_perms = group.permissions or {}
                for perms_list in group_perms.values():
                    if 'add_revenueexpenseentry' in perms_list:
                        return True
        except Exception:
            pass
        return False
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
            ('can_access_inventory', _('Can access inventory')),
            ('can_access_products', _('Can access products')),
            ('can_access_banks', _('Can access banks')),
            #('can_access_cashboxes', _('Can access cashboxes')),
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
        """
        تعيد True إذا كان لدى المستخدم صلاحية الوصول إلى المبيعات
        سواء كانت الصلاحية مباشرة أو من خلال المجموعات الافتراضية أو المجموعات المخصصة (UserGroup).
        """
        if self.is_admin:
            return True
        # تحقق من صلاحيات sales المفصلة
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        try:
            cts = ContentType.objects.filter(app_label='sales')
            sales_perms = set()
            for ct in cts:
                sales_perms.update(f'sales.{codename}' for codename in Permission.objects.filter(content_type=ct).values_list('codename', flat=True))
        except Exception:
            sales_perms = set()
        user_perms = set(self.get_all_permissions())
        if user_perms.intersection(sales_perms):
            return True
        # تحقق من صلاحيات المجموعات المخصصة
        try:
            from users.models import UserGroupMembership
            group_ids = UserGroupMembership.objects.filter(user=self).values_list('group_id', flat=True)
            from users.models import UserGroup
            for group in UserGroup.objects.filter(id__in=group_ids):
                group_perms = group.permissions or {}
                for perms_list in group_perms.values():
                    if 'view_sales' in perms_list or 'add_salesinvoice' in perms_list or 'change_salesinvoice' in perms_list or 'delete_salesinvoice' in perms_list or 'view_salesreturn' in perms_list or 'add_salesreturn' in perms_list or 'change_salesreturn' in perms_list or 'delete_salesreturn' in perms_list or 'view_salescreditnote' in perms_list or 'add_salescreditnote' in perms_list or 'change_salescreditnote' in perms_list or 'delete_salescreditnote' in perms_list:
                        return True
        except Exception:
            pass
        return False

    def has_purchases_permission(self):
        return (
            self.is_admin
            or self.has_perm('purchases.can_view_purchases')
            or self.has_perm('purchases.can_view_debitnote')
            or self.has_perm('purchases.can_view_purchasereturn')
            or self.has_perm('purchases.add_purchaseinvoice')
            or self.has_perm('purchases.add_purchasereturn')
            or self.has_perm('purchases.view_purchaseinvoice')
            or self.has_perm('purchases.can_view_purchase_statement')
        )

    def has_inventory_permission(self):
        """
        تعيد True إذا كان لدى المستخدم صلاحية الوصول إلى المخزون
        سواء كانت الصلاحية مباشرة أو من خلال المجموعات الافتراضية أو المجموعات المخصصة (UserGroup).
        """
        if self.is_admin:
            return True
        if self.has_perm('users.can_access_inventory'):
            return True
        # تحقق من صلاحيات inventory المفصلة
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        try:
            cts = ContentType.objects.filter(app_label='inventory')
            inventory_perms = set()
            for ct in cts:
                inventory_perms.update(f'inventory.{codename}' for codename in Permission.objects.filter(content_type=ct).values_list('codename', flat=True))
        except Exception:
            inventory_perms = set()
        user_perms = set(self.get_all_permissions())
        if user_perms.intersection(inventory_perms):
            return True
        # تحقق من صلاحيات المجموعات المخصصة
        try:
            from users.models import UserGroupMembership
            group_ids = UserGroupMembership.objects.filter(user=self).values_list('group_id', flat=True)
            from users.models import UserGroup
            for group in UserGroup.objects.filter(id__in=group_ids):
                group_perms = group.permissions or {}
                for perms_list in group_perms.values():
                    if 'view_inventory' in perms_list or 'add_warehouse' in perms_list or 'change_warehouse' in perms_list or 'delete_warehouse' in perms_list or 'view_inventorymovement' in perms_list or 'add_inventorymovement' in perms_list or 'change_inventorymovement' in perms_list or 'delete_inventorymovement' in perms_list:
                        return True
        except Exception:
            pass
        return False

    def has_products_permission(self):
        return (
            self.is_admin
            or self.has_perm('users.can_access_products')
            or self.has_perm('products.can_view_products')
            or self.has_perm('products.can_edit_products')
        )

    def has_banks_permission(self):
        return (
            self.is_admin
            or self.has_perm('users.can_access_banks')
            or self.has_perm('banks.can_view_banks_account')
        )

    def has_cashboxes_permission(self):
        return (
            self.is_admin 
            or self.has_perm('users.can_access_cashboxes')
            or self.has_perm('cashboxes.can_add_cashboxes')
            or self.has_perm('cashboxes.can_edit_cashboxes')
            or self.has_perm('cashboxes.can_delete_cashboxes')
        )

    def has_receipts_permission(self):
        return self.is_superadmin or self.user_type == 'admin' or self.has_perm('receipts.can_access_receipts')

    def has_reports_permission(self):
        """
        تعيد True إذا كان لدى المستخدم صلاحية الوصول إلى التقارير
        سواء كانت الصلاحية مباشرة أو من خلال المجموعات الافتراضية أو المجموعات المخصصة (UserGroup).
        """
        if self.is_admin:
            return True
        # تحقق من صلاحيات reports المفصلة
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        try:
            cts = ContentType.objects.filter(app_label='reports')
            reports_perms = set()
            for ct in cts:
                reports_perms.update(f'reports.{codename}' for codename in Permission.objects.filter(content_type=ct).values_list('codename', flat=True))
        except Exception:
            reports_perms = set()
        user_perms = set(self.get_all_permissions())
        if user_perms.intersection(reports_perms):
            return True
        # تحقق من صلاحيات المجموعات المخصصة
        try:
            from users.models import UserGroupMembership
            group_ids = UserGroupMembership.objects.filter(user=self).values_list('group_id', flat=True)
            from users.models import UserGroup
            for group in UserGroup.objects.filter(id__in=group_ids):
                group_perms = group.permissions or {}
                for perms_list in group_perms.values():
                    if 'view_reports' in perms_list or 'add_reportaccesscontrol' in perms_list or 'change_reportaccesscontrol' in perms_list or 'delete_reportaccesscontrol' in perms_list:
                        return True
        except Exception:
            pass
        return False

    def has_settings_permission(self):
        """
        تعيد True إذا كان لدى المستخدم صلاحية الوصول إلى الإعدادات
        سواء كانت الصلاحية مباشرة أو من خلال المجموعات الافتراضية أو المجموعات المخصصة (UserGroup).
        """
        if self.is_admin:
            return True
        # تحقق من صلاحيات settings المفصلة
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        try:
            cts = ContentType.objects.filter(app_label='settings')
            settings_perms = set()
            for ct in cts:
                settings_perms.update(f'settings.{codename}' for codename in Permission.objects.filter(content_type=ct).values_list('codename', flat=True))
        except Exception:
            settings_perms = set()
        user_perms = set(self.get_all_permissions())
        if user_perms.intersection(settings_perms):
            return True
        # تحقق من صلاحيات المجموعات المخصصة
        try:
            from users.models import UserGroupMembership
            group_ids = UserGroupMembership.objects.filter(user=self).values_list('group_id', flat=True)
            from users.models import UserGroup
            for group in UserGroup.objects.filter(id__in=group_ids):
                group_perms = group.permissions or {}
                for perms_list in group_perms.values():
                    if 'view_settings' in perms_list or 'add_currency' in perms_list or 'change_currency' in perms_list or 'delete_currency' in perms_list or 'add_companysettings' in perms_list or 'change_companysettings' in perms_list or 'delete_companysettings' in perms_list:
                        return True
        except Exception:
            pass
        return False

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
                self.has_perm('users.can_access_company_settings') or
                self.has_settings_permission())

    def has_system_management_permission(self):
        return self.is_admin or self.has_perm('users.can_access_system_management') or self.has_settings_permission()

    def has_revenues_expenses_permission(self):
        """
        تعيد True إذا كان لدى المستخدم أي صلاحية من قسم الإيرادات والمصروفات
        سواء كانت الصلاحية مباشرة أو من خلال المجموعات الافتراضية أو المجموعات المخصصة (UserGroup).
        تقرأ جميع الصلاحيات المخزنة في UserGroup لأي مفتاح.
        """
        if self.is_admin:
            return True
        # صلاحيات دجانغو الافتراضية
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        try:
            ct = ContentType.objects.get(app_label='revenues_expenses')
            perms_django = set(Permission.objects.filter(content_type=ct).values_list('codename', flat=True))
        except Exception:
            perms_django = set()
        user_perms = set(self.get_all_permissions())
        # صلاحيات المجموعات المخصصة
        try:
            from users.models import UserGroupMembership
            group_ids = UserGroupMembership.objects.filter(user=self).values_list('group_id', flat=True)
            from users.models import UserGroup
            custom_perms = set()
            for group in UserGroup.objects.filter(id__in=group_ids):
                group_perms = group.permissions or {}
                # اجمع جميع الصلاحيات لأي مفتاح
                for perms_list in group_perms.values():
                    for perm in perms_list:
                        custom_perms.add(perm)
        except Exception:
            custom_perms = set()
        # تحقق من أي صلاحية تخص الإيرادات والمصروفات
        all_perms = user_perms.union(custom_perms)
        for perm in all_perms:
            if 'revenueexpense' in perm or 'revenues_expenses' in perm:
                return True
        return False
    def has_journal_permission(self):
        """
        تعيد True إذا كان لدى المستخدم أي صلاحية من قسم القيود اليومية (journal)
        سواء كانت الصلاحية مباشرة أو من خلال المجموعات الافتراضية أو المجموعات المخصصة (UserGroup).
        """
        if self.is_admin:
            return True
        # صلاحيات دجانغو الافتراضية
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        try:
            ct = ContentType.objects.get(app_label='journal')
            perms_django = set(Permission.objects.filter(content_type=ct).values_list('codename', flat=True))
        except Exception:
            perms_django = set()
        user_perms = set(self.get_all_permissions())
        # صلاحيات المجموعات المخصصة
        try:
            from users.models import UserGroupMembership
            group_ids = UserGroupMembership.objects.filter(user=self).values_list('group_id', flat=True)
            from users.models import UserGroup
            custom_perms = set()
            for group in UserGroup.objects.filter(id__in=group_ids):
                group_perms = group.permissions or {}
                for perms_list in group_perms.values():
                    for perm in perms_list:
                        custom_perms.add(perm)
        except Exception:
            custom_perms = set()
        all_perms = user_perms.union(custom_perms)
        for perm in all_perms:
            if (
                'journalentry' in perm or 'journal_entry' in perm or
                'account' in perm or 'journalaccount' in perm or
                'journalline' in perm or 'journal_line' in perm or
                'journal' in perm
            ):
                return True
        return False
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


# إضافة حقل dashboard_sections إلى Group
from django.contrib.auth.models import Group
Group.add_to_class('dashboard_sections', models.TextField(default='', blank=True, help_text=_('List of dashboard sections to display for this group')))
