from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Product, Category
from inventory.models import Warehouse


class ProductForm(forms.ModelForm):
    """Product add/edit form"""
    
    class Meta:
        model = Product
        fields = [
            'code', 'name', 'name_en', 'product_type', 'barcode', 'serial_number', 
            'category', 'description', 'image', 'cost_price', 
            'minimum_quantity', 'maximum_quantity', 'sale_price', 'wholesale_price', 
            'tax_rate', 'opening_balance_quantity', 'opening_balance_cost', 'opening_balance_warehouse', 'enable_alerts', 'is_active'
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Product Code')}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Product Name')}),
            'name_en': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('English Name')}),
            'product_type': forms.Select(attrs={'class': 'form-control'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Barcode')}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Serial Number')}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Product Description')}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0'}),
            'minimum_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0'}),
            'maximum_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0'}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0'}),
            'wholesale_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0'}),
            'tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'opening_balance_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0'}),
            'opening_balance_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0'}),
            'opening_balance_warehouse': forms.Select(attrs={'class': 'form-control'}),
            'enable_alerts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(is_active=True)
        self.fields['opening_balance_warehouse'].queryset = Warehouse.objects.filter(is_active=True).exclude(code='MAIN')


class CategoryForm(forms.ModelForm):
    """Product category add/edit form"""
    
    class Meta:
        model = Category
        fields = ['name', 'parent', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Category Name')}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Category Description')}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].queryset = Category.objects.filter(is_active=True)
        self.fields['parent'].required = False
