from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import date, datetime
import uuid

User = get_user_model()

class Department(models.Model):
    """الأقسام في الشركة"""
    name = models.CharField(_('Department Name'), max_length=200)
    code = models.CharField(_('Department Code'), max_length=20, unique=True)
    description = models.TextField(_('Description'), blank=True)
    manager = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True, blank=True, 
                               related_name='managed_departments', verbose_name=_('Manager'))
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')
        ordering = ['name']
        permissions = [
            ("view_hr_department", _("Can View Departments")),
            ("add_hr_department", _("Can Add Departments")),
            ("change_hr_department", _("Can Change Departments")),
            ("delete_hr_department", _("Can Delete Departments")),
        ]

    def __str__(self):
        return self.name

class Position(models.Model):
    """المناصب والوظائف"""
    title = models.CharField(_('Position Title'), max_length=200)
    code = models.CharField(_('Position Code'), max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, 
                                  related_name='positions', verbose_name=_('Department'))
    description = models.TextField(_('Description'), blank=True)
    min_salary = models.DecimalField(_('Minimum Salary'), max_digits=10, decimal_places=3, 
                                   validators=[MinValueValidator(Decimal('0'))], default=0)
    max_salary = models.DecimalField(_('Maximum Salary'), max_digits=10, decimal_places=3, 
                                   validators=[MinValueValidator(Decimal('0'))], default=0)
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Position')
        verbose_name_plural = _('Positions')
        ordering = ['department__name', 'title']
        permissions = [
            ("view_hr_position", _("Can View Positions")),
            ("add_hr_position", _("Can Add Positions")),
            ("change_hr_position", _("Can Change Positions")),
            ("delete_hr_position", _("Can Delete Positions")),
        ]

    def __str__(self):
        return f"{self.title} - {self.department.name}"

