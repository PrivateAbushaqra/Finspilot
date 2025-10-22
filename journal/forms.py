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
    # حقول مخصصة غير مقيدة بالخيارات
    entry_type = forms.CharField(
        label=_('Entry Type'),
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=True
    )
    reference_type = forms.CharField(
        label=_('Reference Type'),
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=True
    )
    
    class Meta:
        model = JournalEntry
        fields = ['entry_number', 'entry_date', 'reference_id', 'description']
        widgets = {
            'entry_number': forms.TextInput(attrs={'class': 'form-control'}),
            'entry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reference_id': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # إذا كان التعديل وليس إنشاء جديد
        if self.instance and self.instance.pk:
            # تعيين القيم الأولية للحقول المخصصة
            self.fields['entry_type'].initial = self.instance.entry_type
            self.fields['reference_type'].initial = self.instance.reference_type
            
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
    
    def clean(self):
        cleaned_data = super().clean()
        
        # التحقق من صحة القيم
        entry_type = cleaned_data.get('entry_type')
        reference_type = cleaned_data.get('reference_type')
        
        # التحقق من أن entry_type صحيح
        if entry_type and entry_type not in dict(JournalEntry.ENTRY_TYPES):
            # إذا لم يكن في القائمة الرسمية، تأكد أنه مسموح (مثل القيم القديمة)
            if not (self.instance and self.instance.pk and entry_type == self.instance.entry_type):
                raise forms.ValidationError(_('نوع القيد غير صحيح'))
        
        # التحقق من أن reference_type صحيح
        if reference_type and reference_type not in dict(JournalEntry.REFERENCE_TYPES):
            # إذا لم يكن في القائمة الرسمية، تأكد أنه مسموح (مثل القيم القديمة)
            if not (self.instance and self.instance.pk and reference_type == self.instance.reference_type):
                raise forms.ValidationError(_('نوع العملية غير صحيح'))
        
        return cleaned_data
    
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
        else:  # نموذج موجود - تعيين قيمة البحث باسم الحساب
            if self.instance.account:
                self.fields['account_search'].initial = self.instance.account.name
                self.fields['account'].initial = self.instance.account.id
            # تعيين القيم الأولية للمدين والدائن - تأكد من أن القيمة تُعرض بشكل صحيح
            # استخدام float بدلاً من Decimal لتجنب مشاكل JSON serialization
            debit_val = float(self.instance.debit)
            credit_val = float(self.instance.credit)
            
            # تعيين initial و widget value للتأكد من ظهور القيمة
            if debit_val > 0:
                self.fields['debit'].initial = debit_val
                self.fields['debit'].widget.attrs['value'] = '{:.3f}'.format(debit_val)
            else:
                self.fields['debit'].initial = ''
                
            if credit_val > 0:
                self.fields['credit'].initial = credit_val
                self.fields['credit'].widget.attrs['value'] = '{:.3f}'.format(credit_val)
            else:
                self.fields['credit'].initial = ''
    
    def clean(self):
        """تخطي التحقق من البنود الفارغة تماماً"""
        cleaned_data = super().clean()
        account = cleaned_data.get('account')
        account_search = cleaned_data.get('account_search')
        
        # إذا كان هذا نموذج موجود (تعديل) وليس لديه account في cleaned_data
        # حاول استخدام الحساب من instance
        if self.instance and self.instance.pk and not account:
            if self.instance.account:
                cleaned_data['account'] = self.instance.account
                account = self.instance.account
        
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
    extra=0,  # لا نضيف صفوف فارغة تلقائياً - المستخدم يضيفها يدوياً
    min_num=0,
    validate_min=False,
    can_delete=True,
    fk_name='journal_entry'  # تحديد اسم ForeignKey بشكل صريح
)

class JournalLineFormSet(BaseJournalLineFormSet):
    def clean(self):
        """التحقق من توازن البنود"""
        # لا نستدعي super().clean() لأننا نريد التحكم الكامل في التحقق
        if any(self.errors):
            # إذا كانت هناك أخطاء في النماذج الفردية، لا نتحقق من التوازن
            # نسمح للمستخدم برؤية الأخطاء أولاً
            return
        
        total_debit = Decimal('0')
        total_credit = Decimal('0')
        valid_lines_count = 0
        
        for form in self.forms:
            # تجاهل النماذج المحذوفة
            if self.can_delete and self._should_delete_form(form):
                continue
            
            # إذا لم يكن هناك cleaned_data أو كان فارغاً، تجاهل
            if not hasattr(form, 'cleaned_data') or not form.cleaned_data:
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
