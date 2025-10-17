from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()


class Warehouse(models.Model):
    """المستودع"""
    name = models.CharField(_('Warehouse Name'), max_length=100)
    code = models.CharField(_('Warehouse Code'), max_length=20, unique=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                              verbose_name=_('Parent Warehouse'), related_name='sub_warehouses')
    address = models.TextField(_('Address'), blank=True)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                               verbose_name=_('Warehouse Manager'))
    is_active = models.BooleanField(_('Active'), default=True)
    is_default = models.BooleanField(_('Default Warehouse'), default=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Warehouse')
        verbose_name_plural = _('Warehouses')
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
        ('in', _('In')),
        ('out', _('Out')),
        ('transfer', _('Transfer')),
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
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, verbose_name=_('Product'))
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, verbose_name=_('Warehouse'))
    movement_type = models.CharField(_('Transaction Type'), max_length=20, choices=MOVEMENT_TYPES)
    reference_type = models.CharField(_('Reference Type'), max_length=30, choices=REFERENCE_TYPES)
    reference_id = models.PositiveIntegerField(_('Reference ID'))
    quantity = models.DecimalField(_('Quantity'), max_digits=10, decimal_places=3)
    unit_cost = models.DecimalField(_('Unit Cost'), max_digits=15, decimal_places=3, default=0)
    total_cost = models.DecimalField(_('Total Cost'), max_digits=15, decimal_places=3, default=0)
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Inventory Movement')
        verbose_name_plural = _('Inventory Movements')
        ordering = ['-date', '-movement_number']
        permissions = [
            ('can_view_inventory', _('Can access inventory')),
        ]

    def __str__(self):
        return f"{self.movement_number} - {self.product.name}"

    def save(self, *args, **kwargs):
        # حساب التكلفة الإجمالية تلقائياً
        if self.quantity and self.unit_cost:
            self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)

    @property
    def document_number(self):
        """الحصول على رقم المستند المرجعي"""
        try:
            if self.reference_type == 'sales_invoice':
                from sales.models import SalesInvoice
                doc = SalesInvoice.objects.get(id=self.reference_id)
                return doc.invoice_number
            elif self.reference_type == 'sales_return':
                from sales.models import SalesReturn
                doc = SalesReturn.objects.get(id=self.reference_id)
                return doc.return_number
            elif self.reference_type == 'purchase_invoice':
                from purchases.models import PurchaseInvoice
                doc = PurchaseInvoice.objects.get(id=self.reference_id)
                return doc.invoice_number
            elif self.reference_type == 'purchase_return':
                from purchases.models import PurchaseReturn
                doc = PurchaseReturn.objects.get(id=self.reference_id)
                return doc.return_number
            elif self.reference_type == 'warehouse_transfer':
                doc = WarehouseTransfer.objects.get(id=self.reference_id)
                return doc.transfer_number
            elif self.reference_type == 'adjustment':
                return self.movement_number  # للتسويات، استخدم رقم الحركة
            elif self.reference_type == 'opening_balance':
                return _('Opening Balance')
            else:
                return _('Not Available')
        except Exception:
            return _('Not Found')

    @property
    def document_url(self):
        """الحصول على رابط صفحة تفاصيل المستند"""
        try:
            if self.reference_type == 'sales_invoice':
                return f'/ar/sales/invoices/{self.reference_id}/'
            elif self.reference_type == 'sales_return':
                return None  # لا يوجد صفحة تفاصيل للإرجاعات في المبيعات
            elif self.reference_type == 'purchase_invoice':
                return f'/ar/purchases/invoices/{self.reference_id}/'
            elif self.reference_type == 'purchase_return':
                return f'/ar/purchases/returns/{self.reference_id}/'
            elif self.reference_type == 'warehouse_transfer':
                return None  # لا يوجد صفحة تفاصيل للتحويلات
            elif self.reference_type == 'adjustment':
                return None  # لا رابط للتسويات
            elif self.reference_type == 'opening_balance':
                return None  # لا رابط للرصيد الافتتاحي
            else:
                return None
        except Exception:
            return None

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
                                     verbose_name=_('From Warehouse'), related_name='transfers_from')
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, 
                                   verbose_name=_('To Warehouse'), related_name='transfers_to')
    notes = models.TextField(_('Notes'), blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Warehouse Transfer')
        verbose_name_plural = _('Warehouse Transfers')
        ordering = ['-date', '-transfer_number']

    def __str__(self):
        return f"{self.transfer_number} - {self.from_warehouse.name} -> {self.to_warehouse.name}"


class WarehouseTransferItem(models.Model):
    """عنصر تحويل المستودع"""
    transfer = models.ForeignKey(WarehouseTransfer, on_delete=models.CASCADE, 
                               verbose_name=_('Transfer'), related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT, verbose_name=_('Product'))
    quantity = models.DecimalField(_('Quantity'), max_digits=10, decimal_places=3)
    unit_cost = models.DecimalField(_('Unit Cost'), max_digits=15, decimal_places=3, default=0)
    total_cost = models.DecimalField(_('Total Cost'), max_digits=15, decimal_places=3, default=0)

    class Meta:
        verbose_name = _('Warehouse Transfer Item')
        verbose_name_plural = _('Warehouse Transfer Items')

    def __str__(self):
        return f"{self.transfer.transfer_number} - {self.product.name}"

    def save(self, *args, **kwargs):
        # جميع المنتجات مادية الآن
        self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)
