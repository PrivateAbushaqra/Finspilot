from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib import messages
from django.urls import reverse_lazy
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
            
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
            
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
        total_debt = 0
        customer_credit = 0
        total_balance = 0
        
        for customer in all_customers:
            balance = customer.current_balance
            total_balance += balance
            if balance < 0:
                total_debt += abs(balance)
            elif balance > 0:
                customer_credit += balance
        
        context.update({
            'total_customers': all_customers.count(),
            'active_customers': all_customers.filter(is_active=True).count(),
            'total_debt': total_debt,  # المديونية (قيمة موجبة)
            'customer_credit': customer_credit,  # الأرصدة الدائنة
            'total_balance': total_balance,  # إجمالي الأرصدة
            'average_balance': total_balance / all_customers.count() if all_customers.count() > 0 else 0,
        })
        
        return context

class SupplierListView(LoginRequiredMixin, ListView):
    model = CustomerSupplier
    template_name = 'customers/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 20
    
    def get_queryset(self):
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
            
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
            
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
        return render(request, self.template_name)
    
    def post(self, request, *args, **kwargs):
        try:
            # الحصول على البيانات من النموذج
            name = request.POST.get('name', '').strip()
            type_value = request.POST.get('type', 'customer')
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
                messages.error(request, 'اسم العميل/المورد مطلوب!')
                return render(request, self.template_name)
            
            if not city:
                messages.error(request, 'المدينة مطلوبة!')
                return render(request, self.template_name)
            
            # التحقق من عدم وجود اسم مكرر
            if CustomerSupplier.objects.filter(name=name).exists():
                messages.error(request, f'يوجد عميل/مورد بنفس الاسم "{name}" مسبقاً!')
                return render(request, self.template_name)
            
            # تحويل الأرقام المالية
            try:
                credit_limit = float(credit_limit) if credit_limit else 0
                balance = float(balance) if balance else 0
            except ValueError:
                messages.error(request, 'قيم المبالغ المالية غير صحيحة!')
                return render(request, self.template_name)
            
            # إنشاء العميل/المورد الجديد
            customer_supplier = CustomerSupplier.objects.create(
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
                f'تم إنشاء {type_display} "{name}" بنجاح!\n'
                f'رقم الحساب: {customer_supplier.id}\n'
                f'الرصيد الابتدائي: {balance:.3f} {currency_symbol}'
            )
            
            # إعادة توجيه حسب النوع
            if type_value == 'customer':
                return redirect('customers:customer_list')
            elif type_value == 'supplier':
                return redirect('customers:supplier_list')
            else:
                return redirect('customers:list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حفظ البيانات: {str(e)}')
            return render(request, self.template_name)

class CustomerSupplierUpdateView(LoginRequiredMixin, View):
    template_name = 'customers/edit.html'
    
    def get(self, request, pk, *args, **kwargs):
        customer_supplier = get_object_or_404(CustomerSupplier, pk=pk)
        
        # حساب الائتمان المتاح
        available_credit = customer_supplier.credit_limit - abs(customer_supplier.balance) if customer_supplier.balance < 0 else customer_supplier.credit_limit
        
        context = {
            'customer_supplier': customer_supplier,
            'available_credit': available_credit
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk, *args, **kwargs):
        customer_supplier = get_object_or_404(CustomerSupplier, pk=pk)
        
        try:
            # الحصول على البيانات من النموذج
            name = request.POST.get('name', '').strip()
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
                messages.error(request, 'اسم العميل/المورد مطلوب!')
                return redirect('customers:edit', pk=pk)
            
            if not city:
                messages.error(request, 'المدينة مطلوبة!')
                return redirect('customers:edit', pk=pk)
            
            # التحقق من عدم وجود اسم مكرر (باستثناء نفس الحساب)
            if CustomerSupplier.objects.filter(name=name).exclude(pk=pk).exists():
                messages.error(request, f'يوجد عميل/مورد آخر بنفس الاسم "{name}"!')
                return redirect('customers:edit', pk=pk)
            
            # تحويل الأرقام المالية
            try:
                credit_limit = float(credit_limit) if credit_limit else 0
                balance = float(balance) if balance else 0
            except ValueError:
                messages.error(request, 'قيم المبالغ المالية غير صحيحة!')
                return redirect('customers:edit', pk=pk)
            
            # تحديث البيانات
            customer_supplier.name = name
            customer_supplier.email = email
            customer_supplier.phone = phone
            customer_supplier.address = address
            customer_supplier.city = city
            customer_supplier.tax_number = tax_number
            customer_supplier.credit_limit = credit_limit
            customer_supplier.balance = balance
            customer_supplier.notes = notes
            customer_supplier.is_active = is_active
            customer_supplier.save()
            
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
                f'تم تحديث {type_display} "{name}" بنجاح!\n'
                f'الرصيد الجديد: {balance:.3f} {currency_symbol}'
            )
            
            # إعادة توجيه حسب النوع
            if customer_supplier.type == 'customer':
                return redirect('customers:customer_list')
            elif customer_supplier.type == 'supplier':
                return redirect('customers:supplier_list')
            else:
                return redirect('customers:list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تحديث البيانات: {str(e)}')
            return redirect('customers:edit', pk=pk)

