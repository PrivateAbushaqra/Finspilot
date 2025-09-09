from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from datetime import date, datetime
from decimal import Decimal

User = get_user_model()

from .models import (
    Department, Position, Employee, Contract, Attendance, 
    LeaveType, LeaveRequest, PayrollPeriod, PayrollEntry, EmployeeDocument
)


class EmployeeForm(forms.ModelForm):
    """نموذج إنشاء وتحديث الموظف"""
    
    class Meta:
        model = Employee
        fields = [
            'employee_id', 'first_name', 'last_name', 'first_name_en', 'last_name_en',
            'national_id', 'passport_number', 'birth_date', 'gender', 'marital_status',
            'email', 'phone', 'mobile', 'address', 'department', 'position',
            'hire_date', 'employment_type', 'status', 'basic_salary',
            'allowances', 'social_security_number', 'social_security_rate',
            'emergency_contact_name', 'emergency_contact_phone', 'notes', 'user'
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'hire_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'employee_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Employee ID')}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('First Name')}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Last Name')}),
            'first_name_en': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('First Name (English)')}),
            'last_name_en': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Last Name (English)')}),
            'national_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('National ID')}),
            'passport_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Passport Number')}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('Email')}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Phone')}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Mobile')}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Address')}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Emergency Contact Name')}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Emergency Contact Phone')}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'position': forms.Select(attrs={'class': 'form-control'}),
            'employment_type': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'marital_status': forms.Select(attrs={'class': 'form-control'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'placeholder': _('Basic Salary')}),
            'allowances': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'placeholder': _('Allowances')}),
            'social_security_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Social Security Number')}),
            'social_security_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': _('Social Security Rate %')}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Notes')}),
            'user': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # فلترة المستخدمين لعرض المتاحين فقط
        self.fields['user'].queryset = User.objects.filter(
            employee_profile__isnull=True
        ).exclude(id=self.instance.user_id if self.instance.user else None)
        self.fields['user'].required = False
        self.fields['user'].empty_label = _('Select User (Optional)')
        
        # فلترة الأقسام النشطة فقط
        self.fields['department'].queryset = Department.objects.filter(is_active=True)
        
        # فلترة المناصب النشطة فقط
        self.fields['position'].queryset = Position.objects.filter(is_active=True)

    def clean_employee_id(self):
        employee_id = self.cleaned_data['employee_id']
        if Employee.objects.filter(employee_id=employee_id).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_('Employee ID already exists.'))
        return employee_id

    def clean_national_id(self):
        national_id = self.cleaned_data['national_id']
        if Employee.objects.filter(national_id=national_id).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_('National ID already exists.'))
        return national_id

    def clean_email(self):
        email = self.cleaned_data['email']
        if Employee.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_('Email already exists.'))
        return email

    def clean_birth_date(self):
        birth_date = self.cleaned_data['birth_date']
        if birth_date and birth_date >= date.today():
            raise ValidationError(_('Birth date must be in the past.'))
        # التحقق من العمر (أكبر من 16 سنة)
        if birth_date:
            age = (date.today() - birth_date).days / 365.25
            if age < 16:
                raise ValidationError(_('Employee must be at least 16 years old.'))
        return birth_date

    def clean_hire_date(self):
        hire_date = self.cleaned_data['hire_date']
        birth_date = self.cleaned_data.get('birth_date')
        
        if hire_date and hire_date > date.today():
            raise ValidationError(_('Hire date cannot be in the future.'))
            
        if hire_date and birth_date:
            age_at_hire = (hire_date - birth_date).days / 365.25
            if age_at_hire < 16:
                raise ValidationError(_('Employee must be at least 16 years old at hire date.'))
                
        return hire_date


