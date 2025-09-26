from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.urls import reverse
from datetime import date, datetime
from decimal import Decimal

from .models import RevenueExpenseCategory, RevenueExpenseEntry, RecurringRevenueExpense
from .forms import RevenueExpenseCategoryForm, RevenueExpenseEntryForm, RecurringRevenueExpenseForm
from settings.models import CompanySettings

@login_required
def category_edit(request, category_id):
    """تعديل فئة إيراد/مصروف"""
    category = get_object_or_404(RevenueExpenseCategory, id=category_id)
    # حماية الوصول حسب الصلاحية
    if not request.user.is_admin and not request.user.has_perm('revenues_expenses.change_revenueexpensecategory'):
        messages.error(request, _('ليس لديك صلاحية تعديل فئة إيراد/مصروف'))
        return redirect('revenues_expenses:category_list')
    if request.method == 'POST':
        form = RevenueExpenseCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تعديل الفئة بنجاح'))
            return redirect('revenues_expenses:category_list')
        else:
            messages.error(request, _('يرجى تصحيح الأخطاء في النموذج'))
    else:
        form = RevenueExpenseCategoryForm(instance=category)
    context = {
        'form': form,
        'category': category,
        'page_title': _('تعديل فئة إيراد/مصروف'),
    }
    return render(request, 'revenues_expenses/category_edit.html', context)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.urls import reverse
from datetime import date, datetime
from decimal import Decimal

from .models import RevenueExpenseCategory, RevenueExpenseEntry, RecurringRevenueExpense
from .forms import RevenueExpenseCategoryForm, RevenueExpenseEntryForm, RecurringRevenueExpenseForm
from settings.models import CompanySettings


def create_journal_entry_for_revenue_expense(entry, user):
    """إنشاء قيد محاسبي لقيد الإيرادات/المصروفات"""
    from journal.models import JournalEntry, JournalLine, Account
    
    # البحث عن الحسابات المناسبة
    if entry.type == 'revenue':
        # للإيرادات: نقدية مدين، إيرادات دائن
        if entry.payment_method == 'cash':
            debit_account = Account.objects.filter(code='1101').first()  # الصندوق
        elif entry.payment_method == 'bank':
            debit_account = Account.objects.filter(code='1102').first()  # البنك
        else:
            debit_account = Account.objects.filter(code='1101').first()  # افتراضي صندوق
            
        # حساب الإيرادات حسب الفئة
        if 'مبيعات' in entry.category.name:
            credit_account = Account.objects.filter(code='4001').first()  # إيرادات المبيعات
        elif 'خدمات' in entry.category.name:
            credit_account = Account.objects.filter(code='4002').first()  # إيرادات الخدمات
        else:
            credit_account = Account.objects.filter(code='4999').first()  # إيرادات أخرى
        
    else:  # expense
        # للمصروفات: مصروفات مدين، نقدية دائن
        # حساب المصروفات حسب الفئة
        if 'إدارية' in entry.category.name:
            debit_account = Account.objects.filter(code='5001').first()  # مصروفات إدارية
        elif 'تشغيل' in entry.category.name:
            debit_account = Account.objects.filter(code='5002').first()  # مصروفات تشغيلية
        elif 'رواتب' in entry.category.name:
            debit_account = Account.objects.filter(code='5003').first()  # الرواتب والأجور
        elif 'إيجار' in entry.category.name:
            debit_account = Account.objects.filter(code='5004').first()  # الإيجارات
        elif 'مرافق' in entry.category.name:
            debit_account = Account.objects.filter(code='5005').first()  # المرافق
        else:
            debit_account = Account.objects.filter(code='5999').first()  # مصروفات أخرى
        
        if entry.payment_method == 'cash':
            credit_account = Account.objects.filter(code='1101').first()  # الصندوق
        elif entry.payment_method == 'bank':
            credit_account = Account.objects.filter(code='1102').first()  # البنك
        else:
            credit_account = Account.objects.filter(code='1101').first()  # افتراضي صندوق
    
    if not debit_account or not credit_account:
        raise Exception(_('لم يتم العثور على الحسابات المحاسبية المناسبة'))
    
    # إنشاء القيد المحاسبي
    journal_entry = JournalEntry.objects.create(
        entry_date=entry.date,
        description=f'{entry.get_type_display()} - {entry.category.name} - {entry.description}',
        reference_type='revenue_expense',
        reference_id=entry.id,
        total_amount=entry.amount,
        created_by=user
    )
    
    # إنشاء بنود القيد
    JournalLine.objects.create(
        journal_entry=journal_entry,
        account=debit_account,
        debit=entry.amount,
        credit=Decimal('0'),
        line_description=f'{entry.get_type_display()} - {entry.category.name}'
    )
    
    JournalLine.objects.create(
        journal_entry=journal_entry,
        account=credit_account,
        debit=Decimal('0'),
        credit=entry.amount,
        line_description=f'{entry.get_type_display()} - {entry.category.name}'
    )
    
    return journal_entry


