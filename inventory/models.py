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
    is_active = models.BooleanField(_('Active'), default=True)
    is_default = models.BooleanField(_('المستودع الافتراضي'), default=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('مستودع')
        verbose_name_plural = _('المستودعات')
        ordering = ['name']
        permissions = [
            ('can_view_inventory', _('Can access inventory')),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} -> {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        # التأكد من وجود مستودع افتراضي واحد فقط
        if self.is_default:
            Warehouse.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        
        # إذا كان أول مستودع يتم إنشاؤه، جعله افتراضي
        if not Warehouse.objects.exists() and not self.is_default:
            self.is_default = True
            
        super().save(*args, **kwargs)

    @classmethod
    def get_default_warehouse(cls):
        """الحصول على المستودع الافتراضي"""
        return cls.objects.filter(is_default=True, is_active=True).first()


class InventoryMovement(models.Model):
    """حركة المخزون"""
    MOVEMENT_TYPES = [
        ('in', _('وارد')),
        ('out', _('صادر')),
        ('transfer', _('تحويل')),
        ('adjustment', _('settlement')),
    ]

    REFERENCE_TYPES = [
        ('sales_invoice', _('Sales Invoice')),
        ('sales_return', _('Sales Return')),
        ('purchase_invoice', _('Purchase Invoice')),
        ('purchase_return', _('Purchase Return')),
        ('warehouse_transfer', _('Warehouse Transfer')),
        ('adjustment', _('Adjustment')),
        ('opening_balance', _('Opening Balance')),
    ]

    movement_number = models.CharField(_('Movement Number'), max_length=50, unique=True)
    date = models.DateField(_('Date'))
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, verbose_name=_('المنتج'))
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, verbose_name=_('المستودع'))
    movement_type = models.CharField(_('Transaction Type'), max_length=20, choices=MOVEMENT_TYPES)
    reference_type = models.CharField(_('نوع المرجع'), max_length=30, choices=REFERENCE_TYPES)
    reference_id = models.PositiveIntegerField(_('معرف المرجع'))
    quantity = models.DecimalField(_('الكمية'), max_digits=10, decimal_places=3)
    unit_cost = models.DecimalField(_('تكلفة الوحدة'), max_digits=15, decimal_places=3, default=0)
    total_cost = models.DecimalField(_('التكلفة الإجمالية'), max_digits=15, decimal_places=3, default=0)
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('حركة مخزون')
        verbose_name_plural = _('حركات المخزون')
        ordering = ['-date', '-movement_number']
        permissions = [
            ('can_view_inventory', _('Can access inventory')),
        ]

    def __str__(self):
        return f"{self.movement_number} - {self.product.name}"

    def save(self, *args, **kwargs):
        # إنشاء رقم الحركة تلقائياً إذا لم يكن موجوداً
        if not self.movement_number:
            from django.utils import timezone
            current_date = timezone.now().strftime('%Y%m%d')
            last_movement = InventoryMovement.objects.filter(
                movement_number__startswith=f'MOV-{current_date}'
            ).order_by('-movement_number').first()
            
            if last_movement:
                last_number = int(last_movement.movement_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
                
            self.movement_number = f'MOV-{current_date}-{new_number:04d}'
        
        # حساب التكلفة الإجمالية تلقائياً
        self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)


class WarehouseTransfer(models.Model):
    """تحويل المستودعات"""
    transfer_number = models.CharField(_('Transfer Number'), max_length=50, unique=True)
    date = models.DateField(_('Date'))
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, 
                                     verbose_name=_('من المستودع'), related_name='transfers_from')
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, 
                                   verbose_name=_('إلى المستودع'), related_name='transfers_to')
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

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
        # جميع المنتجات مادية الآن
        self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)
