from django import forms
from django.utils.translation import gettext_lazy as _
from django.forms import inlineformset_factory
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
        fields = ['entry_number', 'entry_date', 'reference_type', 'reference_id', 'description']
        widgets = {
            'entry_number': forms.TextInput(attrs={'class': 'form-control'}),
            'entry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference_type': forms.Select(attrs={'class': 'form-control'}),
            'reference_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
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
                self.fields['entry_number'].initial = seq.get_next_number()
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
    class Meta:
        model = JournalLine
        fields = ['account', 'debit', 'credit', 'line_description']
        widgets = {
            'account': forms.Select(attrs={'class': 'form-control'}),
            'debit': forms.NumberInput(attrs={'class': 'form-control debit-input', 'step': '0.001', 'min': '0'}),
            'credit': forms.NumberInput(attrs={'class': 'form-control credit-input', 'step': '0.001', 'min': '0'}),
            'line_description': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تصفية الحسابات النشطة فقط
        self.fields['account'].queryset = Account.objects.filter(is_active=True)


# إنشاء FormSet للبنود
JournalLineFormSet = inlineformset_factory(
    JournalEntry, 
    JournalLine,
    form=JournalLineForm,
    extra=2,
    min_num=2,
    validate_min=True,
    can_delete=True
)


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
        label=_('نوع الحساب'),
        choices=[('', _('جميع الأنواع'))] + Account.ACCOUNT_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
