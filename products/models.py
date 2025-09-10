from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Max


class Category(models.Model):
    """فئة المنتجات"""
    sequence_number = models.IntegerField(_('الرقم التسلسلي'), unique=True, null=True, blank=True)
    name = models.CharField(_('اسم الفئة'), max_length=100, unique=True)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=100, blank=True)
    code = models.CharField(_('رمز التصنيف'), max_length=20, blank=True, unique=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                              verbose_name=_('الفئة الأساسية'), related_name='subcategories')
    description = models.TextField(_('الوصف'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('فئة')
        verbose_name_plural = _('الفئات')
        ordering = ['sequence_number']
        permissions = [
            ('can_view_products', _('يمكن عرض الفئات والمنتجات')),
            ('can_add_products', _('يمكن إضافة المنتجات')),
            ('can_add_categories', _('يمكن إضافة الفئات')),
            ('can_edit_categories', _('يمكن تعديل الفئات')),
            ('can_delete_categories', _('يمكن حذف الفئات')),
            ('can_delete_products', _('يمكن حذف المنتجات')),
        ]

    def save(self, *args, **kwargs):
        if not self.sequence_number:
            self.sequence_number = self._get_next_sequence_number()
        super().save(*args, **kwargs)

    def _get_next_sequence_number(self):
        """الحصول على أول رقم تسلسلي متاح بدءاً من 10000"""
        existing_numbers = set(Category.objects.values_list('sequence_number', flat=True))
        
        # البداية من 10000
        for num in range(10000, 99999):
            if num not in existing_numbers:
                return num
        
        # في حالة نادرة جداً إذا امتلأت جميع الأرقام
        max_num = Category.objects.aggregate(Max('sequence_number'))['sequence_number__max']
        return (max_num or 9999) + 1

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} -> {self.name}"
        return self.name

    @property
    def full_path(self):
        """المسار الكامل للفئة"""
        if self.parent:
            return f"{self.parent.full_path} -> {self.name}"
        return self.name


class Product(models.Model):
    """المنتج"""
    PRODUCT_TYPE_CHOICES = [
        ('physical', _('سلعة')),
        ('service', _('خدمة')),
    ]
    
    code = models.CharField(_('رقم المنتج'), max_length=50, unique=True)
    name = models.CharField(_('اسم المنتج'), max_length=200)
    name_en = models.CharField(_('الاسم بالإنجليزية'), max_length=200, blank=True)
    product_type = models.CharField(_('نوع المنتج'), max_length=20, choices=PRODUCT_TYPE_CHOICES, default='physical')
    barcode = models.CharField(_('الباركود'), max_length=100, blank=True)
    serial_number = models.CharField(_('الرقم التسلسلي'), max_length=100, blank=True, 
                                   help_text=_('للمنتجات التي تُباع بالقطعة وتحتاج كفالة'))
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name=_('الفئة'))
    description = models.TextField(_('الوصف'), blank=True)
    cost_price = models.DecimalField(_('سعر التكلفة'), max_digits=15, decimal_places=3, 
                                   validators=[MinValueValidator(0)], default=0, blank=True)
    minimum_quantity = models.DecimalField(_('الحد الأدنى للكمية'), max_digits=10, decimal_places=3, 
                                         validators=[MinValueValidator(0)], default=0)
    sale_price = models.DecimalField(_('سعر البيع'), max_digits=15, decimal_places=3, 
                                   validators=[MinValueValidator(0)])
    wholesale_price = models.DecimalField(_('سعر الجملة'), max_digits=15, decimal_places=3, 
                                        validators=[MinValueValidator(0)], default=0, blank=True)
    tax_rate = models.DecimalField(_('نسبة الضريبة'), max_digits=5, decimal_places=2, 
                                 validators=[MinValueValidator(0), MaxValueValidator(100)], default=0)
    enable_alerts = models.BooleanField(_('تفعيل التنبيهات'), default=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(_('تاريخ الإنشاء'), auto_now_add=True)
    updated_at = models.DateTimeField(_('تاريخ التحديث'), auto_now=True)

    class Meta:
        verbose_name = _('منتج')
        verbose_name_plural = _('المنتجات')
        ordering = ['code', 'name']
        permissions = [
            ('can_view_products', _('يمكن عرض الفئات والمنتجات')),
            ('can_add_products', _('يمكن إضافة المنتجات')),
            ('can_add_categories', _('يمكن إضافة الفئات')),
            ('can_edit_categories', _('يمكن تعديل الفئات')),
            ('can_delete_categories', _('يمكن حذف الفئات')),
            ('can_delete_products', _('يمكن حذف المنتجات')),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def product_type_display(self):
        """عرض نوع المنتج"""
        return dict(self.PRODUCT_TYPE_CHOICES).get(self.product_type, _('سلعة'))

    @property
    def is_service(self):
        """هل المنتج خدمة"""
        return self.product_type == 'service'

    @property
    def current_stock(self):
        """الكمية الحالية في المخزون"""
        from inventory.models import InventoryMovement
        
        # حساب الكمية الواردة (in) ناقص الكمية الصادرة (out)
        incoming = InventoryMovement.objects.filter(
            product=self,
            movement_type='in'
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
        
        outgoing = InventoryMovement.objects.filter(
            product=self,
            movement_type='out'
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
        
        return incoming - outgoing

    @property
    def is_low_stock(self):
        """هل المنتج منخفض المخزون"""
        return self.enable_alerts and self.current_stock <= self.minimum_quantity

    def get_price_with_tax(self):
        """السعر مع الضريبة"""
        from decimal import Decimal
        sale_price_decimal = Decimal(str(self.sale_price))
        tax_rate_decimal = Decimal(str(self.tax_rate))
        tax_amount = sale_price_decimal * (tax_rate_decimal / Decimal('100'))
        return sale_price_decimal + tax_amount

    def get_wholesale_price_with_tax(self):
        """سعر الجملة مع الضريبة"""
        from decimal import Decimal
        if self.wholesale_price > 0:
            wholesale_price_decimal = Decimal(str(self.wholesale_price))
            tax_rate_decimal = Decimal(str(self.tax_rate))
            tax_amount = wholesale_price_decimal * (tax_rate_decimal / Decimal('100'))
            return wholesale_price_decimal + tax_amount
        return Decimal('0')

    def get_last_purchase_price(self):
        """آخر سعر شراء للمنتج"""
        from purchases.models import PurchaseInvoiceItem
        
        last_item = PurchaseInvoiceItem.objects.filter(
            product=self
        ).order_by('-invoice__date', '-id').first()
        
        if last_item:
            return last_item.unit_price
        return self.cost_price if self.cost_price > 0 else 0

    def calculate_weighted_average_cost(self):
        """حساب متوسط سعر التكلفة المرجح"""
        from inventory.models import InventoryMovement
        from decimal import Decimal
        
        # جمع جميع حركات الإدخال (المشتريات والرصيد الافتتاحي)
        incoming_movements = InventoryMovement.objects.filter(
            product=self,
            movement_type='in'
        ).exclude(total_cost=0)
        
        if not incoming_movements.exists():
            return self.cost_price if self.cost_price > 0 else Decimal('0')
        
        total_quantity = Decimal('0')
        total_cost = Decimal('0')
        
        for movement in incoming_movements:
            if movement.quantity > 0:
                total_quantity += Decimal(str(movement.quantity))
                total_cost += Decimal(str(movement.total_cost))
        
        if total_quantity > 0:
            return total_cost / total_quantity
        
        return self.cost_price if self.cost_price > 0 else Decimal('0')

    def get_opening_balance(self):
        """الحصول على الرصيد الافتتاحي الحالي"""
        from inventory.models import InventoryMovement
        from decimal import Decimal
        
        # البحث عن حركة الرصيد الافتتاحي
        opening_movement = InventoryMovement.objects.filter(
            product=self,
            movement_type='in',
            reference_type='opening_balance'
        ).first()
        
        if opening_movement:
            return Decimal(str(opening_movement.quantity))
        
        return Decimal('0')