class CustomerSupplierDeleteView(LoginRequiredMixin, View):
    template_name = 'customers/delete.html'
    
    def get(self, request, pk, *args, **kwargs):
        customer_supplier = get_object_or_404(CustomerSupplier, pk=pk)
        
        # التحقق من الصلاحيات - فقط للسوبر أدمين
        if not request.user.is_superuser:
            messages.error(request, _('ليس لديك صلاحية لحذف العملاء/الموردين'))
            return redirect('customers:detail', pk=pk)
        
        # فحص البيانات المرتبطة
        related_data = self._get_related_data_count(customer_supplier)
        
        context = {
            'customer_supplier': customer_supplier,
            'related_data': related_data,
            'can_delete': True,  # السوبر أدمين يمكنه الحذف دائماً
            'warning_message': _('تحذير: سيتم حذف جميع البيانات المرتبطة نهائياً!') if any(related_data.values()) else None
        }
        return render(request, self.template_name, context)
    
    def _get_related_data_count(self, customer_supplier):
        """حساب عدد البيانات المرتبطة"""
        from sales.models import SalesInvoice, SalesReturn
        from purchases.models import PurchaseInvoice, PurchaseReturn
        from accounts.models import AccountTransaction
        
        return {
            'sales_invoices': SalesInvoice.objects.filter(customer=customer_supplier).count(),
            'purchase_invoices': PurchaseInvoice.objects.filter(supplier=customer_supplier).count(),
            'sales_returns': SalesReturn.objects.filter(customer=customer_supplier).count(),
            'purchase_returns': PurchaseReturn.objects.filter(original_invoice__supplier=customer_supplier).count(),
            'transactions': AccountTransaction.objects.filter(customer_supplier=customer_supplier).count(),
        }
    
    def post(self, request, pk, *args, **kwargs):
        customer_supplier = get_object_or_404(CustomerSupplier, pk=pk)
        
        try:
            # التحقق من تأكيد الحذف
            confirm = request.POST.get('confirm_delete')
            if confirm != 'DELETE':
                messages.error(request, _('يجب كتابة "DELETE" للتأكيد!'))
                return redirect('customers:delete', pk=pk)
            
            # التحقق من الصلاحيات - فقط للسوبر أدمين
            if not request.user.is_superuser:
                messages.error(request, _('ليس لديك صلاحية لحذف العملاء/الموردين'))
                return redirect('customers:delete', pk=pk)
            
            # حفظ البيانات للرسالة والتدقيق
            name = customer_supplier.name
            type_display = customer_supplier.get_type_display()
            customer_id = customer_supplier.id
            
            # الحذف الإجباري باستخدام Raw SQL مباشرة
            self._force_delete_customer_supplier(customer_supplier)
            
            # تسجيل عملية الحذف في سجل الأنشطة
            from core.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action_type='delete',
                content_type='CustomerSupplier',
                object_id=customer_id,
                description=_('تم حذف العميل/المورد وجميع البيانات المرتبطة نهائياً: %(name)s (%(type)s)') % {'name': name, 'type': type_display},
                ip_address=self.get_client_ip(request)
            )
            
            # رسالة نجاح
            messages.success(
                request, 
                _('تم حذف %(type)s "%(name)s" بنجاح!\nجميع البيانات المرتبطة تم حذفها نهائياً.') % {'type': type_display, 'name': name}
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
                description=_('فشل حذف العميل/المورد: %(error)s') % {'error': str(e)},
                ip_address=self.get_client_ip(request)
            )
            
            messages.error(request, _('حدث خطأ أثناء حذف البيانات: %(error)s') % {'error': str(e)})
            return redirect('customers:delete', pk=pk)
    
    def _force_delete_customer_supplier(self, customer_supplier):
        """حذف إجباري للعميل/المورد وجميع بياناته بـ Raw SQL"""
        from django.db import connection, transaction
        
        with transaction.atomic():
            with connection.cursor() as cursor:
                customer_id = customer_supplier.id
                
                # 1. حذف مردودات الشراء والمبيعات
                cursor.execute("""
                    DELETE FROM purchases_purchasereturnitem 
                    WHERE return_invoice_id IN (
                        SELECT id FROM purchases_purchasereturn 
                        WHERE original_invoice_id IN (
                            SELECT id FROM purchases_purchaseinvoice WHERE supplier_id = %s
                        )
                    )
                """, [customer_id])
                
                cursor.execute("""
                    DELETE FROM purchases_purchasereturn 
                    WHERE original_invoice_id IN (
                        SELECT id FROM purchases_purchaseinvoice WHERE supplier_id = %s
                    )
                """, [customer_id])
                
                cursor.execute("""
                    DELETE FROM sales_salesreturnitem 
                    WHERE return_invoice_id IN (
                        SELECT id FROM sales_salesreturn 
                        WHERE customer_id = %s
                    )
                """, [customer_id])
                
                cursor.execute("""
                    DELETE FROM sales_salesreturn WHERE customer_id = %s
                """, [customer_id])
                
                # حذف إشعارات خصم المشتريات
                cursor.execute("""
                    DELETE FROM purchases_purchasedebitnote WHERE supplier_id = %s
                """, [customer_id])
                
                # حذف إشعارات ائتمان المبيعات
                cursor.execute("""
                    DELETE FROM sales_salescreditnote WHERE customer_id = %s
                """, [customer_id])
                
                # 2. حذف حركات المخزون المرتبطة
                cursor.execute("""
                    DELETE FROM inventory_inventorymovement 
                    WHERE reference_id IN (
                        SELECT id FROM purchases_purchaseinvoice WHERE supplier_id = %s
                    ) AND reference_type = 'purchase_invoice'
                """, [customer_id])
                
                cursor.execute("""
                    DELETE FROM inventory_inventorymovement 
                    WHERE reference_id IN (
                        SELECT id FROM sales_salesinvoice WHERE customer_id = %s
                    ) AND reference_type = 'sales_invoice'
                """, [customer_id])
                
                # 3. حذف عناصر الفواتير
                cursor.execute("""
                    DELETE FROM purchases_purchaseinvoiceitem 
                    WHERE invoice_id IN (
                        SELECT id FROM purchases_purchaseinvoice WHERE supplier_id = %s
                    )
                """, [customer_id])
                
                cursor.execute("""
                    DELETE FROM sales_salesinvoiceitem 
                    WHERE invoice_id IN (
                        SELECT id FROM sales_salesinvoice WHERE customer_id = %s
                    )
                """, [customer_id])
                
                # 4. حذف الفواتير نفسها (تجاوز PROTECT)
                cursor.execute("""
                    DELETE FROM purchases_purchaseinvoice WHERE supplier_id = %s
                """, [customer_id])
                
                cursor.execute("""
                    DELETE FROM sales_salesinvoice WHERE customer_id = %s
                """, [customer_id])
                
                # 5. حذف معاملات الحساب
                cursor.execute("""
                    DELETE FROM accounts_accounttransaction WHERE customer_supplier_id = %s
                """, [customer_id])
                
                # 6. حذف أي حركات مخزون مرتبطة بفواتير هذا العميل/المورد
                # (حركات المخزون لا تربط مباشرة بالعميل/المورد بل بالفواتير)
                # تم حذفها بالفعل عندما تم حذف الفواتير أعلاه
                
                # 7. أخيراً حذف العميل/المورد نفسه
                cursor.execute("""
                    DELETE FROM customers_customersupplier WHERE id = %s
                """, [customer_id])
    
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
            
            # حساب الإحصائيات
            total_debit = transactions.filter(direction='debit').aggregate(
                total=Sum('amount'))['total'] or 0
            total_credit = transactions.filter(direction='credit').aggregate(
                total=Sum('amount'))['total'] or 0
            
            current_balance = total_debit - total_credit
            
            context.update({
                'customer_supplier': customer_supplier,
                'transactions': transactions,
                'opening_balance': 0,  # يمكن حسابه لاحقاً
                'closing_balance': current_balance,
                'total_debit': total_debit,
                'total_credit': total_credit,
                'total_transactions': transactions.count(),
                'date_from': date_from,
                'date_to': date_to,
            })
            
        except ImportError as e:
            # في حالة عدم وجود نموذج الحسابات
            context.update({
                'customer_supplier': customer_supplier,
                'transactions': [],
                'opening_balance': 0,
                'closing_balance': customer_supplier.balance,
                'total_debit': 0,
                'total_credit': 0,
                'total_transactions': 0,
                'date_from': date_from,
                'date_to': date_to,
                'error_message': 'نموذج الحسابات غير متوفر'
            })
        except Exception as e:
            context.update({
                'customer_supplier': customer_supplier,
                'transactions': [],
                'opening_balance': 0,
                'closing_balance': customer_supplier.balance,
                'total_debit': 0,
                'total_credit': 0,
                'total_transactions': 0,
                'date_from': date_from,
                'date_to': date_to,
                'error_message': f'خطأ في تحميل البيانات: {str(e)}'
            })
        
        return context

