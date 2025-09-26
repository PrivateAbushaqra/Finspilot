from django import forms
from django.utils.translation import gettext_lazy as _
from .models import RevenueExpenseCategory, RevenueExpenseEntry, RecurringRevenueExpense, Sector
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
        fields = ['type', 'category', 'sector', 'amount', 'currency', 'description', 'payment_method', 'reference_number', 'date']
        widgets = {
            'type': forms.Select(attrs={
                'class': 'form-control', 
                'required': True,
                'data-placeholder': 'اختر نوع القيد'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control', 
                'required': True,
                'data-placeholder': 'اختر الفئة'
            }),
            'sector': forms.Select(attrs={
                'class': 'form-control',
                'data-placeholder': 'اختر القطاع (اختياري)'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.001', 
                'min': '0.001',
                'required': True,
                'placeholder': 'أدخل المبلغ'
            }),
            'currency': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'required': True,
                'placeholder': 'أدخل وصف القيد...'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
                'data-placeholder': 'اختر طريقة الدفع'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم الفاتورة أو المرجع (اختياري)'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control', 
                'type': 'date',
                'required': True
            }),
        }
        labels = {
            'type': _('نوع القيد'),
            'category': _('الفئة'),
            'amount': _('المبلغ'),
            'currency': _('العملة'),
            'description': _('الوصف'),
            'payment_method': _('طريقة الدفع'),
            'reference_number': _('رقم المرجع'),
            'date': _('التاريخ'),
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
        
        # تصفية الفئات النشطة فقط في البداية
        self.fields['category'].queryset = RevenueExpenseCategory.objects.filter(is_active=True)
        
        # إضافة خيار فارغ للحقول المطلوبة
        self.fields['type'].empty_label = "اختر نوع القيد"
        self.fields['category'].empty_label = "اختر الفئة"
        self.fields['currency'].empty_label = "اختر العملة"
        self.fields['payment_method'].empty_label = "اختر طريقة الدفع (اختياري)"
        
        # تصفية الفئات حسب النوع المحدد
        if 'type' in self.data:
            try:
                type_value = self.data.get('type')
                self.fields['category'].queryset = RevenueExpenseCategory.objects.filter(
                    type=type_value, is_active=True
                ).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.type:
            # للتعديل، تحديد الفئات المناسبة للنوع الحالي
            self.fields['category'].queryset = RevenueExpenseCategory.objects.filter(
                type=self.instance.type, is_active=True
            ).order_by('name')
    
    def clean_amount(self):
        """التحقق من صحة المبلغ"""
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError(_('يجب أن يكون المبلغ أكبر من صفر'))
        return amount
    
    def clean_date(self):
        """التحقق من صحة التاريخ"""
        from datetime import date
        entry_date = self.cleaned_data.get('date')
        if entry_date and entry_date > date.today():
            raise forms.ValidationError(_('لا يمكن أن يكون تاريخ القيد في المستقبل'))
        return entry_date
    
    def clean(self):
        """التحقق الشامل من البيانات"""
        cleaned_data = super().clean()
        entry_type = cleaned_data.get('type')
        category = cleaned_data.get('category')
        
        # التحقق من تطابق نوع القيد مع نوع الفئة
        if entry_type and category:
            if category.type != entry_type:
                raise forms.ValidationError({
                    'category': _('الفئة المختارة لا تتطابق مع نوع القيد')
                })
        
        return cleaned_data


class RecurringRevenueExpenseForm(forms.ModelForm):
    class Meta:
        model = RecurringRevenueExpense
        fields = ['name', 'category', 'sector', 'amount', 'currency', 'frequency', 'start_date', 'end_date', 
                 'description', 'payment_method', 'is_active', 'auto_generate']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'sector': forms.Select(attrs={'class': 'form-control'}),
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