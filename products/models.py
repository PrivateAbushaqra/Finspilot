from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Max


class Category(models.Model):
    """Product Category"""
    sequence_number = models.IntegerField(_('Sequence Number'), unique=True, null=True, blank=True)
    name = models.CharField(_('Category Name'), max_length=100, unique=True)
    name_en = models.CharField(_('Name in English'), max_length=100, blank=True)
    code = models.CharField(_('Classification code'), max_length=20, blank=True, unique=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                              verbose_name=_('Parent Category'), related_name='subcategories')
    description = models.TextField(_('Description'), blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        ordering = ['sequence_number']
        default_permissions = []  # No default permissions
        permissions = [
            ('can_view_products', _('Can View Products')),
            ('can_add_products', _('Can Add Products')),
            ('can_edit_products', _('Can Edit Products')),
            ('can_delete_products', _('Can Delete Products')),
            ('can_view_product_categories', _('Can View Product Categories')),
            ('can_add_product_categories', _('Can Add Product Categories')),
            ('can_edit_product_categories', _('Can Edit Product Categories')),
            ('can_delete_product_categories', _('Can Delete Product Categories')),
        ]

    def save(self, *args, **kwargs):
        if not self.sequence_number:
            self.sequence_number = self._get_next_sequence_number()
        super().save(*args, **kwargs)

    def _get_next_sequence_number(self):
        """Get the first available sequence number starting from 10000"""
        existing_numbers = set(Category.objects.values_list('sequence_number', flat=True))
        
        # Start from 10000
        for num in range(10000, 99999):
            if num not in existing_numbers:
                return num
        
        # In a very rare case if all numbers are filled
        max_num = Category.objects.aggregate(Max('sequence_number'))['sequence_number__max']
        return (max_num or 9999) + 1

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} -> {self.name}"
        return self.name

    @property
    def full_path(self):
        """Full path of the category"""
        if self.parent:
            return f"{self.parent.full_path} -> {self.name}"
        return self.name

    @property
    def total_available_quantity(self):
        """Total available quantity for all products in the category"""
        from django.db.models import Sum
        from inventory.models import InventoryMovement
        
        # Calculate incoming quantity minus outgoing quantity for products in this category
        products = self.product_set.filter(is_active=True)
        
        total_quantity = 0
        for product in products:
            # Use the same logic as current_stock
            incoming = InventoryMovement.objects.filter(
                product=product,
                movement_type='in'
            ).exclude(reference_type='opening_balance').aggregate(total=Sum('quantity'))['total'] or 0
            
            outgoing = InventoryMovement.objects.filter(
                product=product,
                movement_type='out'
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            # Add opening balance
            product_stock = (incoming - outgoing) + product.opening_balance_quantity
            total_quantity += product_stock
        
        return total_quantity

    @property
    def total_available_cost(self):
        """Total cost of available quantity for all products in the category"""
        from django.db.models import Sum
        from inventory.models import InventoryMovement
        
        products = self.product_set.filter(is_active=True)
        
        total_cost = 0
        for product in products:
            # Calculate available quantity
            incoming = InventoryMovement.objects.filter(
                product=product,
                movement_type='in'
            ).exclude(reference_type='opening_balance').aggregate(total=Sum('quantity'))['total'] or 0
            
            outgoing = InventoryMovement.objects.filter(
                product=product,
                movement_type='out'
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            available_quantity = (incoming - outgoing) + product.opening_balance_quantity
            
            # Calculate cost using weighted average cost
            if available_quantity > 0:
                # Use current product cost or calculate weighted average
                product_cost = product.calculate_weighted_average_cost() if hasattr(product, 'calculate_weighted_average_cost') else product.cost_price
                total_cost += available_quantity * product_cost
        
        return total_cost

    @property
    def products_count(self):
        """Number of products in the category"""
        return self.product_set.filter(is_active=True).count()


class Product(models.Model):
    """Product"""
    PRODUCT_TYPE_CHOICES = [
        ('physical', _('Goods')),
        ('service', _('Service')),
    ]
    
    code = models.CharField(_('Product Code'), max_length=50, unique=True)
    name = models.CharField(_('Product Name'), max_length=200)
    name_en = models.CharField(_('Name in English'), max_length=200, blank=True)
    product_type = models.CharField(_('Product Type'), max_length=20, choices=PRODUCT_TYPE_CHOICES, default='physical')
    barcode = models.CharField(_('Barcode'), max_length=100, blank=True)
    serial_number = models.CharField(_('Serial Number'), max_length=100, blank=True, 
                                   help_text=_('For products sold individually and requiring warranty'))
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name=_('Category'))
    description = models.TextField(_('Description'), blank=True)
    image = models.ImageField(_('Product Image'), upload_to='products/', blank=True, null=True)
    cost_price = models.DecimalField(_('Cost Price'), max_digits=15, decimal_places=3, 
                                   validators=[MinValueValidator(0)], default=0, blank=True)
    minimum_quantity = models.DecimalField(_('Minimum Quantity'), max_digits=10, decimal_places=3, 
                                         validators=[MinValueValidator(0)], default=0)
    maximum_quantity = models.DecimalField(_('Maximum Quantity'), max_digits=10, decimal_places=3, 
                                         validators=[MinValueValidator(0)], default=0, blank=True)
    sale_price = models.DecimalField(_('Sale Price'), max_digits=15, decimal_places=3, 
                                   validators=[MinValueValidator(0)])
    wholesale_price = models.DecimalField(_('Wholesale Price'), max_digits=15, decimal_places=3, 
                                        validators=[MinValueValidator(0)], default=0, blank=True)
    tax_rate = models.DecimalField(_('Tax Rate'), max_digits=5, decimal_places=2, 
                                 validators=[MinValueValidator(0), MaxValueValidator(100)], default=0)
    opening_balance_quantity = models.DecimalField(_('Opening Balance Quantity'), max_digits=10, decimal_places=3, 
                                                 validators=[MinValueValidator(0)], default=0, blank=True)
    opening_balance_cost = models.DecimalField(_('Opening Balance Cost'), max_digits=15, decimal_places=3, 
                                             validators=[MinValueValidator(0)], default=0, blank=True)
    opening_balance_warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.SET_NULL, 
                                                verbose_name=_('Opening Balance Warehouse'), null=True, blank=True)
    enable_alerts = models.BooleanField(_('Enable Alerts'), default=True)
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')
        ordering = ['code', 'name']
        default_permissions = []

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def product_type_display(self):
        """Display product type"""
        return dict(self.PRODUCT_TYPE_CHOICES).get(self.product_type, _('Goods'))

    @property
    def is_service(self):
        """Is the product a service"""
        return self.product_type == 'service'

    @property
    def current_stock(self):
        """Current quantity in stock (sum of all warehouses)"""
        from inventory.models import InventoryMovement
        
        # Calculate incoming quantity (in) minus outgoing quantity (out), excluding opening balance movements to avoid duplication
        incoming = InventoryMovement.objects.filter(
            product=self,
            movement_type='in'
        ).exclude(reference_type='opening_balance').aggregate(total=models.Sum('quantity'))['total'] or 0
        
        outgoing = InventoryMovement.objects.filter(
            product=self,
            movement_type='out'
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
        
        # Add opening balance
        return (incoming - outgoing) + self.opening_balance_quantity

    def get_stock_in_warehouse(self, warehouse):
        """Get current quantity in a specific warehouse"""
        from inventory.models import InventoryMovement
        
        # Calculate incoming quantity (in) minus outgoing quantity (out) in the specified warehouse
        incoming = InventoryMovement.objects.filter(
            product=self,
            warehouse=warehouse,
            movement_type='in'
        ).exclude(reference_type='opening_balance').aggregate(total=models.Sum('quantity'))['total'] or 0
        
        outgoing = InventoryMovement.objects.filter(
            product=self,
            warehouse=warehouse,
            movement_type='out'
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
        
        # Add opening balance if the warehouse is the opening balance warehouse
        opening_balance = self.opening_balance_quantity if self.opening_balance_warehouse == warehouse else 0
        
        return (incoming - outgoing) + opening_balance

    @property
    def is_low_stock(self):
        """Is the product low in stock"""
        return self.enable_alerts and self.current_stock <= self.minimum_quantity

    def get_price_with_tax(self):
        """Price with tax"""
        from decimal import Decimal
        sale_price_decimal = Decimal(str(self.sale_price))
        tax_rate_decimal = Decimal(str(self.tax_rate))
        tax_amount = sale_price_decimal * (tax_rate_decimal / Decimal('100'))
        return sale_price_decimal + tax_amount

    def get_wholesale_price_with_tax(self):
        """Wholesale price with tax"""
        from decimal import Decimal
        if self.wholesale_price > 0:
            wholesale_price_decimal = Decimal(str(self.wholesale_price))
            tax_rate_decimal = Decimal(str(self.tax_rate))
            tax_amount = wholesale_price_decimal * (tax_rate_decimal / Decimal('100'))
            return wholesale_price_decimal + tax_amount
        return Decimal('0')

    def get_last_purchase_price(self):
        """Last purchase price of the product"""
        from purchases.models import PurchaseInvoiceItem
        
        last_item = PurchaseInvoiceItem.objects.filter(
            product=self
        ).order_by('-invoice__date', '-id').first()
        
        if last_item:
            return last_item.unit_price
        return self.cost_price if self.cost_price > 0 else 0

    def calculate_weighted_average_cost(self):
        """Calculate weighted average cost price"""
        from inventory.models import InventoryMovement
        from decimal import Decimal
        
        # Collect all incoming movements (purchases and opening balance)
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
        """Get current opening balance"""
        return self.opening_balance_quantity

    @property
    def has_movements(self):
        """Check if there are movements on the product (excluding opening balance)"""
        from inventory.models import InventoryMovement
        return InventoryMovement.objects.filter(
            product=self
        ).exclude(reference_type='opening_balance').exists()