# API للحصول على بيانات العميل/المورد عبر AJAX
def get_customer_supplier_ajax(request, customer_id):
    if not customer_id:
        return JsonResponse({'error': 'معرف العميل/المورد مطلوب'}, status=400)
    
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
        return JsonResponse({'error': 'العميل/المورد غير موجود'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def delete_transaction(request, customer_pk, transaction_id):
    """حذف حركة - للمدراء فقط"""
    
    # التحقق من أن المستخدم مدير عام
    if not request.user.is_superuser:
        return JsonResponse({
            'success': False,
            'error': 'غير مسموح لك بحذف الحركات'
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
            'message': f'تم حذف الحركة {transaction_number} بنجاح'
        })
        
    except AccountTransaction.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'الحركة غير موجودة'
        }, status=404)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'خطأ في حذف الحركة: {str(e)}'
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
            try:
                credit_limit = float(credit_limit) if credit_limit else 0
                balance = float(balance) if balance else 0
            except ValueError:
                credit_limit = 0
                balance = 0
            
            print(f"محاولة إنشاء مورد جديد: {name}")  # للتتبع
            
            # التحقق من البيانات المطلوبة
            if not name:
                return JsonResponse({
                    'success': False,
                    'message': 'اسم المورد مطلوب'
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
                    'message': 'مورد بهذا الاسم موجود بالفعل'
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
                'message': 'تم إنشاء المورد بنجاح',
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
            'message': f'حدث خطأ أثناء إنشاء المورد: {str(e)}'
        })


