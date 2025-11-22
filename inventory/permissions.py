"""
صلاحيات المخزون
"""
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _


class CanViewInventoryStockMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية عرض المخزون"""
    permission_required = 'inventory.can_view_warehouses'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied(_("You do not have permission to view inventory stock"))


class CanViewWarehousesMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية عرض المستودعات"""
    permission_required = 'inventory.can_view_warehouses'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied(_("You do not have permission to view warehouses"))


class CanAddWarehousesMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية إضافة المستودعات"""
    permission_required = 'inventory.can_add_warehouses'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied(_("You do not have permission to add warehouses"))


class CanEditWarehousesMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية تعديل المستودعات"""
    permission_required = 'inventory.can_edit_warehouses'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied(_("You do not have permission to edit warehouses"))


class CanDeleteWarehousesMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية حذف المستودعات"""
    permission_required = 'inventory.can_delete_warehouses'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied(_("You do not have permission to delete warehouses"))


class CanViewInventoryMovementsMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية عرض حركات المخزون"""
    permission_required = 'inventory.can_view_inventory_movements'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied(_("You do not have permission to view inventory movements"))


class CanAddInventoryMovementsMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية إضافة حركات المخزون"""
    permission_required = 'inventory.can_add_inventory_movements'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied(_("You do not have permission to add inventory movements"))


class CanEditInventoryMovementsMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية تعديل حركات المخزون"""
    permission_required = 'inventory.can_edit_inventory_movements'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied(_("You do not have permission to edit inventory movements"))


class CanDeleteInventoryMovementsMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية حذف حركات المخزون"""
    permission_required = 'inventory.can_delete_inventory_movements'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied(_("You do not have permission to delete inventory movements"))


class CanViewWarehouseTransfersMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية عرض تحويلات المستودعات"""
    permission_required = 'inventory.can_view_warehouse_transfers'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied(_("You do not have permission to view warehouse transfers"))


class CanAddWarehouseTransfersMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية إضافة تحويلات المستودعات"""
    permission_required = 'inventory.can_add_warehouse_transfers'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied(_("You do not have permission to add warehouse transfers"))


class CanEditWarehouseTransfersMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية تعديل تحويلات المستودعات"""
    permission_required = 'inventory.can_edit_warehouse_transfers'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied(_("You do not have permission to edit warehouse transfers"))


class CanDeleteWarehouseTransfersMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية حذف تحويلات المستودعات"""
    permission_required = 'inventory.can_delete_warehouse_transfers'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied(_("You do not have permission to delete warehouse transfers"))


class CanViewStockAlertsMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية عرض تنبيهات المخزون"""
    permission_required = 'inventory.can_view_stock_alerts'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied(_("You do not have permission to view stock alerts"))


# Keep old mixins for backward compatibility
class CanViewInventoryMixin(CanViewInventoryStockMixin):
    """للتوافق مع الصفحات القديمة - استخدم CanViewInventoryStockMixin بدلاً منه"""
    pass


class CanAddInventoryMixin(CanAddWarehousesMixin):
    """للتوافق مع الصفحات القديمة - استخدم الصلاحية المناسبة بدلاً منه"""
    pass


class CanEditInventoryMixin(CanEditWarehousesMixin):
    """للتوافق مع الصفحات القديمة - استخدم الصلاحية المناسبة بدلاً منه"""
    pass


class CanDeleteInventoryMixin(CanDeleteWarehousesMixin):
    """للتوافق مع الصفحات القديمة - استخدم الصلاحية المناسبة بدلاً منه"""
    pass
