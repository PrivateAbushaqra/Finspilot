from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.db.models import Q, Sum, Count
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from .models import CustomerSupplier
from django.core.paginator import Paginator
from django.utils.translation import gettext as _
from core.signals import log_view_activity
from core.utils import get_adjustment_account_code

@login_required
@require_http_methods(["GET"])
def search_customers_ajax(request):
    """بحث آجاكس للعملاء حسب الاسم/الهاتف/الإيميل مع إرجاع نتائج مبسطة.
    Query param: q, optional: limit (default 10)
    """
    q = (request.GET.get('q') or '').strip()
    limit = int(request.GET.get('limit') or 10)
    qs = CustomerSupplier.objects.filter(type__in=['customer', 'both'], is_active=True)
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q)
        )
    results = list(qs.order_by('name')[: max(1, min(limit, 25))].values('id', 'sequence_number', 'name'))
    try:
        class Obj:
            id = 0
            pk = 0
            def __str__(self):
                return str(_('Customer search'))
        if q:
            log_view_activity(request, 'search', Obj(), _('Customer quick search: %(q)s') % {'q': q})
    except Exception:
        pass
    return JsonResponse({'results': results})

class CustomerSupplierListView(LoginRequiredMixin, TemplateView):
    template_name = 'customers/list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # إحصائيات العملاء والموردين
        total_customers = CustomerSupplier.objects.filter(type__in=['customer', 'both']).count()
        total_suppliers = CustomerSupplier.objects.filter(type__in=['supplier', 'both']).count()
        
        # إحصائيات العملاء بناءً على current_balance
        customers = CustomerSupplier.objects.filter(type__in=['customer', 'both'])
        customer_balance = 0
        customer_debit = 0
        customer_credit = 0
        
        for customer in customers:
            balance = customer.current_balance
            customer_balance += balance
            if balance < 0:
                customer_debit += abs(balance)
            elif balance > 0:
                customer_credit += balance
        
        # إحصائيات الموردين بناءً على current_balance
        suppliers = CustomerSupplier.objects.filter(type__in=['supplier', 'both'])
        supplier_balance = 0
        supplier_debit = 0
        supplier_credit = 0
        
        for supplier in suppliers:
            balance = supplier.current_balance
            supplier_balance += balance
            if balance < 0:
                supplier_debit += abs(balance)
            elif balance > 0:
                supplier_credit += balance
        
        context.update({
            'total_customers': total_customers,
            'total_suppliers': total_suppliers,
            'customer_balance': customer_balance,
            'supplier_balance': supplier_balance,
            'customer_debit': customer_debit,  # المديونية (قيمة موجبة)
            'customer_credit': customer_credit,     # الأرصدة الدائنة
            'supplier_debit': supplier_debit,  # المديونية (قيمة موجبة)
            'supplier_credit': supplier_credit,     # الأرصدة الدائنة
        })
        
        return context

class CustomerListView(LoginRequiredMixin, ListView):
    model = CustomerSupplier
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20
    
    def get_queryset(self):
        # فلتر الحسابات النشطة فقط بشكل افتراضي (IFRS Compliant)
        queryset = CustomerSupplier.objects.filter(type__in=['customer', 'both'])
        
        # تطبيق الفلاتر
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        balance = self.request.GET.get('balance')
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(phone__icontains=search) |
                Q(email__icontains=search)
            )
            
        # إظهار الحسابات النشطة فقط بشكل افتراضي (متوافق مع IFRS)
        if status == 'all':
            pass  # إظهار جميع الحسابات (نشطة وغير نشطة)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        else:  # active or no filter
            queryset = queryset.filter(is_active=True)
            
        if balance == 'positive':
            queryset = queryset.filter(balance__gt=0)
        elif balance == 'negative':
            queryset = queryset.filter(balance__lt=0)
        elif balance == 'zero':
            queryset = queryset.filter(balance=0)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # إحصائيات العملاء
        all_customers = CustomerSupplier.objects.filter(type__in=['customer', 'both'])
        
        # حساب الإحصائيات بناءً على current_balance (المحسوب من المعاملات)
        total_debt = 0  # إجمالي الديون (العملاء المدينون للشركة)
        customer_credit = 0  # إجمالي الدائنين (الشركة مدينة للعملاء)
        total_balance = 0
        
        for customer in all_customers:
            balance = customer.current_balance
            total_balance += balance
            if balance > 0:
                total_debt += balance  # العميل مدين للشركة
            elif balance < 0:
                customer_credit += abs(balance)  # الشركة مدينة للعميل
        
        context.update({
            'total_customers': all_customers.count(),
            'active_customers': all_customers.filter(is_active=True).count(),
            'total_debt': total_debt,  # المديونية (قيمة موجبة)
            'customer_credit': customer_credit,  # الأرصدة الدائنة
            'total_balance': total_balance,  # إجمالي الأرصدة
            'average_balance': total_balance / all_customers.count() if all_customers.count() > 0 else 0,
        })
        
        # تسجيل النشاط في سجل المراجعة
        try:
            from core.signals import log_view_activity
            class CustomerListObj:
                def __init__(self):
                    self.id = 0
                    self.pk = 0
                def __str__(self):
                    return str(_('Customer List'))
            log_view_activity(self.request, 'view', CustomerListObj(), _('View customer list'))
        except Exception:
            pass
        
        return context

class SupplierListView(LoginRequiredMixin, ListView):
    model = CustomerSupplier
    template_name = 'customers/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('customers.can_view_suppliers'):
            from core.signals import log_view_activity
            log_view_activity(request, 'denied', None, _('Attempt to access supplier list without permission'))
            messages.error(request, _('You do not have permission to view suppliers'))
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        # فلتر الحسابات النشطة فقط بشكل افتراضي (IFRS Compliant)
        queryset = CustomerSupplier.objects.filter(type__in=['supplier', 'both'])
        
        # تطبيق الفلاتر
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        balance = self.request.GET.get('balance')
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(phone__icontains=search) |
                Q(email__icontains=search)
            )
            
        # إظهار الحسابات النشطة فقط بشكل افتراضي (متوافق مع IFRS)
        if status == 'all':
            pass  # إظهار جميع الحسابات (نشطة وغير نشطة)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        else:  # active or no filter
            queryset = queryset.filter(is_active=True)
            
        if balance == 'positive':
            queryset = queryset.filter(balance__gt=0)
        elif balance == 'negative':
            queryset = queryset.filter(balance__lt=0)
        elif balance == 'zero':
            queryset = queryset.filter(balance=0)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # إحصائيات الموردين
        all_suppliers = CustomerSupplier.objects.filter(type__in=['supplier', 'both'])
        
        # حساب الإحصائيات بناءً على current_balance (المحسوب من المعاملات)
        total_debt = 0
        supplier_credit = 0
        total_balance = 0
        
        for supplier in all_suppliers:
            balance = supplier.current_balance
            total_balance += balance
            if balance < 0:
                total_debt += abs(balance)
            elif balance > 0:
                supplier_credit += balance
        
        context.update({
            'total_suppliers': all_suppliers.count(),
            'active_suppliers': all_suppliers.filter(is_active=True).count(),
            'total_debt': total_debt,  # المديونية (قيمة موجبة)
            'supplier_credit': supplier_credit,  # الأرصدة الدائنة
            'total_balance': total_balance,  # إجمالي الأرصدة
            'average_balance': total_balance / all_suppliers.count() if all_suppliers.count() > 0 else 0,
        })
        
        return context