class Employee(models.Model):
    """الموظفين"""
    GENDER_CHOICES = [
        ('M', _('Male')),
        ('F', _('Female')),
    ]
    
    MARITAL_STATUS_CHOICES = [
        ('single', _('Single')),
        ('married', _('Married')),
        ('divorced', _('Divorced')),
        ('widowed', _('Widowed')),
    ]

    EMPLOYMENT_TYPE_CHOICES = [
        ('full_time', _('Full Time')),
        ('part_time', _('Part Time')),
        ('contract', _('Contract')),
        ('internship', _('Internship')),
    ]

    STATUS_CHOICES = [
        ('active', _('Active')),
        ('inactive', _('Inactive')),
        ('terminated', _('Terminated')),
        ('on_leave', _('On Leave')),
    ]
    
    TERMINATION_REASON_CHOICES = [
        ('dismissal', _('Dismissal')),
        ('resignation', _('Resignation')),
        ('retirement', _('Retirement')),
    ]

    # معلومات شخصية
    employee_id = models.CharField(_('Employee ID'), max_length=20, unique=True)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, 
                               related_name='employee_profile', verbose_name=_('System User'))
    first_name = models.CharField(_('First Name'), max_length=100)
    last_name = models.CharField(_('Last Name'), max_length=100)
    first_name_en = models.CharField(_('First Name (English)'), max_length=100, blank=True)
    last_name_en = models.CharField(_('Last Name (English)'), max_length=100, blank=True)
    national_id = models.CharField(_('National ID'), max_length=20, unique=True)
    passport_number = models.CharField(_('Passport Number'), max_length=20, blank=True)
    birth_date = models.DateField(_('Birth Date'))
    gender = models.CharField(_('Gender'), max_length=1, choices=GENDER_CHOICES)
    marital_status = models.CharField(_('Marital Status'), max_length=20, choices=MARITAL_STATUS_CHOICES)
    
    # معلومات الاتصال
    email = models.EmailField(_('Email'), unique=True)
    phone = models.CharField(_('Phone'), max_length=20)
    mobile = models.CharField(_('Mobile'), max_length=20, blank=True)
    address = models.TextField(_('Address'), blank=True)
    
    # معلومات الوظيفة
    department = models.ForeignKey(Department, on_delete=models.PROTECT, 
                                  related_name='employees', verbose_name=_('Department'))
    position = models.ForeignKey(Position, on_delete=models.PROTECT, 
                                related_name='employees', verbose_name=_('Position'))
    employment_type = models.CharField(_('Employment Type'), max_length=20, choices=EMPLOYMENT_TYPE_CHOICES)
    hire_date = models.DateField(_('Hire Date'))
    probation_period_days = models.IntegerField(_('Probation Period (Days)'), 
                                               validators=[MinValueValidator(0)], 
                                               default=0,
                                               help_text=_('Number of days for probation period. 0 means no probation.'))
    termination_date = models.DateField(_('Termination Date'), null=True, blank=True)
    
    # معلومات إنهاء الخدمة
    is_terminated = models.BooleanField(_('Is Terminated'), default=False)
    termination_reason = models.CharField(_('Termination Reason'), max_length=20, 
                                         choices=TERMINATION_REASON_CHOICES, blank=True, null=True)
    termination_notes = models.TextField(_('Termination Notes'), blank=True)
    
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='active')
    
    # معلومات الراتب
    basic_salary = models.DecimalField(_('Basic Salary'), max_digits=10, decimal_places=3, 
                                     validators=[MinValueValidator(Decimal('0'))], default=0)
    allowances = models.DecimalField(_('Allowances'), max_digits=10, decimal_places=3, 
                                   validators=[MinValueValidator(Decimal('0'))], default=0)
    
    # معلومات الضريبة المقتطعة
    withholding_tax_rate = models.DecimalField(_('Withholding Tax Rate %'), max_digits=5, decimal_places=2,
                                              validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
                                              default=Decimal('0'))
    
    # معلومات الضمان الاجتماعي
    social_security_number = models.CharField(_('Social Security Number'), max_length=20, blank=True)
    social_security_rate = models.DecimalField(_('Social Security Rate %'), max_digits=5, decimal_places=2, 
                                             validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))], 
                                             default=Decimal('7.5'))
    company_social_security_rate = models.DecimalField(_('Company Social Security Rate %'), max_digits=5, decimal_places=2,
                                                       validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
                                                       default=Decimal('9.75'))
    
    # الاقتطاعات الإضافية - تم نقلها إلى نموذج EmployeeDeduction
    DEDUCTION_TYPE_CHOICES = [
        ('percentage', _('Percentage')),
        ('fixed', _('Fixed Amount')),
    ]
    
    # معلومات أخرى
    emergency_contact_name = models.CharField(_('Emergency Contact Name'), max_length=200, blank=True)
    emergency_contact_phone = models.CharField(_('Emergency Contact Phone'), max_length=20, blank=True)
    notes = models.TextField(_('Notes'), blank=True)
    
    # معلومات النظام
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_employees', verbose_name=_('Created By'))

    class Meta:
        verbose_name = _('Employee')
        verbose_name_plural = _('Employees')
        ordering = ['first_name', 'last_name']
        permissions = [
            ("view_hr_menu", _("Can View HR Menu")),
            ("view_hr_employee", _("Can View Employees")),
            ("add_hr_employee", _("Can Add Employees")),
            ("change_hr_employee", _("Can Change Employees")),
            ("delete_hr_employee", _("Can Delete Employees")),
        ]

    def __str__(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name} ({self.employee_id})"
        elif self.first_name:
            return f"{self.first_name} ({self.employee_id})"
        elif self.last_name:
            return f"{self.last_name} ({self.employee_id})"
        else:
            return f"{_('Employee')} ({self.employee_id})"

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return f"{_('Employee')} {self.employee_id}"
    
    def get_full_name(self):
        """Method for compatibility with Django User model"""
        return self.full_name

    @property
    def full_name_en(self):
        if self.first_name_en and self.last_name_en:
            return f"{self.first_name_en} {self.last_name_en}"
        return self.full_name

    @property
    def total_salary(self):
        return self.basic_salary + self.allowances
    
    @property
    def withholding_tax_amount(self):
        """حساب قيمة الضريبة المقتطعة من الراتب الأساسي"""
        if self.withholding_tax_rate and self.basic_salary:
            return (self.basic_salary * self.withholding_tax_rate) / Decimal('100')
        return Decimal('0')
    
    @property
    def social_security_amount(self):
        """حساب قيمة الضمان الاجتماعي المترتبة على الموظف"""
        if self.social_security_rate and self.basic_salary:
            return (self.basic_salary * self.social_security_rate) / Decimal('100')
        return Decimal('0')
    
    @property
    def company_social_security_amount(self):
        """حساب قيمة الضمان الاجتماعي المترتبة على الشركة"""
        if self.company_social_security_rate and self.basic_salary:
            return (self.basic_salary * self.company_social_security_rate) / Decimal('100')
        return Decimal('0')
    
    @property
    def additional_deduction_amount(self):
        """حساب إجمالي قيمة الاقتطاعات الإضافية"""
        total = Decimal('0')
        for deduction in self.deductions.filter(is_active=True):
            total += deduction.calculated_amount
        return total
    
    @property
    def net_salary(self):
        """حساب صافي الراتب بعد جميع الاقتطاعات"""
        gross_salary = self.basic_salary + self.allowances
        total_deductions = self.withholding_tax_amount + self.social_security_amount + self.additional_deduction_amount
        return gross_salary - total_deductions
    
    @property
    def probation_end_date(self):
        """حساب تاريخ انتهاء فترة التجربة"""
        if self.probation_period_days and self.probation_period_days > 0:
            from datetime import timedelta
            return self.hire_date + timedelta(days=self.probation_period_days)
        return None
    
    @property
    def is_in_probation(self):
        """التحقق من أن الموظف في فترة التجربة"""
        if self.probation_end_date:
            from datetime import date
            return date.today() <= self.probation_end_date
        return False

    @property
    def current_contract(self):
        """العقد الحالي النشط للموظف"""
        return self.contracts.filter(status='active').first()

    @property
    def age(self):
        today = date.today()
        return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))

    def get_current_leave_balance(self):
        """حساب رصيد الإجازات الحالي"""
        from datetime import datetime
        current_year = datetime.now().year
        
        balance = {}
        for leave_type in LeaveType.objects.filter(is_active=True):
            used_leaves = self.leave_requests.filter(
                leave_type=leave_type,
                start_date__year=current_year,
                status='approved'
            ).aggregate(
                total_days=models.Sum('days_count')
            )['total_days'] or 0
            
            balance[leave_type.id] = leave_type.days_per_year - used_leaves
        
        return balance

