from django import forms
from django.utils.translation import gettext_lazy as _
from django.forms import inlineformset_factory

from .models import PaymentVoucher  # , PaymentVoucherItem
from customers.models import CustomerSupplier
from cashboxes.models import Cashbox
from banks.models import BankAccount


class PaymentVoucherForm(forms.ModelForm):
    """فورم سند الصرف"""
    
    class Meta:
        model = PaymentVoucher
        fields = [
            'voucher_number', 'date', 'voucher_type', 'payment_type', 'amount',
            'supplier', 'beneficiary_name', 'description', 'notes',
            'cashbox', 'bank', 'bank_reference',
            'check_number', 'check_date', 'check_due_date', 'check_bank_name'
        ]
        widgets = {
            'voucher_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'أدخل رقم السند يدوياً'
            }),
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'voucher_type': forms.Select(attrs={'class': 'form-control'}),
            'payment_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.001',
                'min': '0'
            }),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'beneficiary_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
            'cashbox': forms.Select(attrs={'class': 'form-control'}),
            'bank': forms.Select(attrs={'class': 'form-control'}),
            'bank_reference': forms.TextInput(attrs={'class': 'form-control'}),
            'check_number': forms.TextInput(attrs={'class': 'form-control'}),
            'check_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'check_due_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'check_bank_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تحديد خيارات الموردين
        self.fields['supplier'].queryset = CustomerSupplier.objects.filter(
            type__in=['supplier', 'both']
        ).order_by('name')
        self.fields['supplier'].empty_label = _('اختر المورد...')
        
        # تحديد خيارات الصناديق
        self.fields['cashbox'].queryset = Cashbox.objects.filter(
            is_active=True
        ).order_by('name')
        self.fields['cashbox'].empty_label = _('اختر الصندوق...')
        
        # تحديد خيارات البنوك
        self.fields['bank'].queryset = BankAccount.objects.filter(
            is_active=True
        ).order_by('name')
        self.fields['bank'].empty_label = _('اختر البنك...')
        
        # إضافة علامات مطلوبة
        self.fields['voucher_number'].required = True
        self.fields['date'].required = True
        self.fields['voucher_type'].required = True
        self.fields['payment_type'].required = True
        self.fields['amount'].required = True
        self.fields['description'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        voucher_number = cleaned_data.get('voucher_number')
        voucher_type = cleaned_data.get('voucher_type')
        payment_type = cleaned_data.get('payment_type')
        supplier = cleaned_data.get('supplier')
        beneficiary_name = cleaned_data.get('beneficiary_name')
        cashbox = cleaned_data.get('cashbox')
        bank = cleaned_data.get('bank')
        check_number = cleaned_data.get('check_number')
        check_date = cleaned_data.get('check_date')
        check_due_date = cleaned_data.get('check_due_date')
        check_bank_name = cleaned_data.get('check_bank_name')
        
        # التحقق من تفرد رقم المستند
        if voucher_number:
            existing_voucher = PaymentVoucher.objects.filter(
                voucher_number=voucher_number,
                is_active=True  # التحقق من السندات النشطة فقط
            )
            if self.instance.pk:
                existing_voucher = existing_voucher.exclude(pk=self.instance.pk)
            if existing_voucher.exists():
                raise forms.ValidationError(_('رقم المستند موجود مسبقاً. يرجى استخدام رقم آخر.'))
        
        # التحقق من المستفيد
        if voucher_type == 'supplier' and not supplier:
            raise forms.ValidationError(_('يجب تحديد المورد لسند دفع المورد'))
        
        if not supplier and not beneficiary_name:
            raise forms.ValidationError(_('يجب تحديد إما المورد أو اسم المستفيد'))
        
        # التحقق من طريقة الدفع
        if payment_type == 'cash' and not cashbox:
            raise forms.ValidationError(_('يجب تحديد الصندوق النقدي للدفع النقدي'))
        
        if payment_type == 'bank_transfer' and not bank:
            raise forms.ValidationError(_('يجب تحديد البنك للتحويل البنكي'))
        
        if payment_type == 'check':
            if not check_number:
                raise forms.ValidationError(_('رقم الشيك مطلوب'))
            if not check_date:
                raise forms.ValidationError(_('تاريخ الشيك مطلوب'))
            if not check_due_date:
                raise forms.ValidationError(_('تاريخ استحقاق الشيك مطلوب'))
            if not check_bank_name:
                raise forms.ValidationError(_('اسم البنك مطلوب'))
        
        return cleaned_data


# PaymentVoucherItem سيتم إضافته لاحقاً
# class PaymentVoucherItemForm(forms.ModelForm):
#     """فورم عنصر سند الصرف"""
#     
#     class Meta:
#         model = PaymentVoucherItem
#         fields = ['description', 'amount', 'account']
#         widgets = {
#             'description': forms.TextInput(attrs={'class': 'form-control'}),
#             'amount': forms.NumberInput(attrs={
#                 'class': 'form-control',
#                 'step': '0.001',
#                 'min': '0'
#             }),
#             'account': forms.Select(attrs={'class': 'form-control'}),
#         }


# FormSet للعناصر - سيتم إضافته لاحقاً
# PaymentVoucherItemFormSet = inlineformset_factory(
#     PaymentVoucher,
#     PaymentVoucherItem,
#     form=PaymentVoucherItemForm,
#     extra=1,
#     can_delete=True
# )


class PaymentVoucherFilterForm(forms.Form):
    """فورم تصفية سندات الصرف"""
    
    search = forms.CharField(
        label=_('البحث'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('رقم السند، المستفيد، أو الوصف...')
        })
    )
    
    payment_type = forms.ChoiceField(
        label=_('نوع الدفع'),
        choices=[('', _('الكل'))] + PaymentVoucher.PAYMENT_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    voucher_type = forms.ChoiceField(
        label=_('نوع السند'),
        choices=[('', _('الكل'))] + PaymentVoucher.VOUCHER_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        label=_('من تاريخ'),
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    date_to = forms.DateField(
        label=_('إلى تاريخ'),
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )


class PaymentVoucherReverseForm(forms.Form):
    """فورم عكس سند الصرف"""
    
    reason = forms.CharField(
        label=_('سبب العكس'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'required': True
        })
    )