class CustomerSupplierCreateView(LoginRequiredMixin, View):
    template_name = 'customers/add.html'
    
    def get(self, request, *args, **kwargs):
        # التحقق من الصلاحيات - يحتاج صلاحية واحدة على الأقل
        has_customer_perm = request.user.has_perm('customers.can_add_customers')
        has_supplier_perm = request.user.has_perm('customers.can_add_suppliers')
        
        if not (has_customer_perm or has_supplier_perm):
            from core.signals import log_view_activity
            log_view_activity(request, 'denied', None, _('Attempt to access add customer/supplier page without permission'))
            messages.error(request, _('You do not have permission to add customer/supplier'))
            return redirect('core:dashboard')
        return render(request, self.template_name)
    
    def post(self, request, *args, **kwargs):
        try:
            # الحصول على البيانات من النموذج
            name = request.POST.get('name', '').strip()
            type_value = request.POST.get('type', 'customer')
            
            # التحقق من الصلاحيات بناءً على النوع
            if type_value in ['customer', 'both']:
                if not request.user.has_perm('customers.can_add_customers'):
                    messages.error(request, _('You do not have permission to add customers'))
                    return redirect('core:dashboard')
            if type_value in ['supplier', 'both']:
                if not request.user.has_perm('customers.can_add_suppliers'):
                    messages.error(request, _('You do not have permission to add suppliers'))
                    return redirect('core:dashboard')
            
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            address = request.POST.get('address', '').strip()
            city = request.POST.get('city', '').strip()
            tax_number = request.POST.get('tax_number', '').strip()
            credit_limit = request.POST.get('credit_limit', '0')
            balance = request.POST.get('balance', '0')
            notes = request.POST.get('notes', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            # التحقق من البيانات المطلوبة
            if not name:
                messages.error(request, 'Customer/Supplier name is required!')
                return render(request, self.template_name)
            
            if not city:
                messages.error(request, 'City is required!')
                return render(request, self.template_name)
            
            # التحقق من عدم وجود اسم مكرر
            if CustomerSupplier.objects.filter(name=name).exists():
                messages.error(request, f'A customer/supplier with the same name "{name}" already exists!')
                return render(request, self.template_name)
            
            # تحويل الأرقام المالية
            try:
                from decimal import Decimal
                credit_limit = Decimal(str(credit_limit)) if credit_limit else Decimal('0')
                balance = Decimal(str(balance)) if balance else Decimal('0')
            except (ValueError, Exception):
                messages.error(request, 'Invalid financial values!')
                return render(request, self.template_name)
            
            # إنشاء العميل/المورد الجديد
            customer_supplier = CustomerSupplier(
                name=name,
                type=type_value,
                email=email,
                phone=phone,
                address=address,
                city=city,
                tax_number=tax_number,
                credit_limit=credit_limit,
                balance=balance,
                notes=notes,
                is_active=is_active
            )
            
            # تمرير المستخدم الحالي للـ signal
            customer_supplier._creator_user = request.user
            
            # حفظ العميل (سيتم تنفيذ الـ signal تلقائياً)
            customer_supplier.save()
            
            # ملاحظة: إنشاء معاملة الرصيد الافتتاحي والقيد المحاسبي يتم تلقائياً عبر signal
            # في ملف customers/signals.py - create_opening_balance_journal_entry
            # وهو مطابق لمعايير IFRS
            
            # تسجيل النشاط
            log_view_activity(request, 'create', customer_supplier, _('Created customer/supplier: %(name)s') % {'name': name})
            
            # رسالة نجاح
            type_display = customer_supplier.get_type_display()
            
            # الحصول على رمز العملة من إعدادات الشركة
            currency_symbol = ""
            try:
                from settings.models import CompanySettings
                company_settings = CompanySettings.objects.first()
                if company_settings and company_settings.base_currency:
                    currency_symbol = company_settings.base_currency.symbol
            except:
                currency_symbol = ""
            
            messages.success(
                request, 
                f'{type_display} "{name}" created successfully!\n'
                f'Account number: {customer_supplier.id}\n'
                f'Opening balance: {balance:.3f} {currency_symbol}'
            )
            
            # إعادة توجيه حسب النوع
            if type_value == 'customer':
                return redirect('customers:customer_list')
            elif type_value == 'supplier':
                return redirect('customers:supplier_list')
            else:
                return redirect('customers:list')
            
        except Exception as e:
            messages.error(request, f'An error occurred while saving data: {str(e)}')
            return render(request, self.template_name)

class CustomerSupplierUpdateView(LoginRequiredMixin, View):
    template_name = 'customers/edit.html'
    
    def get(self, request, pk, *args, **kwargs):
        customer_supplier = get_object_or_404(CustomerSupplier, pk=pk)
        
        # التحقق من الصلاحيات بناءً على النوع
        if customer_supplier.type in ['customer', 'both']:
            if not request.user.has_perm('customers.can_edit_customers'):
                messages.error(request, _('You do not have permission to edit customers'))
                return redirect('core:dashboard')
        if customer_supplier.type in ['supplier', 'both']:
            if not request.user.has_perm('customers.can_edit_suppliers'):
                messages.error(request, _('You do not have permission to edit suppliers'))
                return redirect('core:dashboard')
        
        # حساب الائتمان المتاح بناءً على الرصيد الحالي المحسوب من المعاملات
        current_balance = customer_supplier.current_balance
        available_credit = customer_supplier.credit_limit - abs(current_balance) if current_balance < 0 else customer_supplier.credit_limit
        
        context = {
            'customer_supplier': customer_supplier,
            'available_credit': available_credit
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk, *args, **kwargs):
        customer_supplier = get_object_or_404(CustomerSupplier, pk=pk)
        
        # التحقق من الصلاحيات بناءً على النوع القديم
        if customer_supplier.type in ['customer', 'both']:
            if not request.user.has_perm('customers.can_edit_customers'):
                messages.error(request, _('You do not have permission to edit customers'))
                return redirect('core:dashboard')
        if customer_supplier.type in ['supplier', 'both']:
            if not request.user.has_perm('customers.can_edit_suppliers'):
                messages.error(request, _('You do not have permission to edit suppliers'))
                return redirect('core:dashboard')
        
        try:
            # حساب الرصيد الحالي قبل التعديل
            old_current_balance = customer_supplier.current_balance
            
            # الحصول على البيانات من النموذج
            name = request.POST.get('name', '').strip()
            type_value = request.POST.get('type', customer_supplier.type)  # النوع الجديد أو القديم
            
            # التحقق من الصلاحيات للنوع الجديد إذا تم تغييره
            if type_value != customer_supplier.type:
                if type_value in ['customer', 'both']:
                    if not request.user.has_perm('customers.can_edit_customers'):
                        messages.error(request, _('You do not have permission to change type to customer'))
                        return redirect('customers:edit', pk=pk)
                if type_value in ['supplier', 'both']:
                    if not request.user.has_perm('customers.can_edit_suppliers'):
                        messages.error(request, _('You do not have permission to change type to supplier'))
                        return redirect('customers:edit', pk=pk)
            
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            address = request.POST.get('address', '').strip()
            city = request.POST.get('city', '').strip()
            tax_number = request.POST.get('tax_number', '').strip()
            credit_limit = request.POST.get('credit_limit', '0')
            new_current_balance_str = request.POST.get('current_balance', '0')
            notes = request.POST.get('notes', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            # التحقق من البيانات المطلوبة
            if not name:
                messages.error(request, _('Customer/Supplier name is required!'))
                return redirect('customers:edit', pk=pk)
            
            if not city:
                messages.error(request, _('City is required!'))
                return redirect('customers:edit', pk=pk)
            
            # التحقق من عدم وجود اسم مكرر (باستثناء نفس الحساب)
            if CustomerSupplier.objects.filter(name=name).exclude(pk=pk).exists():
                messages.error(request, _('Another customer/supplier with the same name "%(name)s" exists!') % {'name': name})
                return redirect('customers:edit', pk=pk)
            
            # تحويل الأرقام المالية
            try:
                credit_limit = float(credit_limit) if credit_limit else 0
                new_current_balance = float(new_current_balance_str) if new_current_balance_str else 0
            except ValueError:
                messages.error(request, _('Invalid financial values!'))
                return redirect('customers:edit', pk=pk)
            
            # تحديث البيانات الأساسية
            old_type = customer_supplier.type  # حفظ النوع القديم
            customer_supplier.type = type_value
            customer_supplier.name = name
            customer_supplier.email = email
            customer_supplier.phone = phone
            customer_supplier.address = address
            customer_supplier.city = city
            customer_supplier.tax_number = tax_number
            customer_supplier.credit_limit = credit_limit
            customer_supplier.notes = notes
            customer_supplier.is_active = is_active
            customer_supplier.save()
            
            # معالجة تغيير النوع إذا لزم الأمر
            if old_type != type_value:
                # إعادة توليد الرقم التسلسلي للنوع الجديد
                # نحتاج إلى إعادة تعيين sequence_number إلى None أولاً ثم حفظ
                customer_supplier.sequence_number = None
                customer_supplier.save()  # سيستدعي _get_next_sequence_number() تلقائياً
                messages.warning(request, _('Account type changed from %(old)s to %(new)s. Sequence number updated to %(seq)s') % {
                    'old': dict(CustomerSupplier.TYPES)[old_type],
                    'new': dict(CustomerSupplier.TYPES)[type_value],
                    'seq': customer_supplier.sequence_number
                })
            
            # معالجة تغيير الرصيد الحالي
            from decimal import Decimal
            old_balance = Decimal(str(old_current_balance))
            new_balance = Decimal(str(new_current_balance))
            balance_difference = new_balance - old_balance
            
            if balance_difference != 0:
                # إنشاء حركة تعديل في جدول المعاملات وقيد محاسبي
                from accounts.models import AccountTransaction
                from django.utils import timezone
                
                # الحصول على نوع التعديل من الطلب (إذا وجد)
                adjustment_type = request.POST.get('adjustment_type', 'other')
                
                # تحديد نوع الحركة
                if balance_difference > 0:
                    # زيادة في الرصيد = مدين للعميل/مورد
                    direction = 'debit'
                    description = _('Manual balance adjustment - increase: %(amount)s - type: %(type)s') % {
                        'amount': abs(balance_difference),
                        'type': dict(AccountTransaction.ADJUSTMENT_TYPES).get(adjustment_type, 'Not specified')
                    }
                else:
                    # نقص في الرصيد = دائن للعميل/مورد
                    direction = 'credit'
                    description = _('Manual balance adjustment - decrease: %(amount)s - type: %(type)s') % {
                        'amount': abs(balance_difference),
                        'type': dict(AccountTransaction.ADJUSTMENT_TYPES).get(adjustment_type, 'Not specified')
                    }
                
                # إنشاء الحركة مع نوع التعديل
                AccountTransaction.objects.create(
                    customer_supplier=customer_supplier,
                    date=timezone.now().date(),
                    transaction_type='adjustment',
                    direction=direction,
                    amount=abs(balance_difference),
                    description=description,
                    reference_type='balance_adjustment',
                    reference_id=customer_supplier.id,
                    adjustment_type=adjustment_type,
                    is_manual_adjustment=True,
                    created_by=request.user
                )
                
                # تحديث رصيد العميل/المورد بعد إنشاء المعاملة
                customer_supplier.sync_balance()
                
                # إنشاء قيد محاسبي للتعديل باستخدام الحساب الصحيح
                try:
                    from journal.services import JournalService
                    from journal.models import Account
                    
                    # الحصول على الحساب المحاسبي الفرعي للعميل/المورد
                    # البحث تحت الحساب الرئيسي المناسب لتجنب الالتباس
                    if customer_supplier.type in ['customer', 'both']:
                        # البحث تحت حساب العملاء الرئيسي 1301
                        account_obj = Account.objects.filter(
                            name=customer_supplier.name, 
                            parent__code='1301'
                        ).first()
                        if not account_obj:
                            account_obj = Account.objects.filter(code='1301').first()
                    elif customer_supplier.type == 'supplier':
                        # البحث تحت حساب الموردين الرئيسي 2101
                        account_obj = Account.objects.filter(
                            name=customer_supplier.name, 
                            parent__code='2101'
                        ).first()
                        if not account_obj:
                            account_obj = Account.objects.filter(code='2101').first()
                    
                    # تحديد الحساب المقابل حسب نوع التعديل (IFRS compliant)
                    adjustment_account_code = get_adjustment_account_code(adjustment_type, is_bank=False, is_customer_supplier=True)
                    adjustment_account = Account.objects.filter(code=adjustment_account_code).first()
                    
                    if account_obj and adjustment_account:
                        lines_data = []
                        
                        if balance_difference > 0:
                            # زيادة في الرصيد: مدين الحساب / دائن الحساب المقابل
                            lines_data = [
                                {
                                    'account_id': account_obj.id,
                                    'debit': abs(balance_difference),
                                    'credit': Decimal('0'),
                                    'description': f'{_("Increase in balance")}: {name} ({dict(AccountTransaction.ADJUSTMENT_TYPES).get(adjustment_type, "Adjustment")})'
                                },
                                {
                                    'account_id': adjustment_account.id,
                                    'debit': Decimal('0'),
                                    'credit': abs(balance_difference),
                                    'description': f'{adjustment_account.name} - {dict(AccountTransaction.ADJUSTMENT_TYPES).get(adjustment_type, "Adjustment")}'
                                }
                            ]
                        else:
                            # نقصان في الرصيد: دائن الحساب / مدين الحساب المقابل
                            lines_data = [
                                {
                                    'account_id': adjustment_account.id,
                                    'debit': abs(balance_difference),
                                    'credit': Decimal('0'),
                                    'description': f'{adjustment_account.name} - {dict(AccountTransaction.ADJUSTMENT_TYPES).get(adjustment_type, "Adjustment")}'
                                },
                                {
                                    'account_id': account_obj.id,
                                    'debit': Decimal('0'),
                                    'credit': abs(balance_difference),
                                    'description': f'{_("Decrease in balance")}: {name} ({dict(AccountTransaction.ADJUSTMENT_TYPES).get(adjustment_type, "Adjustment")})'
                                }
                            ]
                        
                        journal_entry = JournalService.create_journal_entry(
                            entry_date=timezone.now().date(),
                            description=f'{_("Adjustment of Customer/Supplier Balance")}: {name} - {dict(AccountTransaction.ADJUSTMENT_TYPES).get(adjustment_type, "Adjustment")}',
                            reference_type='adjustment',
                            reference_id=customer_supplier.id,
                            lines_data=lines_data,
                            user=request.user
                        )
                except Exception as e:
                    print(f"خطأ في إنشاء القيد المحاسبي للتعديل: {e}")
                
                # تسجيل النشاط في سجل الأنشطة
                from core.models import AuditLog
                AuditLog.objects.create(
                    user=request.user,
                    action_type='update',
                    content_type='CustomerSupplier',
                    object_id=customer_supplier.id,
                    description=_('Customer/Supplier balance adjustment: %(name)s from %(old)s to %(new)s (difference: %(diff)s) - type: %(type)s') % {
                        'name': name,
                        'old': old_balance,
                        'new': new_balance,
                        'diff': balance_difference,
                        'type': dict(AccountTransaction.ADJUSTMENT_TYPES).get(adjustment_type, 'Not specified')
                    },
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            
            # تسجيل النشاط العام
            log_view_activity(request, 'update', customer_supplier, _('Update customer/supplier data: %(name)s') % {'name': name})
            
            # رسالة نجاح
            type_display = customer_supplier.get_type_display()
            
            # الحصول على رمز العملة من إعدادات الشركة
            currency_symbol = ""
            try:
                from settings.models import CompanySettings
                company_settings = CompanySettings.objects.first()
                if company_settings and company_settings.base_currency:
                    currency_symbol = company_settings.base_currency.symbol
            except:
                currency_symbol = ""
            
            # حساب الرصيد الجديد الفعلي
            final_balance = customer_supplier.current_balance
            
            success_message = _('%(type)s "%(name)s" updated successfully!') % {'type': type_display, 'name': name}
            if balance_difference != 0:
                success_message += '\n' + _('New balance: %(balance)s %(currency)s') % {
                    'balance': f'{final_balance:.3f}',
                    'currency': currency_symbol
                }
            
            messages.success(request, success_message)
            
            # إعادة توجيه حسب النوع
            if customer_supplier.type == 'customer':
                return redirect('customers:customer_list')
            elif customer_supplier.type == 'supplier':
                return redirect('customers:supplier_list')
            else:
                return redirect('customers:list')
            
        except Exception as e:
            # تسجيل الخطأ
            from core.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action_type='error',
                content_type='CustomerSupplier',
                object_id=pk,
                description=_('Error updating customer/supplier: %(error)s') % {'error': str(e)},
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.error(request, _('An error occurred while updating data: %(error)s') % {'error': str(e)})
            return redirect('customers:edit', pk=pk)

class CustomerSupplierDeleteView(LoginRequiredMixin, View):
    template_name = 'customers/delete.html'
    
    def get(self, request, pk, *args, **kwargs):
        customer_supplier = get_object_or_404(CustomerSupplier, pk=pk)
        
        # التحقق من الصلاحيات بناءً على النوع
        if customer_supplier.type in ['customer', 'both']:
            if not request.user.has_perm('customers.can_delete_customers'):
                messages.error(request, _('You do not have permission to delete customers'))
                return redirect('core:dashboard')
        if customer_supplier.type in ['supplier', 'both']:
            if not request.user.has_perm('customers.can_delete_suppliers'):
                messages.error(request, _('You do not have permission to delete suppliers'))
                return redirect('core:dashboard')
        
        # التحقق من الصلاحيات - فقط للسوبر أدمين
        if not request.user.is_superuser:
            messages.error(request, _('You do not have permission to delete customers/suppliers'))
            return redirect('customers:detail', pk=pk)
        
        # فحص البيانات المرتبطة
        related_data = self._get_related_data_count(customer_supplier)
        
        context = {
            'customer_supplier': customer_supplier,
            'related_data': related_data,
            'can_delete': True,  # السوبر أدمين يمكنه الحذف دائماً
            'warning_message': _('Warning: All related data will be permanently deleted!') if any(related_data.values()) else None
        }
        return render(request, self.template_name, context)
    
    def _get_related_data_count(self, customer_supplier):
        """حساب عدد البيانات المرتبطة"""
        from sales.models import SalesInvoice, SalesReturn
        from purchases.models import PurchaseInvoice, PurchaseReturn
        from accounts.models import AccountTransaction
        
        # حساب الفواتير
        sales_invoices_count = SalesInvoice.objects.filter(customer=customer_supplier).count()
        purchase_invoices_count = PurchaseInvoice.objects.filter(supplier=customer_supplier).count()
        total_invoices = sales_invoices_count + purchase_invoices_count
        
        # حساب المردودات
        sales_returns_count = SalesReturn.objects.filter(customer=customer_supplier).count()
        purchase_returns_count = PurchaseReturn.objects.filter(original_invoice__supplier=customer_supplier).count()
        total_returns = sales_returns_count + purchase_returns_count
        
        # حساب المعاملات
        transactions_count = AccountTransaction.objects.filter(customer_supplier=customer_supplier).count()
        
        return {
            'invoices': total_invoices,  # إجمالي فواتير المبيعات والمشتريات
            'payments': total_returns,  # المردودات (يمكن اعتبارها كمدفوعات عكسية)
            'transactions': transactions_count,  # المعاملات المالية
            # بيانات تفصيلية إضافية
            'sales_invoices': sales_invoices_count,
            'purchase_invoices': purchase_invoices_count,
            'sales_returns': sales_returns_count,
            'purchase_returns': purchase_returns_count,
        }
    
    def post(self, request, pk, *args, **kwargs):
        customer_supplier = get_object_or_404(CustomerSupplier, pk=pk)
        
        # التحقق من الصلاحيات بناءً على النوع
        if customer_supplier.type in ['customer', 'both']:
            if not request.user.has_perm('customers.can_delete_customers'):
                messages.error(request, _('You do not have permission to delete customers'))
                return redirect('core:dashboard')
        if customer_supplier.type in ['supplier', 'both']:
            if not request.user.has_perm('customers.can_delete_suppliers'):
                messages.error(request, _('You do not have permission to delete suppliers'))
                return redirect('core:dashboard')
        
        try:
            # التحقق من الصلاحيات - فقط للسوبر أدمين
            if not request.user.is_superuser:
                messages.error(request, _('You do not have permission to delete customers/suppliers'))
                return redirect('customers:delete', pk=pk)
            
            # حفظ البيانات للرسالة والتدقيق
            name = customer_supplier.name
            type_display = customer_supplier.get_type_display()
            customer_id = customer_supplier.id
            
            # الحصول على إحصائيات البيانات المرتبطة
            related_count = self._get_related_data_count(customer_supplier)
            total_records = related_count['invoices'] + related_count['payments'] + related_count['transactions']
            
            # التحقق من وجود حركات
            if total_records > 0:
                # يوجد حركات - منع الحذف واقتراح التعطيل
                action = request.POST.get('action')
                
                if action == 'deactivate':
                    # المستخدم اختار التعطيل
                    customer_supplier.is_active = False
                    customer_supplier.save()
                    
                    # تسجيل عملية التعطيل
                    from core.models import AuditLog
                    AuditLog.objects.create(
                        user=request.user,
                        action_type='deactivate',
                        content_type='CustomerSupplier',
                        object_id=customer_id,
                        description=_('تم تعطيل العميل/المورد مع الحفاظ على جميع السجلات التاريخية: %(name)s (%(type)s). البيانات المحفوظة: %(invoices)s فاتورة، %(returns)s مرتجع، %(transactions)s معاملة. متوافق مع IFRS (IAS 1, IAS 8).') % {
                            'name': name, 
                            'type': type_display,
                            'invoices': related_count['invoices'],
                            'returns': related_count['payments'],
                            'transactions': related_count['transactions']
                        },
                        ip_address=self.get_client_ip(request)
                    )
                    
                    messages.success(
                        request, 
                        _('تم تعطيل %(type)s "%(name)s" بنجاح! جميع السجلات التاريخية محفوظة (%(invoices)s فاتورة، %(returns)s مرتجع، %(transactions)s معاملة). متوافق مع معايير IFRS.') % {
                            'type': type_display, 
                            'name': name,
                            'invoices': related_count['invoices'],
                            'returns': related_count['payments'],
                            'transactions': related_count['transactions']
                        }
                    )
                    
                    return redirect('customers:list')
                else:
                    # عرض رسالة تحذيرية مع خيار التعطيل
                    messages.error(
                        request,
                        _('⚠️ Cannot delete %(type)s "%(name)s" because it has related transactions:\n• %(invoices)s invoices\n• %(returns)s returns\n• %(transactions)s financial transactions\n\n✅ You can disable the account instead of deleting it to preserve accounting records (IFRS compliant).') % {
                            'type': type_display,
                            'name': name,
                            'invoices': related_count['invoices'],
                            'returns': related_count['payments'],
                            'transactions': related_count['transactions']
                        }
                    )
                    
                    # إعادة توجيه إلى صفحة الحذف مع عرض خيار التعطيل
                    return redirect('customers:delete', pk=pk)
            
            else:
                # لا توجد حركات - السماح بالحذف النهائي
                confirm = request.POST.get('confirm_delete')
                if confirm != 'DELETE':
                    messages.error(request, _('You must type "DELETE" to confirm!'))
                    return redirect('customers:delete', pk=pk)
                
                # حذف نهائي
                customer_supplier.delete()
                
                # تسجيل عملية الحذف
                from core.models import AuditLog
                AuditLog.objects.create(
                    user=request.user,
                    action_type='delete',
                    content_type='CustomerSupplier',
                    object_id=customer_id,
                    description=_('تم حذف العميل/المورد نهائياً (لا توجد معاملات مرتبطة): %(name)s (%(type)s)') % {
                        'name': name, 
                        'type': type_display
                    },
                    ip_address=self.get_client_ip(request)
                )
                
                messages.success(
                    request, 
                    _('✅ تم حذف %(type)s "%(name)s" بنجاح! (لم تكن هناك معاملات مرتبطة)') % {
                        'type': type_display, 
                        'name': name
                    }
                )
                
                return redirect('customers:list')
            
        except Exception as e:
            # تسجيل الخطأ في سجل الأنشطة
            from core.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action_type='delete_failed',
                content_type='CustomerSupplier',
                object_id=customer_supplier.id,
                description=_('فشل حذف/تعطيل العميل/المورد: %(error)s') % {'error': str(e)},
                ip_address=self.get_client_ip(request)
            )
            
            messages.error(request, _('An error occurred during the operation: %(error)s') % {'error': str(e)})
            return redirect('customers:delete', pk=pk)
    
    def get_client_ip(self, request):
        """الحصول على عنوان IP الخاص بالعميل"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class CustomerSupplierTransactionsView(LoginRequiredMixin, TemplateView):
    template_name = 'customers/transactions.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = kwargs.get('pk')
        customer_supplier = get_object_or_404(CustomerSupplier, pk=pk)
        
        # الحصول على فلاتر التاريخ من الطلب
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        try:
            # استيراد نموذج المعاملات
            from accounts.models import AccountTransaction
            from datetime import datetime
            from django.db.models import Sum
            from decimal import Decimal
            
            # الحصول على المعاملات
            from django.db.models import Q
            
            # إنشاء query للعميل/المورد الحالي
            query = Q(customer_supplier=customer_supplier)
            
            # إذا كان العميل من نوع "customer" أو "both"، ابحث عن موردين بنفس الاسم
            if customer_supplier.type in ['customer', 'both']:
                # البحث عن موردين بنفس الاسم
                related_suppliers = CustomerSupplier.objects.filter(
                    name=customer_supplier.name,
                    type__in=['supplier', 'both']
                ).exclude(id=customer_supplier.id)
                
                if related_suppliers.exists():
                    # إضافة موردين مرتبطين للـ query
                    query |= Q(customer_supplier__in=related_suppliers)
            
            # إذا كان المورد من نوع "supplier" أو "both"، ابحث عن عملاء بنفس الاسم  
            elif customer_supplier.type in ['supplier', 'both']:
                # البحث عن عملاء بنفس الاسم
                related_customers = CustomerSupplier.objects.filter(
                    name=customer_supplier.name,
                    type__in=['customer', 'both']
                ).exclude(id=customer_supplier.id)
                
                if related_customers.exists():
                    # إضافة عملاء مرتبطين للـ query
                    query |= Q(customer_supplier__in=related_customers)
            
            # جلب جميع المعاملات باستخدام query واحد
            transactions = AccountTransaction.objects.filter(query).order_by('-date', '-id')
            
            # تطبيق فلترة التاريخ
            date_from_obj = None
            date_to_obj = None
            
            if date_from:
                try:
                    date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                    transactions = transactions.filter(date__gte=date_from_obj)
                except ValueError:
                    pass
            
            if date_to:
                try:
                    date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                    transactions = transactions.filter(date__lte=date_to_obj)
                except ValueError:
                    pass
            
            # حساب الرصيد الافتتاحي
            if date_from:
                try:
                    date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                    # حساب المعاملات قبل تاريخ البداية
                    prior_transactions = AccountTransaction.objects.filter(
                        query,
                        date__lt=date_from_obj
                    )
                    prior_debit = prior_transactions.filter(direction='debit').aggregate(
                        total=Sum('amount'))['total'] or Decimal('0')
                    prior_credit = prior_transactions.filter(direction='credit').aggregate(
                        total=Sum('amount'))['total'] or Decimal('0')
                    opening_balance = prior_debit - prior_credit
                except ValueError:
                    opening_balance = Decimal('0')
            else:
                # عندما لا يكون هناك فلترة تاريخ، الرصيد الافتتاحي = معاملات opening_balance فقط
                opening_trans = AccountTransaction.objects.filter(
                    query,
                    reference_type__in=['opening_balance', 'cs_opening']
                )
                opening_debit = opening_trans.filter(direction='debit').aggregate(
                    total=Sum('amount'))['total'] or Decimal('0')
                opening_credit = opening_trans.filter(direction='credit').aggregate(
                    total=Sum('amount'))['total'] or Decimal('0')
                opening_balance = opening_debit - opening_credit
            
            # لا نقوم بإصلاح تلقائي - الفحص يكون من جانب العميل فقط
            
            # الحصول على المستندات الأصلية (للعرض الموسع)
            from sales.models import SalesInvoice, SalesReturn
            from purchases.models import PurchaseInvoice, PurchaseReturn, PurchaseDebitNote
            from receipts.models import PaymentReceipt
            from payments.models import PaymentVoucher
            from sales.models import SalesCreditNote
            
            # فواتير المبيعات (جميع أنواع الدفع)
            sales_invoices = SalesInvoice.objects.filter(customer=customer_supplier)
            
            # فواتير المشتريات (جميع أنواع الدفع)
            purchase_invoices = PurchaseInvoice.objects.filter(supplier=customer_supplier)
            
            # سندات القبض
            receipts = PaymentReceipt.objects.filter(customer=customer_supplier)
            
            # سندات الصرف
            payments = PaymentVoucher.objects.filter(supplier=customer_supplier)
            
            # مردودات المبيعات
            sales_returns = SalesReturn.objects.filter(customer=customer_supplier)
            
            # مردودات المشتريات
            purchase_returns = PurchaseReturn.objects.filter(original_invoice__supplier=customer_supplier)
            
            # مذكرات الدين للمبيعات (Sales Credit Notes)
            sales_credit_notes = SalesCreditNote.objects.filter(customer=customer_supplier)
            
            # مذكرات الخصم للمشتريات (Purchase Debit Notes)
            purchase_debit_notes = PurchaseDebitNote.objects.filter(supplier=customer_supplier)
            
            # تطبيق فلتر التاريخ على المستندات
            if date_from_obj:
                sales_invoices = sales_invoices.filter(date__gte=date_from_obj)
                purchase_invoices = purchase_invoices.filter(date__gte=date_from_obj)
                receipts = receipts.filter(date__gte=date_from_obj)
                payments = payments.filter(date__gte=date_from_obj)
                sales_returns = sales_returns.filter(date__gte=date_from_obj)
                purchase_returns = purchase_returns.filter(date__gte=date_from_obj)
                sales_credit_notes = sales_credit_notes.filter(date__gte=date_from_obj)
                purchase_debit_notes = purchase_debit_notes.filter(date__gte=date_from_obj)
            
            if date_to_obj:
                sales_invoices = sales_invoices.filter(date__lte=date_to_obj)
                purchase_invoices = purchase_invoices.filter(date__lte=date_to_obj)
                receipts = receipts.filter(date__lte=date_to_obj)
                payments = payments.filter(date__lte=date_to_obj)
                sales_returns = sales_returns.filter(date__lte=date_to_obj)
                purchase_returns = purchase_returns.filter(date__lte=date_to_obj)
                sales_credit_notes = sales_credit_notes.filter(date__lte=date_to_obj)
                purchase_debit_notes = purchase_debit_notes.filter(date__lte=date_to_obj)
            
            # إنشاء قائمة موحدة من جميع المستندات مع تصنيف IFRS
            all_documents = []
            
            # إضافة معاملات التعديلات اليدوية فقط (ليس الرصيد الافتتاحي)
            # الرصيد الافتتاحي يُحسب في opening_balance ولا يظهر في قائمة المستندات
            adjustment_transactions = transactions.filter(
                reference_type__in=['cs_adjustment', 'balance_adjustment']
            )
            
            # تطبيق فلتر التاريخ على معاملات التعديلات
            if date_from_obj:
                adjustment_transactions = adjustment_transactions.filter(date__gte=date_from_obj)
            if date_to_obj:
                adjustment_transactions = adjustment_transactions.filter(date__lte=date_to_obj)
            
            for trans in adjustment_transactions:
                all_documents.append({
                    'date': trans.date,
                    'type': 'balance_adjustment',
                    'type_display': _('Balance Adjustment'),
                    'number': trans.transaction_number,
                    'amount': trans.amount,
                    'direction': trans.direction,
                    'payment_type': '-',
                    'url': '#',  # لا يوجد رابط مباشر لمعاملة التعديل
                    'icon': 'fa-edit',
                    'color': 'info',
                    'description': trans.description,
                    'object': trans
                })
            
            # فواتير المبيعات - مدين (Debit) في حساب العميل
            # لأن العميل مدين للشركة (الذمم المدينة)
            for invoice in sales_invoices:
                all_documents.append({
                    'date': invoice.date,
                    'type': 'sales_invoice',
                    'type_display': _('Sales Invoice'),
                    'number': invoice.invoice_number,
                    'amount': invoice.total_amount,
                    'direction': 'debit',  # مدين في حساب العميل (الذمم المدينة)
                    'payment_type': invoice.get_payment_type_display(),
                    'url': reverse('sales:invoice_detail', args=[invoice.id]),
                    'icon': 'fa-file-invoice',
                    'color': 'success',
                    'object': invoice
                })
            
            # فواتير المشتريات - الاتجاه يعتمد على نوع العميل/المورد
            for invoice in purchase_invoices:
                # إذا كان العميل من نوع "supplier" أو "both"، فاتورة المشتريات = دائن (Credit)
                # لأننا ندين للمورد (الذمم الدائنة)
                if customer_supplier.type in ['supplier', 'both']:
                    direction = 'credit'  # IFRS: نحن ندين للمورد = دائن في حساب المورد
                else:
                    direction = 'debit'   # IFRS: المشتريات = مصروف/أصل = مدين
                
                all_documents.append({
                    'date': invoice.date,
                    'type': 'purchase_invoice',
                    'type_display': _('Purchase Invoice'),
                    'number': invoice.invoice_number,
                    'amount': invoice.total_amount,
                    'direction': direction,
                    'payment_type': invoice.get_payment_type_display(),
                    'url': reverse('purchases:invoice_detail', args=[invoice.id]),
                    'icon': 'fa-shopping-cart',
                    'color': 'danger',
                    'object': invoice
                })
            
            # سندات القبض - دائن (Credit) حسب IFRS (تحصيل نقدية)
            for receipt in receipts:
                all_documents.append({
                    'date': receipt.date,
                    'type': 'receipt',
                    'type_display': _('Receipt Voucher'),
                    'number': receipt.receipt_number,
                    'amount': receipt.amount,
                    'direction': 'credit',  # IFRS: قبض نقدية = تخفيض ذمم = دائن
                    'payment_type': receipt.get_payment_type_display(),
                    'url': reverse('receipts:receipt_detail', args=[receipt.id]),
                    'icon': 'fa-money-bill-wave',
                    'color': 'success',
                    'object': receipt
                })
            
            # سندات الصرف - مدين (Debit) حسب IFRS (صرف نقدية)
            for payment in payments:
                all_documents.append({
                    'date': payment.date,
                    'type': 'payment',
                    'type_display': _('Payment Voucher'),
                    'number': payment.voucher_number,
                    'amount': payment.amount,
                    'direction': 'debit',  # IFRS: صرف نقدية = تخفيض دائنين = مدين
                    'payment_type': payment.get_payment_type_display(),
                    'url': reverse('payments:payment_detail', args=[payment.id]),
                    'icon': 'fa-hand-holding-usd',
                    'color': 'danger',
                    'object': payment
                })
            
            # مردودات المبيعات - دائن (Credit) في حساب العميل
            # لأنها تقلل الذمم المدينة (عكس فاتورة المبيعات)
            for return_inv in sales_returns:
                all_documents.append({
                    'date': return_inv.date,
                    'type': 'sales_return',
                    'type_display': _('Sales Return'),
                    'number': return_inv.return_number,
                    'amount': return_inv.total_amount,
                    'direction': 'credit',  # دائن في حساب العميل (تقليل الذمم)
                    'payment_type': '-',
                    'url': reverse('sales:return_detail', args=[return_inv.id]),
                    'icon': 'fa-undo',
                    'color': 'warning',
                    'object': return_inv
                })
            
            # مردودات المشتريات - دائن (Credit) حسب IFRS (عكس المصروف)
            for return_inv in purchase_returns:
                all_documents.append({
                    'date': return_inv.date,
                    'type': 'purchase_return',
                    'type_display': _('Purchase Return'),
                    'number': return_inv.return_number,
                    'amount': return_inv.total_amount,
                    'direction': 'credit',  # IFRS: مرتجع مشتريات = عكس المصروف = دائن
                    'payment_type': '-',
                    'url': reverse('purchases:return_detail', args=[return_inv.id]),
                    'icon': 'fa-undo',
                    'color': 'info',
                    'object': return_inv
                })
            
            # مذكرات الدين للمبيعات - دائن (Credit) في حساب العميل
            # مذكرة الدين تُستخدم لتقليل المبلغ المستحق على العميل (تخفيض الذمم المدينة)
            for credit_note in sales_credit_notes:
                all_documents.append({
                    'date': credit_note.date,
                    'type': 'sales_credit_note',
                    'type_display': _('Sales Credit Note'),
                    'number': credit_note.note_number,
                    'amount': credit_note.total_amount,
                    'direction': 'credit',  # IFRS: تخفيض ذمم مدينة = دائن
                    'payment_type': '-',
                    'url': reverse('sales:creditnote_detail', args=[credit_note.id]),
                    'icon': 'fa-file-invoice-dollar',
                    'color': 'primary',
                    'object': credit_note
                })
            
            # مذكرات الخصم للمشتريات - مدين (Debit) في حساب المورد
            # مذكرة الخصم تُستخدم لتقليل المبلغ المستحق للمورد (تخفيض الذمم الدائنة)
            for debit_note in purchase_debit_notes:
                all_documents.append({
                    'date': debit_note.date,
                    'type': 'purchase_debit_note',
                    'type_display': _('Purchase Debit Note'),
                    'number': debit_note.note_number,
                    'amount': debit_note.total_amount,
                    'direction': 'debit',  # IFRS: تخفيض ذمم دائنة = مدين
                    'payment_type': '-',
                    'url': reverse('purchases:debitnote_detail', args=[debit_note.id]),
                    'icon': 'fa-file-invoice-dollar',
                    'color': 'secondary',
                    'object': debit_note
                })
            
            # ⭐ إضافة المعاملات التي ليس لها مستند أصلي (محذوف أو مفقود)
            # هذا يحل مشكلة عدم ظهور المعاملات للفواتير المحذوفة
            displayed_transaction_ids = set()
            
            # جمع IDs المعاملات التي تم عرضها بالفعل من خلال المستندات
            for trans in adjustment_transactions:
                displayed_transaction_ids.add(trans.id)
            
            # البحث عن المعاملات المتبقية التي لم يتم عرضها
            # استثناء الرصيد الافتتاحي والتعديلات لأنها تُحسب بشكل منفصل
            orphaned_transactions = transactions.exclude(
                id__in=displayed_transaction_ids
            ).exclude(
                reference_type__in=['opening_balance', 'cs_opening', 'cs_adjustment', 'balance_adjustment']
            )
            
            # إضافة المعاملات اليتيمة (بدون مستند أصلي)
            for trans in orphaned_transactions:
                # التحقق من أن المستند الأصلي محذوف
                document_exists = False
                
                if trans.reference_type == 'sales_invoice' and trans.reference_id:
                    document_exists = sales_invoices.filter(id=trans.reference_id).exists()
                elif trans.reference_type == 'purchase_invoice' and trans.reference_id:
                    document_exists = purchase_invoices.filter(id=trans.reference_id).exists()
                elif trans.reference_type == 'receipt' and trans.reference_id:
                    document_exists = receipts.filter(id=trans.reference_id).exists()
                elif trans.reference_type == 'payment' and trans.reference_id:
                    document_exists = payments.filter(id=trans.reference_id).exists()
                elif trans.reference_type == 'sales_return' and trans.reference_id:
                    document_exists = sales_returns.filter(id=trans.reference_id).exists()
                elif trans.reference_type == 'purchase_return' and trans.reference_id:
                    document_exists = purchase_returns.filter(id=trans.reference_id).exists()
                elif trans.reference_type == 'credit_note' and trans.reference_id:
                    document_exists = sales_credit_notes.filter(id=trans.reference_id).exists()
                elif trans.reference_type == 'debit_note' and trans.reference_id:
                    document_exists = purchase_debit_notes.filter(id=trans.reference_id).exists()
                
                # إذا كان المستند محذوف أو لا يوجد reference_id، أضف المعاملة
                if not document_exists:
                    all_documents.append({
                        'date': trans.date,
                        'type': 'orphaned_transaction',
                        'type_display': trans.get_transaction_type_display() + ' ' + _('(Deleted Document)'),
                        'number': trans.transaction_number,
                        'amount': trans.amount,
                        'direction': trans.direction,
                        'payment_type': '-',
                        'url': '#',
                        'icon': 'fa-exclamation-triangle',
                        'color': 'warning',
                        'description': trans.description,
                        'object': trans
                    })
            
            # ترتيب جميع المستندات حسب التاريخ (الأحدث أولاً)
            all_documents.sort(key=lambda x: x['date'], reverse=True)
            
            # ⭐ حساب إجماليات المستندات (بدون الرصيد الافتتاحي فقط)
            # وفقاً لـ IFRS: نفصل الرصيد الافتتاحي عن المعاملات الفعلية
            # لكن التعديلات (balance_adjustment) تُحسب ضمن الإجماليات
            total_debit = Decimal('0')
            total_credit = Decimal('0')
            
            for doc in all_documents:
                # استثناء الرصيد الافتتاحي فقط من الإجماليات
                # التعديلات تُحسب ضمن المعاملات
                if doc['type'] != 'opening_balance':
                    if doc['direction'] == 'debit':
                        total_debit += doc['amount']
                    elif doc['direction'] == 'credit':
                        total_credit += doc['amount']
            
            # حساب إجماليات جميع المستندات (بما فيها الرصيد الافتتاحي) للعرض
            total_documents_debit = sum(doc['amount'] for doc in all_documents if doc['direction'] == 'debit')
            total_documents_credit = sum(doc['amount'] for doc in all_documents if doc['direction'] == 'credit')

            # حساب الرصيد الختامي وفقاً لـ IFRS
            # الرصيد الختامي = الرصيد الافتتاحي + (إجمالي المدين - إجمالي الدائن)
            closing_balance = opening_balance + (total_debit - total_credit)
            
            # إذا لم تكن هناك فلترة تاريخ، يجب أن يطابق الرصيد الختامي الرصيد الحالي
            if not date_from and not date_to:
                closing_balance = customer_supplier.balance
            
            # حساب إجمالي المستندات (عدد المستندات)
            total_documents_count = len(all_documents)
            
            context.update({
                'customer_supplier': customer_supplier,
                'transactions': transactions,
                'opening_balance': opening_balance,  # الرصيد الافتتاحي المحسوب
                'closing_balance': closing_balance,  # الرصيد الختامي = افتتاحي + صافي المستندات
                'total_debit': total_debit,
                'total_credit': total_credit,
                'total_transactions': total_documents_count,
                'date_from': date_from,
                'date_to': date_to,
                # إجماليات المستندات
                'total_documents_debit': total_documents_debit,
                'total_documents_credit': total_documents_credit,
                'total_documents_count': total_documents_count,
                # إضافة المستندات الأصلية
                'sales_invoices': sales_invoices.order_by('-date'),
                'purchase_invoices': purchase_invoices.order_by('-date'),
                'receipts': receipts.order_by('-date'),
                'payments': payments.order_by('-date'),
                'sales_returns': sales_returns.order_by('-date'),
                'purchase_returns': purchase_returns.order_by('-date'),
                'sales_credit_notes': sales_credit_notes.order_by('-date'),
                'purchase_debit_notes': purchase_debit_notes.order_by('-date'),
                # إضافة القائمة الموحدة
                'all_documents': all_documents,
            })
            
        except ImportError as e:
            # في حالة عدم وجود نموذج الحسابات
            from sales.models import SalesInvoice, SalesReturn
            from purchases.models import PurchaseInvoice, PurchaseReturn
            from receipts.models import PaymentReceipt
            from payments.models import PaymentVoucher
            
            context.update({
                'customer_supplier': customer_supplier,
                'transactions': [],
                'opening_balance': Decimal('0'),
                'closing_balance': customer_supplier.balance,
                'total_debit': Decimal('0'),
                'total_credit': Decimal('0'),
                'total_transactions': 0,
                'date_from': date_from,
                'date_to': date_to,
                'error_message': 'Accounts model not available',
                # إضافة المستندات حتى في حالة الخطأ
                'sales_invoices': SalesInvoice.objects.filter(customer=customer_supplier),
                'purchase_invoices': PurchaseInvoice.objects.filter(supplier=customer_supplier),
                'receipts': PaymentReceipt.objects.filter(customer=customer_supplier),
                'payments': PaymentVoucher.objects.filter(supplier=customer_supplier),
                'sales_returns': SalesReturn.objects.filter(customer=customer_supplier),
                'purchase_returns': PurchaseReturn.objects.filter(original_invoice__supplier=customer_supplier),
            })
        except Exception as e:
            # في حالة أي خطأ آخر
            from sales.models import SalesInvoice, SalesReturn
            from purchases.models import PurchaseInvoice, PurchaseReturn
            from receipts.models import PaymentReceipt
            from payments.models import PaymentVoucher
            
            context.update({
                'customer_supplier': customer_supplier,
                'transactions': [],
                'opening_balance': Decimal('0'),
                'closing_balance': customer_supplier.balance,
                'total_debit': Decimal('0'),
                'total_credit': Decimal('0'),
                'total_transactions': 0,
                'date_from': date_from,
                'date_to': date_to,
                'error_message': f'Error loading data: {str(e)}',
                # إضافة المستندات حتى في حالة الخطأ
                'sales_invoices': SalesInvoice.objects.filter(customer=customer_supplier),
                'purchase_invoices': PurchaseInvoice.objects.filter(supplier=customer_supplier),
                'receipts': PaymentReceipt.objects.filter(customer=customer_supplier),
                'payments': PaymentVoucher.objects.filter(supplier=customer_supplier),
                'sales_returns': SalesReturn.objects.filter(customer=customer_supplier),
                'purchase_returns': PurchaseReturn.objects.filter(original_invoice__supplier=customer_supplier),
            })
        
        # تسجيل النشاط في سجل الأنشطة
        from core.models import AuditLog
        total_transactions_count = context.get('total_transactions', 0)
        AuditLog.objects.create(
            user=self.request.user,
            action_type='view',
            content_type='customer_supplier_transactions',
            description=f'View customer/supplier transactions: {customer_supplier.name} ({total_transactions_count} transactions)',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        
        return context

# API للحصول على بيانات العميل/المورد عبر AJAX
def get_customer_supplier_ajax(request, customer_id):
    if not customer_id:
        return JsonResponse({'error': 'Customer/Supplier ID required'}, status=400)
    
    try:
        customer_supplier = CustomerSupplier.objects.get(id=customer_id)
        
        data = {
            'id': customer_supplier.id,
            'name': customer_supplier.name,
            'type': customer_supplier.type,
            'type_display': customer_supplier.get_type_display(),
            'email': customer_supplier.email,
            'phone': customer_supplier.phone,
            'address': customer_supplier.address,
            'tax_number': customer_supplier.tax_number,
            'credit_limit': float(customer_supplier.credit_limit),
            'balance': float(customer_supplier.balance),
            'current_balance': float(customer_supplier.current_balance),
            'is_active': customer_supplier.is_active,
            'notes': customer_supplier.notes,
            'created_at': customer_supplier.created_at.strftime('%Y-%m-%d'),
        }
        
        return JsonResponse(data)
        
    except CustomerSupplier.DoesNotExist:
        return JsonResponse({'error': 'Customer/Supplier not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def report_balance_issue(request, customer_pk):
    """الإبلاغ عن مشكلة في الرصيد من جانب العميل"""
    
    try:
        from django.http import JsonResponse
        import json
        
        # الحصول على العميل/المورد
        customer_supplier = get_object_or_404(CustomerSupplier, pk=customer_pk)
        
        # قراءة البيانات المرسلة
        data = json.loads(request.body)
        
        # تسجيل الإبلاغ في سجل الأنشطة
        from core.models import AuditLog
        from django.utils.translation import gettext as _
        
        description = _('Balance issue reported for customer/supplier %(name)s. Opening: %(opening).3f, Debit: %(debit).3f, Credit: %(credit).3f, Expected: %(expected).3f, Displayed: %(displayed).3f') % {
            'name': customer_supplier.name,
            'opening': data.get('opening_balance', 0),
            'debit': data.get('total_debit', 0),
            'credit': data.get('total_credit', 0),
            'expected': data.get('expected_balance', 0),
            'displayed': data.get('displayed_balance', 0)
        }
        
        AuditLog.objects.create(
            user=request.user,
            action_type='report',
            content_type='customer_supplier_balance_issue',
            object_id=customer_supplier.id,
            description=description,
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return JsonResponse({'success': True, 'message': _('Balance issue reported successfully')})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    """حذف حركة - للمدراء فقط"""
    
    # التحقق من أن المستخدم مدير عام
    if not request.user.is_superuser:
        return JsonResponse({
            'success': False,
            'error': 'You are not allowed to delete transactions'
        }, status=403)
    
    try:
        # استيراد نموذج المعاملات
        from accounts.models import AccountTransaction
        
        # الحصول على العميل/المورد
        customer_supplier = get_object_or_404(CustomerSupplier, pk=customer_pk)
        
        # الحصول على الحركة
        transaction_obj = get_object_or_404(
            AccountTransaction, 
            id=transaction_id,
            customer_supplier=customer_supplier
        )
        
        # حفظ معلومات الحركة للسجل
        transaction_number = transaction_obj.transaction_number
        amount = transaction_obj.amount
        direction = transaction_obj.direction
        
        # حساب التأثير على رصيد العميل/المورد
        balance_adjustment = 0
        if direction == 'debit':
            # الحركة المدينة تزيد الرصيد، فعند الحذف نقلل الرصيد
            balance_adjustment = -amount
        else:
            # الحركة الدائنة تقلل الرصيد، فعند الحذف نزيد الرصيد
            balance_adjustment = amount
        
        # بدء المعاملة في قاعدة البيانات
        with transaction.atomic():
            # حذف الحركة
            transaction_obj.delete()
            
            # تحديث رصيد العميل/المورد
            customer_supplier.balance += balance_adjustment
            customer_supplier.save()
            
            # إعادة حساب الأرصدة للحركات التالية إذا لزم الأمر
            # (يمكن تنفيذ هذا لاحقاً إذا احتجنا لدقة أكبر في الأرصدة)
        
        return JsonResponse({
            'success': True,
            'message': f'Transaction {transaction_number} deleted successfully'
        })
        
    except AccountTransaction.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Transaction not found'
        }, status=404)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error deleting transaction: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt  
def ajax_add_supplier(request):
    """إضافة مورد جديد عبر AJAX"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'طريقة الطلب غير صحيحة'
        })
    
    # التحقق من الصلاحيات
    if not request.user.has_perm('customers.can_add_suppliers'):
        return JsonResponse({
            'success': False,
            'message': 'You do not have permission to add suppliers'
        })
    
    try:
        with transaction.atomic():
            # استلام البيانات
            name = request.POST.get('name', '').strip()
            phone = request.POST.get('phone', '').strip()
            email = request.POST.get('email', '').strip()
            tax_number = request.POST.get('tax_number', '').strip()
            address = request.POST.get('address', '').strip()
            city = request.POST.get('city', '').strip()
            notes = request.POST.get('notes', '').strip()
            supplier_type = request.POST.get('type', 'supplier')
            
            # المعلومات المالية
            credit_limit = request.POST.get('credit_limit', 0)
            balance = request.POST.get('balance', 0)
            
            # معلومات إضافية
            is_active = request.POST.get('is_active') == 'on'
            
            # تحويل القيم المالية
            from decimal import Decimal
            try:
                credit_limit = Decimal(str(credit_limit)) if credit_limit else Decimal('0')
                balance = Decimal(str(balance)) if balance else Decimal('0')
            except (ValueError, Exception):
                credit_limit = Decimal('0')
                balance = Decimal('0')
            
            print(f"محاولة إنشاء مورد جديد: {name}")  # للتتبع
            
            # التحقق من البيانات المطلوبة
            if not name:
                return JsonResponse({
                    'success': False,
                    'message': 'Supplier name is required'
                })
            
            if not city:
                return JsonResponse({
                    'success': False,
                    'message': 'المدينة مطلوبة'
                })
            
            # التحقق من عدم تكرار الاسم
            if CustomerSupplier.objects.filter(name=name).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'A supplier with this name already exists'
                })
            
            # إنشاء المورد الجديد
            supplier = CustomerSupplier.objects.create(
                name=name,
                phone=phone,
                email=email,
                tax_number=tax_number,
                address=address,
                city=city,
                notes=notes,
                type=supplier_type,
                credit_limit=credit_limit,
                balance=balance,
                is_active=is_active
            )
            
            print(f"تم إنشاء المورد: {supplier.name} بـ ID: {supplier.id}")
            
            return JsonResponse({
                'success': True,
                'message': 'Supplier created successfully',
                'supplier': {
                    'id': supplier.id,
                    'name': supplier.name,
                    'phone': supplier.phone,
                    'email': supplier.email
                }
            })
            
    except Exception as e:
        print(f"خطأ في إنشاء المورد: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'An error occurred while creating supplier: {str(e)}'
        })