@login_required
def revenue_expense_dashboard(request):
    """{% trans "Revenues and Expenses Dashboard" %}"""
    # الحصول على العملة الأساسية
    company_settings = CompanySettings.objects.first()
    base_currency = company_settings.base_currency if company_settings else None
    
    # الإحصائيات الشهرية
    current_month = date.today().month
    current_year = date.today().year
    
    monthly_revenues = RevenueExpenseEntry.objects.filter(
        type='revenue',
        date__month=current_month,
        date__year=current_year,
        is_approved=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    monthly_expenses = RevenueExpenseEntry.objects.filter(
        type='expense',
        date__month=current_month,
        date__year=current_year,
        is_approved=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # الإحصائيات السنوية
    yearly_revenues = RevenueExpenseEntry.objects.filter(
        type='revenue',
        date__year=current_year,
        is_approved=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    yearly_expenses = RevenueExpenseEntry.objects.filter(
        type='expense',
        date__year=current_year,
        is_approved=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # آخر العمليات
    recent_entries = RevenueExpenseEntry.objects.select_related('category', 'created_by', 'currency').order_by('-created_at')[:10]
    
    # العمليات المتكررة المستحقة
    pending_recurring = RecurringRevenueExpense.objects.filter(
        is_active=True,
        next_due_date__lte=date.today()
    ).select_related('category', 'currency').order_by('next_due_date')[:5]
    
    context = {
        'page_title': _('Revenues and Expenses Dashboard'),
        'monthly_revenues': monthly_revenues,
        'monthly_expenses': monthly_expenses,
        'monthly_net': monthly_revenues - monthly_expenses,
        'yearly_revenues': yearly_revenues,
        'yearly_expenses': yearly_expenses,
        'yearly_net': yearly_revenues - yearly_expenses,
        'recent_entries': recent_entries,
        'pending_recurring': pending_recurring,
        'base_currency': base_currency,
    }
    
    return render(request, 'revenues_expenses/dashboard.html', context)


@login_required
def category_list(request):
    """{% trans "Revenue/Expense Categories List" %}"""
    # حماية الوصول حسب الصلاحية (دالة مخصصة)
    if not request.user.has_revenueexpensecategory_view_permission():
        messages.error(request, _('ليس لديك صلاحية عرض فئة إيراد/مصروف'))
        return redirect('revenues_expenses:dashboard')
    categories = RevenueExpenseCategory.objects.filter(is_active=True).select_related('created_by')
    # التصفية
    category_type = request.GET.get('type')
    if category_type:
        categories = categories.filter(type=category_type)
    search = request.GET.get('search')
    if search:
        categories = categories.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    # الترقيم
    paginator = Paginator(categories, 25)
    page_number = request.GET.get('page')
    categories = paginator.get_page(page_number)
    context = {
        'page_title': _('فئات الإيرادات والمصروفات'),
        'categories': categories,
        'category_types': RevenueExpenseCategory.CATEGORY_TYPES,
    }
    return render(request, 'revenues_expenses/category_list.html', context)


@login_required
def category_create(request):
    """{% trans "Add New Category" %}"""
    # حماية الوصول حسب الصلاحية
    if not request.user.is_admin and not request.user.has_revenueexpensecategory_add_permission():
        messages.error(request, _('ليس لديك صلاحية إضافة فئة إيراد/مصروف'))
        return redirect('revenues_expenses:category_list')
    if request.method == 'POST':
        form = RevenueExpenseCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            category.save()
            messages.success(request, _('تم إنشاء الفئة بنجاح'))
            return redirect('revenues_expenses:category_list')
        else:
            messages.error(request, _('يرجى تصحيح الأخطاء في النموذج'))
    else:
        form = RevenueExpenseCategoryForm()
    context = {
        'form': form,
        'page_title': _('Add New Category'),
    }
    return render(request, 'revenues_expenses/category_create.html', context)


@login_required
def category_delete(request, category_id):
    """{% trans "Delete Revenue/Expense Category" %}"""
    category = get_object_or_404(RevenueExpenseCategory, id=category_id)
    # حماية الوصول حسب الصلاحية
    if not request.user.is_admin and not request.user.has_perm('revenues_expenses.delete_revenueexpensecategory'):
        messages.error(request, _('ليس لديك صلاحية حذف فئة إيراد/مصروف'))
        return redirect('revenues_expenses:category_list')
    if request.method == 'POST':
        category.is_active = False
        category.save()
        messages.success(request, _('تم حذف الفئة بنجاح'))
        return redirect('revenues_expenses:category_list')
    context = {
        'category': category,
        'page_title': _('تأكيد حذف الفئة'),
    }
    return render(request, 'revenues_expenses/category_confirm_delete.html', context)


@login_required
def entry_create(request):
    """{% trans "Add New Entry" %}"""
    # حماية الوصول حسب الصلاحية
    if not request.user.is_admin and not request.user.has_revenueexpenseentry_add_permission():
        messages.error(request, _('ليس لديك صلاحية إضافة قيد إيراد/مصروف'))
        return redirect('revenues_expenses:entry_list')
    if request.method == 'POST':
        form = RevenueExpenseEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.created_by = request.user
            entry.save()
            messages.success(request, _('تم إنشاء القيد بنجاح'))
            return redirect('revenues_expenses:entry_detail', entry_id=entry.id)
        else:
            messages.error(request, _('يرجى تصحيح الأخطاء في النموذج'))
    else:
        form = RevenueExpenseEntryForm()
    context = {
        'form': form,
        'page_title': _('Add New Entry'),
    }
    return render(request, 'revenues_expenses/entry_create.html', context)


@login_required
def entry_delete(request, entry_id):
    """حذف قيد الإيراد/المصروف"""
    entry = get_object_or_404(RevenueExpenseEntry, id=entry_id)
    if not request.user.is_admin and not request.user.has_perm('revenues_expenses.delete_revenueexpenseentry'):
        messages.error(request, _('ليس لديك صلاحية حذف قيد إيراد/مصروف'))
        return redirect('revenues_expenses:entry_list')
    if request.method == 'POST':
        entry.delete()
        messages.success(request, _('تم حذف القيد بنجاح'))
        return redirect('revenues_expenses:entry_list')
    context = {
        'entry': entry,
        'page_title': _('تأكيد حذف القيد'),
    }
    return render(request, 'revenues_expenses/entry_confirm_delete.html', context)


@login_required
def entry_edit(request, entry_id):
    """تعديل قيد الإيراد/المصروف"""
    entry = get_object_or_404(RevenueExpenseEntry, id=entry_id)
    if not request.user.is_admin and not request.user.has_perm('revenues_expenses.change_revenueexpenseentry'):
        messages.error(request, _('ليس لديك صلاحية تعديل قيد إيراد/مصروف'))
        return redirect('revenues_expenses:entry_list')
    if request.method == 'POST':
        form = RevenueExpenseEntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, _('تم تعديل القيد بنجاح'))
            return redirect('revenues_expenses:entry_detail', entry_id=entry.id)
        else:
            messages.error(request, _('يرجى تصحيح الأخطاء في النموذج'))
    else:
        form = RevenueExpenseEntryForm(instance=entry)
    context = {
        'form': form,
        'entry': entry,
        'page_title': _('تعديل قيد إيراد/مصروف'),
    }
    return render(request, 'revenues_expenses/entry_edit.html', context)


@login_required
def entry_detail(request, entry_id):
    """تفاصيل القيد"""
    entry = get_object_or_404(RevenueExpenseEntry.objects.select_related('category', 'created_by', 'approved_by', 'currency'), id=entry_id)
    context = {
        'entry': entry,
        'page_title': f'{_("تفاصيل القيد")} - {entry.entry_number}',
    }
    return render(request, 'revenues_expenses/entry_detail.html', context)


@login_required
def entry_approve(request, entry_id):
    """اعتماد القيد"""
    entry = get_object_or_404(RevenueExpenseEntry, id=entry_id)
    if not entry.is_approved:
        entry.is_approved = True
        entry.approved_by = request.user
        entry.approved_at = datetime.now()
        entry.save()
        messages.success(request, _('تم اعتماد القيد بنجاح'))
    return redirect('revenues_expenses:entry_detail', entry_id=entry.id)


@login_required
def recurring_list(request):
    """قائمة الإيرادات والمصروفات المتكررة"""
    recurring_items = RecurringRevenueExpense.objects.select_related(
        'category', 'created_by', 'currency'
    ).order_by('-created_at')
    
    # التصفية
    category_type = request.GET.get('type')
    if category_type:
        recurring_items = recurring_items.filter(category__type=category_type)
    
    category = request.GET.get('category')
    if category:
        recurring_items = recurring_items.filter(category_id=category)
    
    frequency = request.GET.get('frequency')
    if frequency:
        recurring_items = recurring_items.filter(frequency=frequency)
    
    status = request.GET.get('status')
    if status == 'active':
        recurring_items = recurring_items.filter(is_active=True)
    elif status == 'inactive':
        recurring_items = recurring_items.filter(is_active=False)
    
    search = request.GET.get('search')
    if search:
        recurring_items = recurring_items.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # الترقيم
    paginator = Paginator(recurring_items, 25)
    page_number = request.GET.get('page')
    recurring_items = paginator.get_page(page_number)
    
    # البيانات للتصفية
    categories = RevenueExpenseCategory.objects.filter(is_active=True).order_by('name')
    
    # إحصائيات
    total_recurring = RecurringRevenueExpense.objects.filter(is_active=True).count()
    overdue_count = RecurringRevenueExpense.objects.filter(
        is_active=True,
        next_due_date__lt=date.today()
    ).count()
    due_today_count = RecurringRevenueExpense.objects.filter(
        is_active=True,
        next_due_date=date.today()
    ).count()
    
    context = {
        'page_title': _('Recurring revenues and expenses'),
        'recurring_items': recurring_items,
        'categories': categories,
        'frequency_choices': RecurringRevenueExpense.FREQUENCY_CHOICES,
        'entry_types': RevenueExpenseCategory.CATEGORY_TYPES,
        'total_recurring': total_recurring,
        'overdue_count': overdue_count,
        'due_today_count': due_today_count,
    }
    return render(request, 'revenues_expenses/recurring_list.html', context)


@login_required
def recurring_create(request):
    """إضافة إيراد/مصروف متكرر"""
    if request.method == 'POST':
        form = RecurringRevenueExpenseForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                recurring = form.save(commit=False)
                recurring.created_by = request.user
                
                # حساب التاريخ المستحق التالي
                from dateutil.relativedelta import relativedelta
                start_date = recurring.start_date
                
                if recurring.frequency == 'daily':
                    recurring.next_due_date = start_date
                elif recurring.frequency == 'weekly':
                    recurring.next_due_date = start_date
                elif recurring.frequency == 'monthly':
                    recurring.next_due_date = start_date
                elif recurring.frequency == 'quarterly':
                    recurring.next_due_date = start_date
                elif recurring.frequency == 'semi_annual':
                    recurring.next_due_date = start_date
                elif recurring.frequency == 'annual':
                    recurring.next_due_date = start_date
                else:
                    recurring.next_due_date = start_date
                
                recurring.save()
                
                # تسجيل النشاط
                from core.signals import log_activity
                log_activity(
                    action_type='create',
                    obj=recurring,
                    description=f'إضافة إيراد/مصروف متكرر جديد: {recurring.name}',
                    user=request.user
                )
                
                messages.success(request, _('تم إنشاء الإيراد/المصروف المتكرر بنجاح'))
                return redirect('revenues_expenses:recurring_list')
        else:
            messages.error(request, _('يرجى تصحيح الأخطاء في النموذج'))
    else:
        form = RecurringRevenueExpenseForm()
    
    context = {
        'form': form,
        'page_title': _('إضافة إيراد/مصروف متكرر'),
    }
    return render(request, 'revenues_expenses/recurring_create.html', context)


@login_required
def recurring_detail(request, recurring_id):
    """تفاصيل الإيراد/المصروف المتكرر"""
    recurring = get_object_or_404(RecurringRevenueExpense, id=recurring_id)
    
    # الحصول على القيود المولدة من هذا المتكرر
    generated_entries = RevenueExpenseEntry.objects.filter(
        description__icontains=f"متكرر #{recurring.id}"
    ).order_by('-date')
    
    context = {
        'page_title': f'{recurring.name} - {_("تفاصيل الإيراد/المصروف المتكرر")}',
        'recurring': recurring,
        'generated_entries': generated_entries,
    }
    return render(request, 'revenues_expenses/recurring_detail.html', context)


@login_required
def recurring_edit(request, recurring_id):
    """تعديل الإيراد/المصروف المتكرر"""
    recurring = get_object_or_404(RecurringRevenueExpense, id=recurring_id)
    
    if request.method == 'POST':
        form = RecurringRevenueExpenseForm(request.POST, instance=recurring)
        if form.is_valid():
            with transaction.atomic():
                updated_recurring = form.save()
                
                # تسجيل النشاط
                from core.signals import log_activity
                log_activity(
                    action_type='update',
                    obj=updated_recurring,
                    description=f'تعديل الإيراد/المصروف المتكرر: {updated_recurring.name}',
                    user=request.user
                )
                
                messages.success(request, _('تم تحديث الإيراد/المصروف المتكرر بنجاح'))
                return redirect('revenues_expenses:recurring_detail', recurring_id=recurring.id)
        else:
            messages.error(request, _('يرجى تصحيح الأخطاء في النموذج'))
    else:
        form = RecurringRevenueExpenseForm(instance=recurring)
    
    context = {
        'form': form,
        'recurring': recurring,
        'page_title': f'{recurring.name} - {_("تعديل الإيراد/المصروف المتكرر")}',
    }
    return render(request, 'revenues_expenses/recurring_edit.html', context)


@login_required
def recurring_delete(request, recurring_id):
    """حذف الإيراد/المصروف المتكرر"""
    recurring = get_object_or_404(RecurringRevenueExpense, id=recurring_id)
    
    if request.method == 'POST':
        with transaction.atomic():
            recurring_name = recurring.name
            
            # تسجيل النشاط قبل الحذف
            from core.signals import log_activity
            log_activity(
                action_type='delete',
                obj=None,
                description=f'حذف الإيراد/المصروف المتكرر: {recurring_name}',
                user=request.user
            )
            
            recurring.delete()
            
            messages.success(request, f'تم حذف الإيراد/المصروف المتكرر "{recurring_name}" بنجاح')
            return redirect('revenues_expenses:recurring_list')
    
    return redirect('revenues_expenses:recurring_detail', recurring_id=recurring_id)


@login_required
def recurring_toggle_status(request, recurring_id):
    """تفعيل/إلغاء تفعيل الإيراد/المصروف المتكرر"""
    recurring = get_object_or_404(RecurringRevenueExpense, id=recurring_id)
    
    if request.method == 'POST':
        with transaction.atomic():
            recurring.is_active = not recurring.is_active
            recurring.save()
            
            status_text = 'تفعيل' if recurring.is_active else 'إلغاء تفعيل'
            
            # تسجيل النشاط
            from core.signals import log_activity
            log_activity(
                action_type='update',
                obj=recurring,
                description=f'{status_text} الإيراد/المصروف المتكرر: {recurring.name}',
                user=request.user
            )
            
            messages.success(request, f'تم {status_text} الإيراد/المصروف المتكرر بنجاح')
    
    return redirect('revenues_expenses:recurring_detail', recurring_id=recurring_id)


@login_required
def recurring_generate_entry(request, recurring_id):
    """توليد قيد من الإيراد/المصروف المتكرر يدوياً"""
    recurring = get_object_or_404(RecurringRevenueExpense, id=recurring_id)
    
    if request.method == 'POST':
        with transaction.atomic():
            # إنشاء قيد جديد من المتكرر
            entry = RevenueExpenseEntry.objects.create(
                type=recurring.category.type,
                category=recurring.category,
                amount=recurring.amount,
                currency=recurring.currency,
                description=f"{recurring.description}\n(مولد من متكرر #{recurring.id}: {recurring.name})",
                payment_method=recurring.payment_method,
                date=date.today(),
                created_by=request.user
            )
            
            # تحديث آخر تاريخ توليد
            recurring.last_generated = date.today()
            
            # حساب التاريخ المستحق التالي
            from dateutil.relativedelta import relativedelta
            
            if recurring.frequency == 'daily':
                recurring.next_due_date = recurring.next_due_date + relativedelta(days=1)
            elif recurring.frequency == 'weekly':
                recurring.next_due_date = recurring.next_due_date + relativedelta(weeks=1)
            elif recurring.frequency == 'monthly':
                recurring.next_due_date = recurring.next_due_date + relativedelta(months=1)
            elif recurring.frequency == 'quarterly':
                recurring.next_due_date = recurring.next_due_date + relativedelta(months=3)
            elif recurring.frequency == 'semi_annual':
                recurring.next_due_date = recurring.next_due_date + relativedelta(months=6)
            elif recurring.frequency == 'annual':
                recurring.next_due_date = recurring.next_due_date + relativedelta(years=1)
            
            recurring.save()
            
            # تسجيل النشاط
            from core.signals import log_activity
            log_activity(
                action_type='create',
                obj=entry,
                description=f'توليد قيد من المتكرر: {recurring.name} - رقم القيد: {entry.entry_number}',
                user=request.user
            )
            
            messages.success(request, f'تم توليد القيد {entry.entry_number} من الإيراد/المصروف المتكرر بنجاح')
            return redirect('revenues_expenses:entry_detail', entry_id=entry.id)
    
    return redirect('revenues_expenses:recurring_detail', recurring_id=recurring_id)


@login_required
def entry_detail(request, entry_id):
    """تفاصيل قيد الإيرادات/المصروفات"""
    entry = get_object_or_404(RevenueExpenseEntry, id=entry_id)
    
    context = {
        'page_title': f'{entry.entry_number} - {_("تفاصيل القيد")}',
        'entry': entry,
    }
    return render(request, 'revenues_expenses/entry_detail.html', context)


@login_required
def entry_create(request):
    """إضافة قيد إيرادات/مصروفات"""
    if request.method == 'POST':
        form = RevenueExpenseEntryForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                entry = form.save(commit=False)
                entry.created_by = request.user
                
                # معالجة الخيارات الإضافية
                auto_approve = request.POST.get('auto_approve') == 'true'
                create_journal = request.POST.get('create_journal') == 'true'
                
                entry.save()
                
                # الاعتماد التلقائي إذا تم تحديده
                if auto_approve:
                    entry.is_approved = True
                    entry.approved_by = request.user
                    entry.approved_at = datetime.now()
                    entry.save()
                
                # إنشاء القيد المحاسبي إذا تم تحديده
                if create_journal:
                    try:
                        journal_entry = create_journal_entry_for_revenue_expense(entry, request.user)
                        messages.info(request, f'تم إنشاء القيد المحاسبي رقم {journal_entry.entry_number}')
                    except Exception as e:
                        messages.warning(request, f'تم إنشاء القيد بنجاح لكن فشل في إنشاء القيد المحاسبي: {str(e)}')
                
                # تسجيل النشاط
                from core.signals import log_activity
                log_activity(
                    action_type='create',
                    obj=entry,
                    description=f'إضافة قيد {entry.get_type_display()} جديد: {entry.entry_number} - {entry.description[:50]}',
                    user=request.user
                )
                
                success_message = f'تم إنشاء القيد {entry.entry_number} بنجاح. المبلغ: {entry.amount:,.3f} {entry.currency.code if entry.currency else ""}'
                if auto_approve:
                    success_message += ' (معتمد تلقائياً)'
                
                messages.success(request, success_message)
                return redirect('revenues_expenses:entry_detail', entry_id=entry.id)
        else:
            # إضافة رسائل خطأ مفصلة
            for field, errors in form.errors.items():
                for error in errors:
                    field_label = form.fields[field].label if field in form.fields else field
                    messages.error(request, f'{field_label}: {error}')
    else:
        form = RevenueExpenseEntryForm()
        # تعيين التاريخ الحالي كافتراضي
        from datetime import date
        form.fields['date'].initial = date.today()
    
    # إحضار الإحصائيات للعرض
    from django.db.models import Sum
    from datetime import date
    today = date.today()
    
    today_revenues = RevenueExpenseEntry.objects.filter(
        type='revenue',
        date=today,
        is_approved=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    today_expenses = RevenueExpenseEntry.objects.filter(
        type='expense', 
        date=today,
        is_approved=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # إحضار الفئات النشطة للجافا سكريبت
    revenue_categories = RevenueExpenseCategory.objects.filter(
        type='revenue', is_active=True
    ).values('id', 'name').order_by('name')
    
    expense_categories = RevenueExpenseCategory.objects.filter(
        type='expense', is_active=True
    ).values('id', 'name').order_by('name')
    
    context = {
        'form': form,
        'page_title': _('إضافة قيد إيرادات/مصروفات'),
        'today_revenues': today_revenues,
        'today_expenses': today_expenses,
        'revenue_categories': list(revenue_categories),
        'expense_categories': list(expense_categories),
    }
    return render(request, 'revenues_expenses/entry_create.html', context)


@login_required
def get_categories_by_type(request, entry_type):
    """API لجلب الفئات حسب النوع"""
    categories = RevenueExpenseCategory.objects.filter(
        type=entry_type, 
        is_active=True
    ).values('id', 'name').order_by('name')
    
    return JsonResponse({
        'categories': list(categories)
    })


@login_required
def get_today_stats(request):
    """API لجلب إحصائيات اليوم"""
    from django.db.models import Sum
    from datetime import date
    today = date.today()
    
    revenues = RevenueExpenseEntry.objects.filter(
        type='revenue',
        date=today,
        is_approved=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    expenses = RevenueExpenseEntry.objects.filter(
        type='expense',
        date=today,
        is_approved=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    return JsonResponse({
        'revenues': f"{revenues:,.2f}",
        'expenses': f"{expenses:,.2f}",
        'net': f"{revenues - expenses:,.2f}"
    })


@login_required
def entry_approve(request, entry_id):
    """اعتماد قيد الإيرادات/المصروفات"""
    entry = get_object_or_404(RevenueExpenseEntry, id=entry_id)
    
    if request.method == 'POST':
        with transaction.atomic():
            entry.is_approved = True
            entry.approved_by = request.user
            entry.approved_at = datetime.now()
            entry.save()
            
            # تسجيل النشاط
            from core.signals import log_activity
            log_activity(
                action_type='approve',
                obj=entry,
                description=f'اعتماد قيد {entry.get_type_display()}: {entry.entry_number}',
                user=request.user
            )
            
            messages.success(request, f'تم اعتماد القيد {entry.entry_number} بنجاح')
    
    return redirect('revenues_expenses:entry_detail', entry_id=entry_id)


@login_required
def entry_list(request):
    # حماية الوصول حسب الصلاحية
    if not request.user.is_admin and not request.user.has_revenueexpenseentry_view_permission():
        messages.error(request, _('ليس لديك صلاحية عرض قيد إيراد/مصروف'))
        return redirect('revenues_expenses:dashboard')
    """قائمة قيود الإيرادات والمصروفات"""
    entries = RevenueExpenseEntry.objects.select_related(
        'category', 'created_by', 'approved_by', 'currency'
    ).order_by('-date', '-created_at')
    
    # التصفية
    entry_type = request.GET.get('type')
    if entry_type:
        entries = entries.filter(type=entry_type)
    
    category = request.GET.get('category')
    if category:
        entries = entries.filter(category_id=category)
    
    status = request.GET.get('status')
    if status == 'approved':
        entries = entries.filter(is_approved=True)
    elif status == 'pending':
        entries = entries.filter(is_approved=False)
    
    search = request.GET.get('search')
    if search:
        entries = entries.filter(
            Q(entry_number__icontains=search) |
            Q(description__icontains=search) |
            Q(reference_number__icontains=search)
        )
    
    # الترقيم
    paginator = Paginator(entries, 25)
    page_number = request.GET.get('page')
    entries = paginator.get_page(page_number)
    
    # فئات للتصفية
    categories = RevenueExpenseCategory.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page_title': _('قيود الإيرادات والمصروفات'),
        'entries': entries,
        'categories': categories,
        'entry_types': RevenueExpenseEntry.ENTRY_TYPES,
    }
    
    return render(request, 'revenues_expenses/entry_list.html', context)


@login_required
def sector_analysis(request):
    """تحليل الإيرادات والمصاريف حسب القطاع"""
    user = request.user
    has_perm = (
        getattr(user, 'is_superuser', False) or
        getattr(user, 'user_type', None) in ['superadmin', 'admin'] or
        user.has_revenues_expenses_permission()
    )
    if not has_perm:
        messages.error(request, _('ليس لديك صلاحية عرض تحليل القطاعات'))
        return redirect('revenues_expenses:dashboard')

    from datetime import date, timedelta
    from .models import Sector

    # فلاتر التاريخ
    today = date.today()
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    sector_filter = request.GET.get('sector')

    if not start_date:
        start_date = today.replace(day=1)  # بداية الشهر الحالي
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    if not end_date:
        end_date = today
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    # تحليل حسب القطاع
    sectors = Sector.objects.filter(is_active=True)
    if sector_filter:
        sectors = sectors.filter(id=sector_filter)

    analysis_data = []
    total_revenue = Decimal('0')
    total_expense = Decimal('0')

    for sector in sectors:
        # إيرادات القطاع
        sector_revenue = RevenueExpenseEntry.objects.filter(
            sector=sector,
            type='revenue',
            date__gte=start_date,
            date__lte=end_date,
            is_approved=True
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # مصاريف القطاع
        sector_expense = RevenueExpenseEntry.objects.filter(
            sector=sector,
            type='expense',
            date__gte=start_date,
            date__lte=end_date,
            is_approved=True
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # صافي الربح للقطاع
        sector_profit = sector_revenue - sector_expense

        analysis_data.append({
            'sector': sector,
            'revenue': sector_revenue,
            'expense': sector_expense,
            'profit': sector_profit,
        })

        total_revenue += sector_revenue
        total_expense += sector_expense

    total_profit = total_revenue - total_expense

    # تسجيل النشاط
    try:
        from core.signals import log_view_activity
        class ReportObj:
            id = 0
            pk = 0
            def __str__(self):
                return str(_('تحليل الإيرادات والمصاريف حسب القطاع'))
        log_view_activity(request, 'view', ReportObj(), str(_('عرض تحليل القطاعات')))
    except Exception:
        pass

    context = {
        'page_title': _('تحليل الإيرادات والمصاريف حسب القطاع'),
        'analysis_data': analysis_data,
        'start_date': start_date,
        'end_date': end_date,
        'sector_filter': sector_filter,
        'total_revenue': total_revenue,
        'total_expense': total_expense,
        'total_profit': total_profit,
        'sectors': Sector.objects.filter(is_active=True),
    }

    return render(request, 'revenues_expenses/sector_analysis.html', context)
