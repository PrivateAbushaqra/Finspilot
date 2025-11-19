"""
صلاحيات المنتجات والفئات
"""
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied


class CanViewProductsMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية عرض المنتجات"""
    permission_required = 'products.can_view_products'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("ليس لديك صلاحية لعرض المنتجات")


class CanAddProductsMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية إضافة المنتجات"""
    permission_required = 'products.can_add_products'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("ليس لديك صلاحية لإضافة المنتجات")


class CanEditProductsMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية تعديل المنتجات"""
    permission_required = 'products.can_edit_products'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("ليس لديك صلاحية لتعديل المنتجات")


class CanDeleteProductsMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية حذف المنتجات"""
    permission_required = 'products.can_delete_products'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("ليس لديك صلاحية لحذف المنتجات")


class CanViewProductCategoriesMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية عرض فئات المنتجات"""
    permission_required = 'products.can_view_product_categories'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("ليس لديك صلاحية لعرض فئات المنتجات")


class CanAddProductCategoriesMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية إضافة فئات المنتجات"""
    permission_required = 'products.can_add_product_categories'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("ليس لديك صلاحية لإضافة فئات المنتجات")


class CanEditProductCategoriesMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية تعديل فئات المنتجات"""
    permission_required = 'products.can_edit_product_categories'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("ليس لديك صلاحية لتعديل فئات المنتجات")


class CanDeleteProductCategoriesMixin(PermissionRequiredMixin):
    """Mixin للتحقق من صلاحية حذف فئات المنتجات"""
    permission_required = 'products.can_delete_product_categories'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("ليس لديك صلاحية لحذف فئات المنتجات")
