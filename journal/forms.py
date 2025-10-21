from django import forms
from django.utils.translation import gettext_lazy as _
from django.forms import inlineformset_factory
from decimal import Decimal
from .models import Account, JournalEntry, JournalLine


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['code', 'name', 'account_type', 'parent', 'description', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_type': forms.Select(attrs={'class': 'form-control'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تصفية الحسابات الرئيسية لتجنب الحلقات المفرغة
        if self.instance.pk:
            self.fields['parent'].queryset = Account.objects.filter(
                is_active=True
            ).exclude(pk=self.instance.pk)
        else:
            self.fields['parent'].queryset = Account.objects.filter(is_active=True)


class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['entry_number', 'entry_date', 'entry_type', 'reference_type', 'reference_id', 'description']
        widgets = {
            'entry_number': forms.TextInput(attrs={'class': 'form-control'}),
            'entry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'entry_type': forms.Select(attrs={'class': 'form-control'}),
            'reference_type': forms.Select(attrs={'class': 'form-control'}),
            'reference_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # تصفية أنواع العمليات - إزالة أنواع الفواتير التي تُنشأ تلقائياً
        # حسب معايير IFRS: القيود المرتبطة بالفواتير يجب أن تُنشأ آلياً من الفواتير فقط
        # لا يجوز إنشاء قيود مبيعات/مشتريات يدوياً بدون مستندات داعمة (فواتير)
        EXCLUDED_TYPES = ['sales_invoice', 'purchase_invoice', 'sales_return', 'purchase_return']
        allowed_choices = [
            (key, value) for key, value in JournalEntry.REFERENCE_TYPES 
            if key not in EXCLUDED_TYPES
        ]
        self.fields['reference_type'].choices = allowed_choices
        
        # إذا كان التعديل وليس إنشاء جديد
        if self.instance and self.instance.pk:
            # تحقق من صلاحية تعديل رقم القيد
            if self.user and not self.user.has_perm('journal.change_entry_number'):
                # إذا لم يكن لديه الصلاحية، اجعل الحقل غير قابل للتعديل
                self.fields['entry_number'].widget.attrs['readonly'] = True
                self.fields['entry_number'].help_text = _('لا تملك صلاحية تعديل رقم القيد')
        else:
            # إنشاء جديد - توليد رقم القيد من تسلسل المستندات
            try:
                from core.models import DocumentSequence
                seq = DocumentSequence.objects.get(document_type='journal_entry')
                self.fields['entry_number'].initial = seq.peek_next_number()
            except DocumentSequence.DoesNotExist:
                pass  # سيتم توليد رقم افتراضي في النموذج
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.entry_number:
            # توليد رقم إذا لم يكن محدداً
            instance.entry_number = instance.generate_entry_number()
        if commit:
            instance.save()
        return instance


class JournalLineForm(forms.ModelForm):
    # حقل نصي للبحث عن الحساب
    account_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control account-search-input',
            'placeholder': _('اكتب للبحث عن الحساب...'),
            'autocomplete': 'off'
        })
    )
    
    class Meta:
        model = JournalLine
        fields = ['account', 'debit', 'credit', 'line_description']
        widgets = {
            'account': forms.HiddenInput(),  # إخفاء الحقل الأصلي
            'debit': forms.NumberInput(attrs={'class': 'form-control debit-input', 'step': '0.001', 'min': '0', 'placeholder': '0'}),
            'credit': forms.NumberInput(attrs={'class': 'form-control credit-input', 'step': '0.001', 'min': '0', 'placeholder': '0'}),
            'line_description': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # إزالة queryset لأن الحقل أصبح مخفي
        # جعل الحقول غير مطلوبة (سيتم التحقق في clean)
        self.fields['account'].required = False
        self.fields['debit'].required = False
        self.fields['credit'].required = False
        # عدم تعيين قيمة افتراضية للحقول - نتركها فارغة
        if not self.instance.pk:  # نموذج جديد فقط
            self.fields['debit'].initial = ''
            self.fields['credit'].initial = ''
            self.fields['account_search'].initial = ''
    
    def clean(self):
        """تخطي التحقق من البنود الفارغة تماماً"""
        cleaned_data = super().clean()
        account = cleaned_data.get('account')
        account_search = cleaned_data.get('account_search')
        
        # إذا كان account_search موجود ولا يوجد account، نبحث عن الحساب
        if account_search and not account:
            try:
                from django.db import models
                from .models import Account
                account = Account.objects.filter(
                    models.Q(name__icontains=account_search) | 
                    models.Q(code__icontains=account_search)
                ).first()
                if account:
                    cleaned_data['account'] = account
            except:
                pass
        
        # معالجة القيم الفارغة بشكل صحيح
        debit = cleaned_data.get('debit')
        credit = cleaned_data.get('credit')
        
        # تحويل None أو '' إلى Decimal('0')
        if debit is None or debit == '':
            debit = Decimal('0')
            cleaned_data['debit'] = debit
        if credit is None or credit == '':
            credit = Decimal('0')
            cleaned_data['credit'] = credit
        
        # إذا كان البند فارغاً تماماً (بغض النظر عن الحساب)، نتجاهله
        # هذا يسمح للمستخدم باختيار حساب وترك القيم فارغة
        if debit == 0 and credit == 0:
            # لا نرفع ValidationError - نترك الـ formset يتعامل معه
            return cleaned_data
        
        # إذا كانت هناك قيمة ولكن لا يوجد حساب، نرفع خطأ
        if not account and (debit > 0 or credit > 0):
            raise forms.ValidationError(_('يجب اختيار حساب'))
        
        return cleaned_data


# إنشاء FormSet للبنود - Base Class
BaseJournalLineFormSet = inlineformset_factory(
    JournalEntry, 
    JournalLine,
    form=JournalLineForm,
    extra=2,
    min_num=0,
    validate_min=False,
    can_delete=True
)

class JournalLineFormSet(BaseJournalLineFormSet):
    def clean(self):
        """التحقق من توازن البنود"""
        super().clean()
        
        # تجاهل أخطاء النماذج الفردية للحقول الفارغة
        total_debit = Decimal('0')
        total_credit = Decimal('0')
        valid_lines_count = 0
        
        for form in self.forms:
            # تجاهل النماذج المحذوفة
            if form.cleaned_data and form.cleaned_data.get('DELETE', False):
                continue
            
            # إذا لم يكن هناك cleaned_data، تجاهل
            if not form.cleaned_data:
                continue
            
            account = form.cleaned_data.get('account')
            
            # إذا لم يكن هناك حساب محدد، تجاهل هذا البند
            if not account:
                continue
            
            # تحويل القيم إلى Decimal والتعامل مع None أو القيم الفارغة
            debit_value = form.cleaned_data.get('debit')
            credit_value = form.cleaned_data.get('credit')
            
            try:
                debit = Decimal(str(debit_value)) if debit_value not in (None, '', 0) else Decimal('0')
            except:
                debit = Decimal('0')
                
            try:
                credit = Decimal(str(credit_value)) if credit_value not in (None, '', 0) else Decimal('0')
            except:
                credit = Decimal('0')
            
            # احسب البند الصالح (حساب محدد + قيمة غير صفرية)
            if debit > Decimal('0') or credit > Decimal('0'):
                valid_lines_count += 1
                total_debit += debit
                total_credit += credit
        
        # التحقق من وجود بنود صالحة
        if valid_lines_count == 0:
            raise forms.ValidationError(_('يجب إدخال بنود القيد المحاسبي'))
        
        # التحقق من التوازن
        if abs(total_debit - total_credit) > Decimal('0.001'):
            raise forms.ValidationError(_('يجب أن يساوي مجموع المدين مجموع الدائن'))


class JournalSearchForm(forms.Form):
    """نموذج البحث في القيود"""
    date_from = forms.DateField(
        label=_('From Date'),
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        label=_('To Date'),
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    reference_type = forms.ChoiceField(
        label=_('نوع العملية'),
        choices=[('', _('All'))] + JournalEntry.REFERENCE_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    account = forms.ModelChoiceField(
        label=_('الحساب'),
        queryset=Account.objects.filter(is_active=True),
        required=False,
        empty_label=_('جميع الحسابات'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    entry_number = forms.CharField(
        label=_('رقم القيد'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )


class TrialBalanceForm(forms.Form):
    """نموذج ميزان المراجعة"""
    date_from = forms.DateField(
        label=_('From Date'),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        label=_('To Date'),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    account_type = forms.ChoiceField(
        label=_('Account Type'),
        choices=[('', _('جميع الأنواع'))] + Account.ACCOUNT_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
