from django import forms
from django.utils.translation import gettext_lazy as _
from .models import RevenueExpenseCategory, RevenueExpenseEntry, RecurringRevenueExpense
from settings.models import Currency, CompanySettings


class RevenueExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = RevenueExpenseCategory
        fields = ['name', 'type', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class RevenueExpenseEntryForm(forms.ModelForm):
    class Meta:
        model = RevenueExpenseEntry
        fields = ['type', 'category', 'amount', 'currency', 'description', 'payment_method', 'reference_number', 'date']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0.001'}),
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تصفية العملات النشطة فقط
        self.fields['currency'].queryset = Currency.objects.filter(is_active=True)
        
        # تعيين العملة الافتراضية
        if not self.instance.pk:  # للقيود الجديدة فقط
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                self.fields['currency'].initial = company_settings.base_currency
        
        # تصفية الفئات حسب النوع المحدد
        if 'type' in self.data:
            try:
                type_value = self.data.get('type')
                self.fields['category'].queryset = RevenueExpenseCategory.objects.filter(
                    type=type_value, is_active=True
                )
            except (ValueError, TypeError):
                pass


class RecurringRevenueExpenseForm(forms.ModelForm):
    class Meta:
        model = RecurringRevenueExpense
        fields = ['name', 'category', 'amount', 'currency', 'frequency', 'start_date', 'end_date', 
                 'description', 'payment_method', 'is_active', 'auto_generate']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'min': '0.001'}),
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'frequency': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_generate': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تصفية العملات النشطة فقط
        self.fields['currency'].queryset = Currency.objects.filter(is_active=True)
        
        # تعيين العملة الافتراضية
        if not self.instance.pk:  # للقيود الجديدة فقط
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                self.fields['currency'].initial = company_settings.base_currency
        
        # تصفية الفئات النشطة فقط
        self.fields['category'].queryset = RevenueExpenseCategory.objects.filter(is_active=True)