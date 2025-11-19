"""
صلاحيات المخزون
"""
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied


class CanViewInventoryMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية عرض المخزون"""
    permission_required = 'inventory.can_view_inventory'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("ليس لديك صلاحية لعرض المخزون")


class CanAddInventoryMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية إضافة بيانات المخزون"""
    permission_required = 'inventory.can_add_inventory'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("ليس لديك صلاحية لإضافة بيانات المخزون")


class CanEditInventoryMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية تعديل بيانات المخزون"""
    permission_required = 'inventory.can_edit_inventory'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("ليس لديك صلاحية لتعديل بيانات المخزون")


class CanDeleteInventoryMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية حذف بيانات المخزون"""
    permission_required = 'inventory.can_delete_inventory'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("ليس لديك صلاحية لحذف بيانات المخزون")
