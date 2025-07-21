from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Q, Sum, Count
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db import transaction
from .models import CustomerSupplier
from django.core.paginator import Paginator

class CustomerSupplierListView(LoginRequiredMixin, TemplateView):
    template_name = 'customers/list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # إحصائيات العملاء والموردين
        total_customers = CustomerSupplier.objects.filter(type__in=['customer', 'both']).count()
        total_suppliers = CustomerSupplier.objects.filter(type__in=['supplier', 'both']).count()
        
        # إحصائيات العملاء
        customers = CustomerSupplier.objects.filter(type__in=['customer', 'both'])
        customer_balance = customers.aggregate(total=Sum('balance'))['total'] or 0
        customer_debit = customers.filter(balance__lt=0).aggregate(total=Sum('balance'))['total'] or 0
        customer_credit = customers.filter(balance__gt=0).aggregate(total=Sum('balance'))['total'] or 0
        
        # إحصائيات الموردين  
        suppliers = CustomerSupplier.objects.filter(type__in=['supplier', 'both'])
        supplier_balance = suppliers.aggregate(total=Sum('balance'))['total'] or 0
        supplier_debit = suppliers.filter(balance__lt=0).aggregate(total=Sum('balance'))['total'] or 0
        supplier_credit = suppliers.filter(balance__gt=0).aggregate(total=Sum('balance'))['total'] or 0
        
        context.update({
            'total_customers': total_customers,
            'total_suppliers': total_suppliers,
            'customer_balance': customer_balance,
            'supplier_balance': supplier_balance,
            'customer_debit': abs(customer_debit),  # المديونية (قيمة موجبة)
            'customer_credit': customer_credit,     # الأرصدة الدائنة
            'supplier_debit': abs(supplier_debit),  # المديونية (قيمة موجبة)
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
        context.update({
            'total_customers': all_customers.count(),
            'active_customers': all_customers.filter(is_active=True).count(),
            'total_debt': all_customers.aggregate(total=Sum('balance'))['total'] or 0,
            'average_balance': all_customers.aggregate(avg=Sum('balance'))['avg'] or 0,
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
        context.update({
            'total_suppliers': all_suppliers.count(),
            'active_suppliers': all_suppliers.filter(is_active=True).count(),
            'total_debt': all_suppliers.aggregate(total=Sum('balance'))['total'] or 0,
            'average_balance': all_suppliers.aggregate(avg=Sum('balance'))['avg'] or 0,
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
            tax_number = request.POST.get('tax_number', '').strip()
            credit_limit = request.POST.get('credit_limit', '0')
            balance = request.POST.get('balance', '0')
            notes = request.POST.get('notes', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            # التحقق من البيانات المطلوبة
            if not name:
                messages.error(request, 'اسم العميل/المورد مطلوب!')
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
            tax_number = request.POST.get('tax_number', '').strip()
            credit_limit = request.POST.get('credit_limit', '0')
            balance = request.POST.get('balance', '0')
            notes = request.POST.get('notes', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            # التحقق من البيانات المطلوبة
            if not name:
                messages.error(request, 'اسم العميل/المورد مطلوب!')
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
        
        # فحص البيانات المرتبطة (يمكن توسيعها لاحقاً)
        related_data = {
            'invoices': 0,  # سيتم ربطها بنماذج الفواتير لاحقاً
            'payments': 0,  # سيتم ربطها بنماذج المدفوعات لاحقاً
            'transactions': 0,  # سيتم ربطها بنماذج المعاملات لاحقاً
        }
        
        context = {
            'customer_supplier': customer_supplier,
            'related_data': related_data,
            'can_delete': not any(related_data.values())
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk, *args, **kwargs):
        customer_supplier = get_object_or_404(CustomerSupplier, pk=pk)
        
        try:
            # التحقق من تأكيد الحذف
            confirm = request.POST.get('confirm_delete')
            if confirm != 'DELETE':
                messages.error(request, 'يجب كتابة "DELETE" للتأكيد!')
                return redirect('customers:delete', pk=pk)
            
            # حفظ البيانات للرسالة
            name = customer_supplier.name
            type_display = customer_supplier.get_type_display()
            
            # حذف العميل/المورد
            customer_supplier.delete()
            
            # رسالة نجاح
            messages.success(
                request, 
                f'تم حذف {type_display} "{name}" بنجاح!\n'
                f'جميع البيانات المرتبطة تم حذفها نهائياً.'
            )
            
            return redirect('customers:list')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء حذف البيانات: {str(e)}')
            return redirect('customers:delete', pk=pk)

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
            
            # الحصول على المعاملات
            transactions = AccountTransaction.objects.filter(
                customer_supplier=customer_supplier
            ).order_by('date', 'created_at')
            
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
            
        except ImportError:
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
def get_customer_supplier_ajax(request):
    customer_id = request.GET.get('customer_id')
    
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
