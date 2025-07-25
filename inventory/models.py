from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()


class Warehouse(models.Model):
    """المستودع"""
    name = models.CharField(_('اسم المستودع'), max_length=100)
    code = models.CharField(_('رمز المستودع'), max_length=20, unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                              verbose_name=_('المستودع الأساسي'), related_name='sub_warehouses')
    address = models.TextField(_('العنوان'), blank=True)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                               verbose_name=_('مدير المستودع'))
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('مستودع')
        verbose_name_plural = _('المستودعات')
        ordering = ['name']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} -> {self.name}"
        return self.name


class InventoryMovement(models.Model):
    """حركة المخزون"""
    MOVEMENT_TYPES = [
        ('in', _('وارد')),
        ('out', _('صادر')),
        ('transfer', _('تحويل')),
        ('adjustment', _('تسوية')),
    ]

    REFERENCE_TYPES = [
        ('sales_invoice', _('فاتورة مبيعات')),
        ('sales_return', _('مردود مبيعات')),
        ('purchase_invoice', _('فاتورة مشتريات')),
        ('purchase_return', _('مردود مشتريات')),
        ('warehouse_transfer', _('تحويل مستودع')),
        ('adjustment', _('تسوية')),
    ]

    movement_number = models.CharField(_('رقم الحركة'), max_length=50, unique=True)
    date = models.DateField(_('التاريخ'))
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, verbose_name=_('المنتج'))
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, verbose_name=_('المستودع'))
    movement_type = models.CharField(_('نوع الحركة'), max_length=20, choices=MOVEMENT_TYPES)
    reference_type = models.CharField(_('نوع المرجع'), max_length=30, choices=REFERENCE_TYPES)
    reference_id = models.PositiveIntegerField(_('معرف المرجع'))
    quantity = models.DecimalField(_('الكمية'), max_digits=10, decimal_places=3)
    unit_cost = models.DecimalField(_('تكلفة الوحدة'), max_digits=15, decimal_places=3, default=0)
    total_cost = models.DecimalField(_('التكلفة الإجمالية'), max_digits=15, decimal_places=3, default=0)
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('أنشئ بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)

    class Meta:
        verbose_name = _('حركة مخزون')
        verbose_name_plural = _('حركات المخزون')
        ordering = ['-date', '-movement_number']

    def __str__(self):
        return f"{self.movement_number} - {self.product.name}"

    def save(self, *args, **kwargs):
        self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)


class WarehouseTransfer(models.Model):
    """تحويل المستودعات"""
    transfer_number = models.CharField(_('رقم التحويل'), max_length=50, unique=True)
    date = models.DateField(_('التاريخ'))
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, 
                                     verbose_name=_('من المستودع'), related_name='transfers_from')
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, 
                                   verbose_name=_('إلى المستودع'), related_name='transfers_to')
    notes = models.TextField(_('ملاحظات'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('أنشئ بواسطة'))
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('تحويل مستودع')
        verbose_name_plural = _('تحويلات المستودعات')
        ordering = ['-date', '-transfer_number']

    def __str__(self):
        return f"{self.transfer_number} - {self.from_warehouse.name} -> {self.to_warehouse.name}"


class WarehouseTransferItem(models.Model):
    """عنصر تحويل المستودع"""
    transfer = models.ForeignKey(WarehouseTransfer, on_delete=models.CASCADE, 
                               verbose_name=_('التحويل'), related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, verbose_name=_('المنتج'))
    quantity = models.DecimalField(_('الكمية'), max_digits=10, decimal_places=3)
    unit_cost = models.DecimalField(_('تكلفة الوحدة'), max_digits=15, decimal_places=3, default=0)
    total_cost = models.DecimalField(_('التكلفة الإجمالية'), max_digits=15, decimal_places=3, default=0)

    class Meta:
        verbose_name = _('عنصر تحويل المستودع')
        verbose_name_plural = _('عناصر تحويل المستودعات')

    def __str__(self):
        return f"{self.transfer.transfer_number} - {self.product.name}"

    def save(self, *args, **kwargs):
        self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)
