from django import forms
from django.utils.translation import gettext_lazy as _
from .models import AssetCategory, Asset, LiabilityCategory, Liability, DepreciationEntry
from settings.models import Currency, CompanySettings
from django.contrib.auth import get_user_model

User = get_user_model()


class AssetCategoryForm(forms.ModelForm):
    class Meta:
        model = AssetCategory
        fields = ['name', 'type', 'description', 'depreciation_rate', 'useful_life_years', 'is_depreciable', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'depreciation_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'useful_life_years': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_depreciable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = ['name', 'category', 'description', 'purchase_cost', 'current_value', 'salvage_value', 
                 'currency', 'purchase_date', 'supplier', 'invoice_number', 'warranty_expiry', 
                 'location', 'responsible_person', 'status', 'depreciation_method']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'purchase_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0'}),
            'current_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0'}),
            'salvage_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0'}),
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'purchase_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'supplier': forms.TextInput(attrs={'class': 'form-control'}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control'}),
            'warranty_expiry': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'responsible_person': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'depreciation_method': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تصفية العملات النشطة فقط
        self.fields['currency'].queryset = Currency.objects.filter(is_active=True)
        
        # تعيين العملة الافتراضية
        if not self.instance.pk:  # للأصول الجديدة فقط
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                self.fields['currency'].initial = company_settings.base_currency
        
        # تصفية الفئات النشطة فقط
        self.fields['category'].queryset = AssetCategory.objects.filter(is_active=True)
        
        # تصفية المستخدمين النشطين فقط
        self.fields['responsible_person'].queryset = User.objects.filter(is_active=True)


class LiabilityCategoryForm(forms.ModelForm):
    class Meta:
        model = LiabilityCategory
        fields = ['name', 'type', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class LiabilityForm(forms.ModelForm):
    class Meta:
        model = Liability
        fields = ['name', 'category', 'description', 'original_amount', 'current_balance', 'interest_rate',
                 'currency', 'start_date', 'due_date', 'creditor_name', 'creditor_contact', 
                 'contract_number', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'original_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0.001'}),
            'current_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0'}),
            'interest_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'creditor_name': forms.TextInput(attrs={'class': 'form-control'}),
            'creditor_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'contract_number': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تصفية العملات النشطة فقط
        self.fields['currency'].queryset = Currency.objects.filter(is_active=True)
        
        # تعيين العملة الافتراضية
        if not self.instance.pk:  # للخصوم الجديدة فقط
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                self.fields['currency'].initial = company_settings.base_currency
        
        # تصفية الفئات النشطة فقط
        self.fields['category'].queryset = LiabilityCategory.objects.filter(is_active=True)


class DepreciationEntryForm(forms.ModelForm):
    class Meta:
        model = DepreciationEntry
        fields = ['asset', 'depreciation_date', 'depreciation_amount', 'notes']
        widgets = {
            'asset': forms.Select(attrs={'class': 'form-control'}),
            'depreciation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'depreciation_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0.001'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تصفية الأصول النشطة والقابلة للإهلاك فقط
        self.fields['asset'].queryset = Asset.objects.filter(
            status='active',
            category__is_depreciable=True
        )