class ContractForm(forms.ModelForm):
    """نموذج العقود"""
    
    class Meta:
        model = Contract
        fields = [
            'employee', 'contract_number', 'contract_type', 'start_date', 'end_date',
            'salary', 'allowances', 'working_hours_per_day', 'working_days_per_week',
            'annual_leave_days', 'status', 'terms_and_conditions', 'notes'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'contract_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Contract Number')}),
            'contract_type': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'allowances': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'working_hours_per_day': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '12'}),
            'working_days_per_week': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '7'}),
            'annual_leave_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'terms_and_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        contract_type = cleaned_data.get('contract_type')

        if start_date and end_date:
            if end_date <= start_date:
                raise ValidationError(_('End date must be after start date.'))

        # التحقق من وجوب تاريخ الانتهاء للعقود المؤقتة
        if contract_type == 'temporary' and not end_date:
            raise ValidationError({'end_date': _('End date is required for temporary contracts.')})

        return cleaned_data


class AttendanceForm(forms.ModelForm):
    """نموذج الحضور والانصراف"""
    
    class Meta:
        model = Attendance
        fields = [
            'employee', 'date', 'check_in_time', 'check_out_time',
            'attendance_type', 'overtime_hours', 'notes'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'check_in_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'check_out_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'attendance_type': forms.Select(attrs={'class': 'form-control'}),
            'overtime_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ترتيب الموظفين بحسب الاسم وإظهار الموظفين النشطين فقط
        active_employees = Employee.objects.filter(status='active').select_related('department', 'position')
        self.fields['employee'].queryset = active_employees.order_by('first_name', 'last_name')
        
        # تحسين عرض قائمة الموظفين
        self.fields['employee'].empty_label = _('اختر الموظف')
        
        # تحديد التاريخ الافتراضي لليوم الحالي
        if not self.instance.pk:
            from datetime import date
            self.fields['date'].initial = date.today()

    def clean(self):
        cleaned_data = super().clean()
        check_in_time = cleaned_data.get('check_in_time')
        check_out_time = cleaned_data.get('check_out_time')
        attendance_type = cleaned_data.get('attendance_type')

        # التحقق من أوقات الحضور والانصراف
        if attendance_type == 'present':
            if not check_in_time:
                raise ValidationError({'check_in_time': _('Check-in time is required for present attendance.')})

        if check_in_time and check_out_time:
            if check_out_time <= check_in_time:
                raise ValidationError({'check_out_time': _('Check-out time must be after check-in time.')})

        return cleaned_data


class AttendanceUploadForm(forms.Form):
    """نموذج رفع ملف الحضور"""
    csv_file = forms.FileField(
        label=_('CSV File'),
        widget=forms.FileInput(attrs={'class': 'form-control-file', 'accept': '.csv'})
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        if not csv_file.name.endswith('.csv'):
            raise ValidationError(_('File must be in CSV format.'))
        return csv_file


class LeaveRequestForm(forms.ModelForm):
    """نموذج طلب الإجازة"""
    
    class Meta:
        model = LeaveRequest
        fields = [
            'employee', 'leave_type', 'start_date', 'end_date',
            'reason'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'leave_type': forms.Select(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Reason for leave')}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = Employee.objects.filter(status='active')
        self.fields['leave_type'].queryset = LeaveType.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        employee = cleaned_data.get('employee')
        leave_type = cleaned_data.get('leave_type')

        if start_date and end_date:
            if end_date < start_date:
                raise ValidationError({'end_date': _('End date must be after or equal to start date.')})

            # حساب عدد الأيام
            days_count = (end_date - start_date).days + 1

            # التحقق من الحد الأقصى للأيام
            if leave_type and leave_type.max_days and days_count > leave_type.max_days:
                raise ValidationError(
                    _('Leave request exceeds maximum allowed days for this leave type (%(max_days)s days).') %
                    {'max_days': leave_type.max_days}
                )

            # التحقق من رصيد الإجازات
            if employee and leave_type:
                current_balance = employee.get_current_leave_balance().get(leave_type.id, 0)
                if days_count > current_balance:
                    raise ValidationError(
                        _('Leave request exceeds available balance (%(balance)s days).') %
                        {'balance': current_balance}
                    )

        return cleaned_data


class PayrollPeriodForm(forms.ModelForm):
    """نموذج فترة الرواتب"""
    
    class Meta:
        model = PayrollPeriod
        fields = ['name', 'start_date', 'end_date', 'notes']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Period Name')}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if end_date <= start_date:
                raise ValidationError({'end_date': _('End date must be after start date.')})

            # التحقق من عدم تداخل الفترات
            overlapping_periods = PayrollPeriod.objects.filter(
                start_date__lte=end_date,
                end_date__gte=start_date
            ).exclude(pk=self.instance.pk if self.instance else None)

            if overlapping_periods.exists():
                raise ValidationError(_('Payroll period overlaps with existing period.'))

        return cleaned_data


class PayrollEntryForm(forms.ModelForm):
    """نموذج قيد الراتب"""
    
    class Meta:
        model = PayrollEntry
        fields = [
            'employee', 'basic_salary', 'allowances', 'overtime_amount',
            'bonuses', 'social_security_deduction', 'income_tax',
            'deductions', 'unpaid_leave_deduction', 'notes'
        ]
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'allowances': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'overtime_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'bonuses': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'social_security_deduction': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'income_tax': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'deductions': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'unpaid_leave_deduction': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.payroll_period = kwargs.pop('payroll_period', None)
        super().__init__(*args, **kwargs)
        
        if self.payroll_period:
            # عرض الموظفين الذين لم يتم إنشاء قيد راتب لهم في هذه الفترة
            existing_entries = PayrollEntry.objects.filter(
                payroll_period=self.payroll_period
            ).values_list('employee_id', flat=True)
            
            self.fields['employee'].queryset = Employee.objects.filter(
                status='active'
            ).exclude(id__in=existing_entries)


class EmployeeDocumentForm(forms.ModelForm):
    """نموذج مستندات الموظف"""
    
    class Meta:
        model = EmployeeDocument
        fields = ['employee', 'document_type', 'title', 'description', 'file']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'document_type': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Document Title')}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'file': forms.FileInput(attrs={'class': 'form-control-file'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = Employee.objects.filter(status='active')
        
        # إذا كان هناك instance (تحديث)، اجعل حقل employee غير قابل للتعديل
        if self.instance and self.instance.pk:
            self.fields['employee'].disabled = True
            # في حالة التحديث، الملف غير مطلوب
            self.fields['file'].required = False


class DepartmentForm(forms.ModelForm):
    """نموذج الأقسام"""
    
    class Meta:
        model = Department
        fields = ['name', 'code', 'description', 'manager', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Department Name')}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Department Code')}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'manager': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['manager'].queryset = Employee.objects.filter(status='active')
        self.fields['manager'].required = False
        self.fields['manager'].empty_label = _('Select Manager (Optional)')

    def clean_code(self):
        code = self.cleaned_data['code']
        if Department.objects.filter(code=code).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_('Department code already exists.'))
        return code


class PositionForm(forms.ModelForm):
    """نموذج المناصب"""
    
    class Meta:
        model = Position
        fields = [
            'title', 'code', 'department', 'description',
            'min_salary', 'max_salary', 'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Position Title')}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Position Code')}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'min_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'max_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.filter(is_active=True)

    def clean_code(self):
        code = self.cleaned_data['code']
        if Position.objects.filter(code=code).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_('Position code already exists.'))
        return code

    def clean(self):
        cleaned_data = super().clean()
        min_salary = cleaned_data.get('min_salary')
        max_salary = cleaned_data.get('max_salary')

        if min_salary and max_salary:
            if max_salary <= min_salary:
                raise ValidationError({'max_salary': _('Maximum salary must be greater than minimum salary.')})

        return cleaned_data