@login_required
@csrf_exempt  
def ajax_add_customer(request):
    """إضافة عميل جديد عبر AJAX"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Request method is incorrect'
        })
    
    # التحقق من الصلاحيات
    if not request.user.has_perm('customers.can_add_customers'):
        return JsonResponse({
            'success': False,
            'message': 'ليس لديك صلاحية لإضافة عملاء'
        })
    
    try:
        with transaction.atomic():
            # استلام البيانات
            name = request.POST.get('name', '').strip()
            phone = request.POST.get('phone', '').strip()
            email = request.POST.get('email', '').strip()
            tax_number = request.POST.get('tax_number', '').strip()
            address = request.POST.get('address', '').strip()
            city = request.POST.get('city', '').strip()
            notes = request.POST.get('notes', '').strip()
            customer_type = request.POST.get('type', 'customer')
            
            # المعلومات المالية
            credit_limit = request.POST.get('credit_limit', 0)
            balance = request.POST.get('balance', 0)
            
            # معلومات إضافية
            is_active = request.POST.get('is_active') == 'on'
            
            # تحويل القيم المالية
            from decimal import Decimal
            try:
                credit_limit = Decimal(str(credit_limit)) if credit_limit else Decimal('0')
                balance = Decimal(str(balance)) if balance else Decimal('0')
            except (ValueError, Exception):
                credit_limit = Decimal('0')
                balance = Decimal('0')
            
            print(f"محاولة إنشاء عميل جديد: {name}, city: {city}, type: {customer_type}")  # للتتبع
            print(f"البيانات المستلمة: credit_limit={credit_limit}, balance={balance}, is_active={is_active}")
            
            # التحقق من البيانات المطلوبة
            if not name:
                return JsonResponse({
                    'success': False,
                    'message': 'اسم العميل مطلوب'
                })
            
            if not city:
                return JsonResponse({
                    'success': False,
                    'message': 'المدينة مطلوبة'
                })
            
            # التحقق من عدم تكرار الاسم
            if CustomerSupplier.objects.filter(name=name).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'عميل بهذا الاسم موجود بالفعل'
                })
            
            # إنشاء العميل الجديد
            customer = CustomerSupplier.objects.create(
                name=name,
                phone=phone,
                email=email,
                tax_number=tax_number,
                address=address,
                city=city,
                notes=notes,
                type=customer_type,
                credit_limit=credit_limit,
                balance=balance,
                is_active=is_active
            )
            
            print(f"تم إنشاء العميل: {customer.name} بـ ID: {customer.id}")
            
            return JsonResponse({
                'success': True,
                'message': 'تم إنشاء العميل بنجاح',
                'customer': {
                    'id': customer.id,
                    'name': str(customer.name or ''),
                    'phone': str(customer.phone or ''),
                    'email': str(customer.email or '')
                }
            })
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"خطأ في إنشاء العميل: {str(e)}")
        print(f"Traceback: {error_details}")
        # تأكد من إرجاع JSON response دائماً
        try:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred while creating customer: {str(e)}'
            }, status=500)
        except Exception as json_error:
            # في حالة فشل إنشاء JSON، أرجع response نصي
            print(f"خطأ في إنشاء JSON response: {json_error}")
            from django.http import HttpResponse
            return HttpResponse('{"success": false, "message": "Internal server error"}', 
                              content_type='application/json', status=500)


@login_required
def preview_transaction_document(request, customer_pk, transaction_id):
    """معاينة المستند المرتبط بالمعاملة"""
    from accounts.models import AccountTransaction
    from django.http import Http404
    from django.contrib import messages
    from django.shortcuts import redirect
    
    try:
        # التحقق من صحة المعاملة والعميل
        customer_supplier = get_object_or_404(CustomerSupplier, pk=customer_pk)
        transaction = get_object_or_404(AccountTransaction, id=transaction_id, customer_supplier=customer_supplier)
        
        # تسجيل النشاط
        from core.models import AuditLog
        AuditLog.objects.create(
            user=request.user,
            action_type='view',
            content_type='AccountTransaction',
            object_id=transaction.id,
            description=f'Preview transaction document {transaction.transaction_number} for customer/supplier {customer_supplier.name}',
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # التحقق من وجود مرجع صالح
        if not transaction.reference_type or not transaction.reference_id:
            if transaction.transaction_type == 'adjustment':
                messages.info(request, f'This is a balance adjustment transaction: {transaction.description}')
            else:
                messages.info(request, _('This transaction does not have a related document to preview'))
            return redirect('customers:transactions', pk=customer_pk)
        
        # تحديد نوع المستند والمسار المناسب
        document_found = False
        
        if transaction.reference_type == 'sales_invoice':
            from sales.models import SalesInvoice
            try:
                invoice = SalesInvoice.objects.get(id=transaction.reference_id)
                messages.success(request, f'Opened sales invoice number {invoice.invoice_number}')
                return redirect('sales:invoice_detail', pk=invoice.id)
            except SalesInvoice.DoesNotExist:
                messages.error(request, f'Sales invoice related to this transaction (ID: {transaction.reference_id}) not found in system')
                
        elif transaction.reference_type == 'purchase_invoice':
            from purchases.models import PurchaseInvoice
            try:
                invoice = PurchaseInvoice.objects.get(id=transaction.reference_id)
                messages.success(request, f'Opened purchase invoice number {invoice.invoice_number}')
                return redirect('purchases:invoice_detail', pk=invoice.id)
            except PurchaseInvoice.DoesNotExist:
                messages.error(request, f'Purchase invoice related to this transaction (ID: {transaction.reference_id}) not found in system')
                
        elif transaction.reference_type == 'sales_return':
            from sales.models import SalesReturn
            try:
                return_doc = SalesReturn.objects.get(id=transaction.reference_id)
                messages.success(request, f'Opened sales return number {return_doc.return_number}')
                return redirect('sales:return_detail', pk=return_doc.id)
            except SalesReturn.DoesNotExist:
                messages.error(request, f'Sales return related to this transaction (ID: {transaction.reference_id}) not found in system')
                
        elif transaction.reference_type == 'purchase_return':
            from purchases.models import PurchaseReturn
            try:
                return_doc = PurchaseReturn.objects.get(id=transaction.reference_id)
                messages.success(request, f'Opened purchase return number {return_doc.return_number}')
                return redirect('purchases:return_detail', pk=return_doc.id)
            except PurchaseReturn.DoesNotExist:
                messages.error(request, f'Purchase return related to this transaction (ID: {transaction.reference_id}) not found in system')
                
        elif transaction.reference_type == 'debit_note':
            from purchases.models import PurchaseDebitNote
            try:
                debit_note = PurchaseDebitNote.objects.get(id=transaction.reference_id)
                messages.success(request, f'Opened debit note number {debit_note.note_number}')
                return redirect('purchases:debitnote_detail', pk=debit_note.id)
            except PurchaseDebitNote.DoesNotExist:
                messages.error(request, f'Debit note related to this transaction (ID: {transaction.reference_id}) not found in system')
                
        elif transaction.reference_type == 'credit_note':
            from sales.models import SalesCreditNote
            try:
                credit_note = SalesCreditNote.objects.get(id=transaction.reference_id)
                messages.success(request, f'Opened credit note number {credit_note.note_number}')
                return redirect('sales:creditnote_detail', pk=credit_note.id)
            except SalesCreditNote.DoesNotExist:
                messages.error(request, f'Credit note related to this transaction (ID: {transaction.reference_id}) not found in system')
                
        elif transaction.reference_type == 'payment':
            from payments.models import PaymentVoucher
            try:
                payment = PaymentVoucher.objects.get(id=transaction.reference_id)
                messages.success(request, f'Opened payment voucher number {payment.voucher_number}')
                return redirect('payments:detail', pk=payment.id)
            except PaymentVoucher.DoesNotExist:
                messages.error(request, f'Payment voucher related to this transaction (ID: {transaction.reference_id}) not found in system')
                
        elif transaction.reference_type == 'receipt':
            from receipts.models import PaymentReceipt
            try:
                receipt = PaymentReceipt.objects.get(id=transaction.reference_id)
                messages.success(request, f'Opened payment receipt number {receipt.receipt_number}')
                return redirect('receipts:detail', pk=receipt.id)
            except PaymentReceipt.DoesNotExist:
                messages.error(request, f'Payment receipt related to this transaction (ID: {transaction.reference_id}) not found in system')
                
        else:
            messages.warning(request, f'Document type "{transaction.reference_type}" not currently supported for preview')
            
    except Exception as e:
        messages.error(request, f'An error occurred while trying to preview document: {str(e)}')
        # تسجيل الخطأ في سجل الأنشطة
        try:
            from core.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action_type='error',
                content_type='AccountTransaction',
                object_id=transaction_id,
                description=f'Error previewing transaction document {transaction_id}: {str(e)}',
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
        except:
            pass  # تجاهل الأخطاء في تسجيل الخطأ
    
    # العودة إلى صفحة المعاملات
    return redirect('customers:transactions', pk=customer_pk)


@login_required
def delete_transaction(request, customer_pk, transaction_id):
    """حذف معاملة فردية"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': _('Method not allowed')}, status=405)
    
    # التحقق من الصلاحيات - فقط للسوبر أدمين
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': _('You do not have permission to delete transactions')}, status=403)
    
    try:
        # التحقق من صحة العميل/المورد والمعاملة
        customer_supplier = get_object_or_404(CustomerSupplier, pk=customer_pk)
        transaction = get_object_or_404(AccountTransaction, id=transaction_id, customer_supplier=customer_supplier)
        
        # حفظ بيانات المعاملة للتسجيل
        transaction_data = {
            'number': transaction.transaction_number,
            'amount': str(transaction.amount),
            'type': transaction.transaction_type,
            'description': transaction.description
        }
        
        # حذف المعاملة
        transaction.delete()
        
        # إعادة حساب رصيد العميل/المورد
        from accounts.services import recalculate_customer_supplier_balance
        recalculate_customer_supplier_balance(customer_supplier)
        
        # تسجيل النشاط في سجل الأنشطة
        from core.models import AuditLog
        AuditLog.objects.create(
            user=request.user,
            action_type='delete',
            content_type='AccountTransaction',
            object_id=transaction_id,
            description=f'Delete transaction {transaction_data["number"]} for customer/supplier {customer_supplier.name} - Amount: {transaction_data["amount"]} - Type: {transaction_data["type"]}',
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'Transaction {transaction_data["number"]} deleted successfully'
        })
        
    except Exception as e:
        # تسجيل الخطأ في سجل الأنشطة
        try:
            from core.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action_type='error',
                content_type='AccountTransaction',
                object_id=transaction_id,
                description=f'Error deleting transaction {transaction_id}: {str(e)}',
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
        except:
            pass  # تجاهل الأخطاء في تسجيل الخطأ
        
        return JsonResponse({'success': False, 'error': f'An error occurred while deleting transaction: {str(e)}'}, status=500)
