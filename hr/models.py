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
    termination_date = models.DateField(_('Termination Date'), null=True, blank=True)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='active')
    
    # معلومات الراتب
    basic_salary = models.DecimalField(_('Basic Salary'), max_digits=10, decimal_places=3, 
                                     validators=[MinValueValidator(Decimal('0'))], default=0)
    allowances = models.DecimalField(_('Allowances'), max_digits=10, decimal_places=3, 
                                   validators=[MinValueValidator(Decimal('0'))], default=0)
    
    # معلومات الضمان الاجتماعي
    social_security_number = models.CharField(_('Social Security Number'), max_length=20, blank=True)
    social_security_rate = models.DecimalField(_('Social Security Rate %'), max_digits=5, decimal_places=2, 
                                             validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))], 
                                             default=Decimal('7.5'))
    
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
            ("can_view_hr", "Can View HR"),
            ("can_manage_employees", "Can Manage Employees"),
            ("can_manage_attendance", "Can Manage Attendance"),
            ("can_manage_payroll", "Can Manage Payroll"),
            ("can_approve_leaves", "Can Approve Leaves"),
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

    @property
    def full_name_en(self):
        if self.first_name_en and self.last_name_en:
            return f"{self.first_name_en} {self.last_name_en}"
        return self.full_name

    @property
    def total_salary(self):
        return self.basic_salary + self.allowances

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
        annual_leave_days = 21  # يمكن جعلها قابلة للتخصيص
        
        used_leaves = self.leave_requests.filter(
            start_date__year=current_year,
            status='approved'
        ).aggregate(
            total_days=models.Sum('days_count')
        )['total_days'] or 0
        
        return annual_leave_days - used_leaves

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

    def __str__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"

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

    def __str__(self):
        return f"{self.employee.full_name} - {self.title}"