class Contract(models.Model):
    """عقود الموظفين"""
    CONTRACT_TYPES = [
        ('permanent', _('Permanent')),
        ('temporary', _('Temporary')),
        ('probation', _('Probation')),
        ('renewal', _('Renewal')),
    ]

    STATUS_CHOICES = [
        ('active', _('Active')),
        ('expired', _('Expired')),
        ('terminated', _('Terminated')),
        ('draft', _('Draft')),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, 
                                related_name='contracts', verbose_name=_('Employee'))
    contract_number = models.CharField(_('Contract Number'), max_length=50, unique=True)
    contract_type = models.CharField(_('Contract Type'), max_length=20, choices=CONTRACT_TYPES)
    start_date = models.DateField(_('Start Date'))
    end_date = models.DateField(_('End Date'), null=True, blank=True)
    salary = models.DecimalField(_('Salary'), max_digits=10, decimal_places=3, 
                               validators=[MinValueValidator(Decimal('0'))])
    allowances = models.DecimalField(_('Allowances'), max_digits=10, decimal_places=3, 
                                   validators=[MinValueValidator(Decimal('0'))], default=0)
    working_hours_per_day = models.IntegerField(_('Working Hours Per Day'), default=8)
    working_days_per_week = models.IntegerField(_('Working Days Per Week'), default=5)
    annual_leave_days = models.IntegerField(_('Annual Leave Days'), default=21)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='draft')
    terms_and_conditions = models.TextField(_('Terms and Conditions'), blank=True)
    notes = models.TextField(_('Notes'), blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_contracts', verbose_name=_('Created By'))

    class Meta:
        verbose_name = _('Contract')
        verbose_name_plural = _('Contracts')
        ordering = ['-start_date']
        permissions = [
            ("view_hr_contract", _("Can View Contracts")),
            ("add_hr_contract", _("Can Add Contracts")),
            ("change_hr_contract", _("Can Change Contracts")),
            ("delete_hr_contract", _("Can Delete Contracts")),
        ]

    def __str__(self):
        return f"{self.contract_number} - {self.employee.full_name}"

class Attendance(models.Model):
    """الحضور والانصراف"""
    ATTENDANCE_TYPES = [
        ('present', _('Present')),
        ('absent', _('Absent')),
        ('late', _('Late')),
        ('half_day', _('Half Day')),
        ('on_leave', _('On Leave')),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, 
                                related_name='attendances', verbose_name=_('Employee'))
    date = models.DateField(_('Date'))
    check_in_time = models.TimeField(_('Check In Time'), null=True, blank=True)
    check_out_time = models.TimeField(_('Check Out Time'), null=True, blank=True)
    attendance_type = models.CharField(_('Attendance Type'), max_length=20, choices=ATTENDANCE_TYPES, default='present')
    worked_hours = models.DecimalField(_('Worked Hours'), max_digits=4, decimal_places=2, default=0)
    overtime_hours = models.DecimalField(_('Overtime Hours'), max_digits=4, decimal_places=2, default=0)
    notes = models.TextField(_('Notes'), blank=True)
    is_manual_entry = models.BooleanField(_('Manual Entry'), default=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_attendances', verbose_name=_('Created By'))

    class Meta:
        verbose_name = _('Attendance')
        verbose_name_plural = _('Attendances')
        ordering = ['-date', 'employee__first_name']
        unique_together = ['employee', 'date']
        permissions = [
            ("view_hr_attendance", _("Can View Attendance")),
            ("add_hr_attendance", _("Can Add Attendance")),
            ("change_hr_attendance", _("Can Change Attendance")),
            ("delete_hr_attendance", _("Can Delete Attendance")),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.date}"

    def save(self, *args, **kwargs):
        # حساب ساعات العمل تلقائياً
        if self.check_in_time and self.check_out_time:
            check_in_datetime = datetime.combine(self.date, self.check_in_time)
            check_out_datetime = datetime.combine(self.date, self.check_out_time)
            duration = check_out_datetime - check_in_datetime
            
            # إذا كان وقت الانصراف في اليوم التالي
            if check_out_datetime < check_in_datetime:
                check_out_datetime = datetime.combine(self.date.replace(day=self.date.day + 1), self.check_out_time)
                duration = check_out_datetime - check_in_datetime
            
            total_hours = duration.total_seconds() / 3600
            
            # حساب الساعات الإضافية (أكثر من 8 ساعات)
            if total_hours > 8:
                self.worked_hours = 8
                self.overtime_hours = total_hours - 8
            else:
                self.worked_hours = total_hours
                self.overtime_hours = 0
        
        super().save(*args, **kwargs)

class LeaveType(models.Model):
    """أنواع الإجازات"""
    name = models.CharField(_('Leave Type Name'), max_length=100)
    name_en = models.CharField(_('Leave Type Name (English)'), max_length=100, blank=True)
    code = models.CharField(_('Code'), max_length=20, unique=True)
    days_per_year = models.IntegerField(_('Days Per Year'), default=0)
    is_paid = models.BooleanField(_('Is Paid'), default=True)
    requires_approval = models.BooleanField(_('Requires Approval'), default=True)
    max_consecutive_days = models.IntegerField(_('Max Consecutive Days'), default=30)
    description = models.TextField(_('Description'), blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Leave Type')
        verbose_name_plural = _('Leave Types')
        ordering = ['name']
        permissions = [
            ("view_hr_leavetype", _("Can View Leave Types")),
            ("add_hr_leavetype", _("Can Add Leave Types")),
            ("change_hr_leavetype", _("Can Change Leave Types")),
            ("delete_hr_leavetype", _("Can Delete Leave Types")),
        ]

    def __str__(self):
        return self.name

class LeaveRequest(models.Model):
    """طلبات الإجازات"""
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('cancelled', _('Cancelled')),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, 
                                related_name='leave_requests', verbose_name=_('Employee'))
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, 
                                  related_name='leave_requests', verbose_name=_('Leave Type'))
    start_date = models.DateField(_('Start Date'))
    end_date = models.DateField(_('End Date'))
    days_count = models.IntegerField(_('Days Count'))
    reason = models.TextField(_('Reason'))
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='approved_leaves', verbose_name=_('Approved By'))
    approval_date = models.DateTimeField(_('Approval Date'), null=True, blank=True)
    rejection_reason = models.TextField(_('Rejection Reason'), blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_leave_requests', verbose_name=_('Created By'))

    class Meta:
        verbose_name = _('Leave Request')
        verbose_name_plural = _('Leave Requests')
        ordering = ['-created_at']
        permissions = [
            ("view_hr_leaverequest", _("Can View Leave Requests")),
            ("add_hr_leaverequest", _("Can Add Leave Requests")),
            ("change_hr_leaverequest", _("Can Change Leave Requests")),
            ("delete_hr_leaverequest", _("Can Delete Leave Requests")),
            ("approve_hr_leaverequest", _("Can Approve Leave Requests")),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.leave_type.name} ({self.start_date} to {self.end_date})"

    def save(self, *args, **kwargs):
        # حساب عدد الأيام تلقائياً
        if self.start_date and self.end_date:
            self.days_count = (self.end_date - self.start_date).days + 1
        super().save(*args, **kwargs)

class PayrollPeriod(models.Model):
    """فترات الرواتب"""
    name = models.CharField(_('Period Name'), max_length=100)
    start_date = models.DateField(_('Start Date'))
    end_date = models.DateField(_('End Date'))
    is_processed = models.BooleanField(_('Is Processed'), default=False)
    processed_date = models.DateTimeField(_('Processed Date'), null=True, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                    related_name='processed_payrolls', verbose_name=_('Processed By'))
    notes = models.TextField(_('Notes'), blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_payroll_periods', verbose_name=_('Created By'))

    class Meta:
        verbose_name = _('Payroll Period')
        verbose_name_plural = _('Payroll Periods')
        ordering = ['-start_date']
        permissions = [
            ("view_hr_payrollperiod", _("Can View Payroll Periods")),
            ("add_hr_payrollperiod", _("Can Add Payroll Periods")),
            ("change_hr_payrollperiod", _("Can Change Payroll Periods")),
            ("delete_hr_payrollperiod", _("Can Delete Payroll Periods")),
            ("process_hr_payrollperiod", _("Can Process Payroll Periods")),
        ]

    def __str__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"
    
    @property
    def total_gross_salary(self):
        """حساب إجمالي الرواتب الإجمالية للفترة"""
        return self.payroll_entries.aggregate(
            total=models.Sum('gross_salary')
        )['total'] or 0
    
    @property
    def total_net_salary(self):
        """حساب إجمالي الرواتب الصافية للفترة"""
        return self.payroll_entries.aggregate(
            total=models.Sum('net_salary')
        )['total'] or 0

class PayrollEntry(models.Model):
    """قيود الرواتب"""
    payroll_period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE, 
                                      related_name='payroll_entries', verbose_name=_('Payroll Period'))
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, 
                                related_name='payroll_entries', verbose_name=_('Employee'))
    
    # الراتب الأساسي والبدلات
    basic_salary = models.DecimalField(_('Basic Salary'), max_digits=10, decimal_places=3, default=0)
    allowances = models.DecimalField(_('Allowances'), max_digits=10, decimal_places=3, default=0)
    overtime_amount = models.DecimalField(_('Overtime Amount'), max_digits=10, decimal_places=3, default=0)
    bonuses = models.DecimalField(_('Bonuses'), max_digits=10, decimal_places=3, default=0)
    
    # الخصومات
    deductions = models.DecimalField(_('Deductions'), max_digits=10, decimal_places=3, default=0)
    social_security_deduction = models.DecimalField(_('Social Security Deduction'), max_digits=10, decimal_places=3, default=0)
    income_tax = models.DecimalField(_('Income Tax'), max_digits=10, decimal_places=3, default=0)
    unpaid_leave_deduction = models.DecimalField(_('Unpaid Leave Deduction'), max_digits=10, decimal_places=3, default=0)
    
    # الإجماليات
    gross_salary = models.DecimalField(_('Gross Salary'), max_digits=10, decimal_places=3, default=0)
    total_deductions = models.DecimalField(_('Total Deductions'), max_digits=10, decimal_places=3, default=0)
    net_salary = models.DecimalField(_('Net Salary'), max_digits=10, decimal_places=3, default=0)
    
    # ربط مع نظام المحاسبة
    journal_entry = models.ForeignKey('journal.JournalEntry', on_delete=models.SET_NULL, null=True, blank=True, 
                                     related_name='payroll_entries', verbose_name=_('Journal Entry'))
    
    # معلومات الدفع
    is_paid = models.BooleanField(_('Is Paid'), default=False)
    payment_date = models.DateField(_('Payment Date'), null=True, blank=True)
    payment_method = models.CharField(_('Payment Method'), max_length=50, blank=True)
    notes = models.TextField(_('Notes'), blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_payroll_entries', verbose_name=_('Created By'))

    class Meta:
        verbose_name = _('Payroll Entry')
        verbose_name_plural = _('Payroll Entries')
        ordering = ['-payroll_period__start_date', 'employee__first_name']
        unique_together = ['payroll_period', 'employee']
        permissions = [
            ("view_hr_payrollentry", _("Can View Payroll Entries")),
            ("add_hr_payrollentry", _("Can Add Payroll Entries")),
            ("change_hr_payrollentry", _("Can Change Payroll Entries")),
            ("delete_hr_payrollentry", _("Can Delete Payroll Entries")),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.payroll_period.name}"

    def save(self, *args, **kwargs):
        # إذا لم يكن payroll_period محدد، أنشئ واحد تلقائياً
        if not self.payroll_period_id:
            self.payroll_period = self.get_or_create_current_payroll_period()
        
        # حساب الإجماليات تلقائياً
        self.gross_salary = self.basic_salary + self.allowances + self.overtime_amount + self.bonuses
        self.total_deductions = self.deductions + self.social_security_deduction + self.income_tax + self.unpaid_leave_deduction
        self.net_salary = self.gross_salary - self.total_deductions
        super().save(*args, **kwargs)

    @classmethod
    def get_or_create_current_payroll_period(cls, user=None):
        """الحصول على فترة الرواتب الحالية أو إنشاء واحدة جديدة"""
        from calendar import monthrange
        from django.utils import timezone
        
        today = timezone.now().date()
        # بداية الشهر الحالي
        start_date = today.replace(day=1)
        # نهاية الشهر الحالي
        _, last_day = monthrange(today.year, today.month)
        end_date = today.replace(day=last_day)
        
        # البحث عن فترة موجودة
        existing_period = PayrollPeriod.objects.filter(
            start_date=start_date,
            end_date=end_date
        ).first()
        
        if existing_period:
            return existing_period
        
        # إنشاء فترة جديدة
        period_name = f"Payroll {today.strftime('%B %Y')}"
        if user:
            created_by = user
        else:
            # استخدم أول مستخدم superuser إذا لم يكن محدد
            from django.contrib.auth import get_user_model
            User = get_user_model()
            created_by = User.objects.filter(is_superuser=True).first()
            if not created_by:
                created_by = User.objects.filter(is_staff=True).first()
        
        if not created_by:
            raise ValueError(_('Cannot create payroll period without user'))
        
        new_period = PayrollPeriod.objects.create(
            name=period_name,
            start_date=start_date,
            end_date=end_date,
            created_by=created_by
        )
        
        return new_period

    def calculate_social_security(self):
        """حساب الضمان الاجتماعي"""
        if self.employee.social_security_number:
            return (self.basic_salary * self.employee.social_security_rate) / 100
        return 0

class EmployeeDocument(models.Model):
    """مستندات الموظفين"""
    DOCUMENT_TYPES = [
        ('contract', _('Contract')),
        ('id_copy', _('ID Copy')),
        ('certificate', _('Certificate')),
        ('resume', _('Resume')),
        ('photo', _('Photo')),
        ('other', _('Other')),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, 
                                related_name='documents', verbose_name=_('Employee'))
    document_type = models.CharField(_('Document Type'), max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    file = models.FileField(_('File'), upload_to='hr/documents/')
    upload_date = models.DateTimeField(_('Upload Date'), auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='uploaded_documents', verbose_name=_('Uploaded By'))

    class Meta:
        verbose_name = _('Employee Document')
        verbose_name_plural = _('Employee Documents')
        ordering = ['-upload_date']
        permissions = [
            ("view_hr_employeedocument", _("Can View Employee Documents")),
            ("add_hr_employeedocument", _("Can Add Employee Documents")),
            ("change_hr_employeedocument", _("Can Change Employee Documents")),
            ("delete_hr_employeedocument", _("Can Delete Employee Documents")),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.title}"


class EmployeeDeduction(models.Model):
    """اقتطاعات الموظفين الإضافية"""
    DEDUCTION_TYPE_CHOICES = [
        ('percentage', _('Percentage')),
        ('fixed', _('Fixed Amount')),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE,
                                related_name='deductions', verbose_name=_('Employee'))
    name = models.CharField(_('Deduction Name'), max_length=200)
    deduction_type = models.CharField(_('Deduction Type'), max_length=20,
                                     choices=DEDUCTION_TYPE_CHOICES, default='fixed')
    value = models.DecimalField(_('Deduction Value'), max_digits=10, decimal_places=3,
                               validators=[MinValueValidator(Decimal('0'))], default=0)
    notes = models.TextField(_('Deduction Notes'), blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT,
                                  related_name='created_deductions', verbose_name=_('Created By'))
    
    class Meta:
        verbose_name = _('Employee Deduction')
        verbose_name_plural = _('Employee Deductions')
        ordering = ['employee', '-created_at']
        permissions = [
            ("view_hr_employeededuction", _("Can View Employee Deductions")),
            ("add_hr_employeededuction", _("Can Add Employee Deductions")),
            ("change_hr_employeededuction", _("Can Change Employee Deductions")),
            ("delete_hr_employeededuction", _("Can Delete Employee Deductions")),
        ]
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.name}"
    
    @property
    def calculated_amount(self):
        """حساب قيمة الاقتطاع"""
        if not self.is_active:
            return Decimal('0')
        
        if self.deduction_type == 'percentage':
            return (self.employee.basic_salary * self.value) / Decimal('100')
        else:
            return self.value