@login_required
@csrf_exempt  
def ajax_add_customer(request):
    """إضافة عميل جديد عبر AJAX"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'طريقة الطلب غير صحيحة'
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
            try:
                credit_limit = float(credit_limit) if credit_limit else 0
                balance = float(balance) if balance else 0
            except ValueError:
                credit_limit = 0
                balance = 0
            
            print(f"محاولة إنشاء عميل جديد: {name}")  # للتتبع
            
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
                    'name': customer.name,
                    'phone': customer.phone,
                    'email': customer.email
                }
            })
            
    except Exception as e:
        print(f"خطأ في إنشاء العميل: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ أثناء إنشاء العميل: {str(e)}'
        })


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
            description=f'معاينة مستند المعاملة {transaction.transaction_number} للعميل/المورد {customer_supplier.name}',
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # التحقق من وجود مرجع صالح
        if not transaction.reference_type or not transaction.reference_id:
            if transaction.transaction_type == 'adjustment':
                messages.info(request, f'هذه معاملة تسوية رصيد: {transaction.description}')
            else:
                messages.info(request, 'هذه المعاملة لا تحتوي على مستند مرتبط للمعاينة')
            return redirect('customers:transactions', pk=customer_pk)
        
        # تحديد نوع المستند والمسار المناسب
        document_found = False
        
        if transaction.reference_type == 'sales_invoice':
            from sales.models import SalesInvoice
            try:
                invoice = SalesInvoice.objects.get(id=transaction.reference_id)
                messages.success(request, f'تم فتح فاتورة المبيعات رقم {invoice.invoice_number}')
                return redirect('sales:invoice_detail', pk=invoice.id)
            except SalesInvoice.DoesNotExist:
                messages.error(request, f'فاتورة المبيعات المرتبطة بهذه المعاملة (ID: {transaction.reference_id}) غير موجودة في النظام')
                
        elif transaction.reference_type == 'purchase_invoice':
            from purchases.models import PurchaseInvoice
            try:
                invoice = PurchaseInvoice.objects.get(id=transaction.reference_id)
                messages.success(request, f'تم فتح فاتورة المشتريات رقم {invoice.invoice_number}')
                return redirect('purchases:invoice_detail', pk=invoice.id)
            except PurchaseInvoice.DoesNotExist:
                messages.error(request, f'فاتورة المشتريات المرتبطة بهذه المعاملة (ID: {transaction.reference_id}) غير موجودة في النظام')
                
        elif transaction.reference_type == 'sales_return':
            from sales.models import SalesReturn
            try:
                return_doc = SalesReturn.objects.get(id=transaction.reference_id)
                messages.success(request, f'تم فتح مردود المبيعات رقم {return_doc.return_number}')
                return redirect('sales:return_detail', pk=return_doc.id)
            except SalesReturn.DoesNotExist:
                messages.error(request, f'مردود المبيعات المرتبط بهذه المعاملة (ID: {transaction.reference_id}) غير موجود في النظام')
                
        elif transaction.reference_type == 'purchase_return':
            from purchases.models import PurchaseReturn
            try:
                return_doc = PurchaseReturn.objects.get(id=transaction.reference_id)
                messages.success(request, f'تم فتح مردود المشتريات رقم {return_doc.return_number}')
                return redirect('purchases:return_detail', pk=return_doc.id)
            except PurchaseReturn.DoesNotExist:
                messages.error(request, f'مردود المشتريات المرتبط بهذه المعاملة (ID: {transaction.reference_id}) غير موجود في النظام')
                
        elif transaction.reference_type == 'debit_note':
            from purchases.models import PurchaseDebitNote
            try:
                debit_note = PurchaseDebitNote.objects.get(id=transaction.reference_id)
                messages.success(request, f'تم فتح مذكرة الدين رقم {debit_note.note_number}')
                return redirect('purchases:debitnote_detail', pk=debit_note.id)
            except PurchaseDebitNote.DoesNotExist:
                messages.error(request, f'مذكرة الدين المرتبطة بهذه المعاملة (ID: {transaction.reference_id}) غير موجودة في النظام')
                
        elif transaction.reference_type == 'credit_note':
            from sales.models import SalesCreditNote
            try:
                credit_note = SalesCreditNote.objects.get(id=transaction.reference_id)
                messages.success(request, f'تم فتح مذكرة ائتمان رقم {credit_note.note_number}')
                return redirect('sales:creditnote_detail', pk=credit_note.id)
            except SalesCreditNote.DoesNotExist:
                messages.error(request, f'مذكرة الائتمان المرتبطة بهذه المعاملة (ID: {transaction.reference_id}) غير موجودة في النظام')
                
        elif transaction.reference_type == 'payment':
            from payments.models import PaymentVoucher
            try:
                payment = PaymentVoucher.objects.get(id=transaction.reference_id)
                messages.success(request, f'تم فتح سند الدفع رقم {payment.voucher_number}')
                return redirect('payments:detail', pk=payment.id)
            except PaymentVoucher.DoesNotExist:
                messages.error(request, f'سند الدفع المرتبط بهذه المعاملة (ID: {transaction.reference_id}) غير موجود في النظام')
                
        elif transaction.reference_type == 'receipt':
            from receipts.models import PaymentReceipt
            try:
                receipt = PaymentReceipt.objects.get(id=transaction.reference_id)
                messages.success(request, f'تم فتح سند القبض رقم {receipt.receipt_number}')
                return redirect('receipts:detail', pk=receipt.id)
            except PaymentReceipt.DoesNotExist:
                messages.error(request, f'سند القبض المرتبط بهذه المعاملة (ID: {transaction.reference_id}) غير موجود في النظام')
                
        else:
            messages.warning(request, f'نوع المستند "{transaction.reference_type}" غير مدعوم للمعاينة حالياً')
            
    except Exception as e:
        messages.error(request, f'حدث خطأ أثناء محاولة معاينة المستند: {str(e)}')
        # تسجيل الخطأ في سجل الأنشطة
        try:
            from core.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action_type='error',
                content_type='AccountTransaction',
                object_id=transaction_id,
                description=f'خطأ في معاينة مستند المعاملة {transaction_id}: {str(e)}',
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
        except:
            pass  # تجاهل الأخطاء في تسجيل الخطأ
    
    # العودة إلى صفحة المعاملات
    return redirect('customers:transactions', pk=customer_pk)
