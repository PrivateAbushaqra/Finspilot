from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.db.models import Q, Sum
from django.http import JsonResponse
from datetime import datetime, date
from customers.models import CustomerSupplier
from .models import AccountTransaction


class LoginView(auth_views.LoginView):
    """صفحة تسجيل الدخول"""
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        # إذا كان المستخدم من نوع "مستخدم نقطة بيع"، توجيهه إلى شاشة نقطة البيع
        if (self.request.user.is_authenticated and 
            hasattr(self.request.user, 'user_type') and 
            self.request.user.user_type == 'pos_user'):
            return reverse_lazy('sales:pos')
        
        # للمستخدمين العاديين، توجيهه إلى الصفحة الرئيسية
        return reverse_lazy('core:dashboard')


@login_required
def customer_account_statement(request, customer_id):
    """كشف حساب العميل/المورد"""
    customer = get_object_or_404(CustomerSupplier, id=customer_id)
    
    # الحصول على جميع المعاملات
    transactions = AccountTransaction.objects.filter(
        customer_supplier=customer
    ).order_by('date', 'created_at')
    
    # فلترة حسب التاريخ إذا تم تحديدها
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            transactions = transactions.filter(date__gte=date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            transactions = transactions.filter(date__lte=date_to)
        except ValueError:
            pass
    
    # حساب الإحصائيات
    total_debit = transactions.filter(direction='debit').aggregate(
        total=Sum('amount'))['total'] or 0
    total_credit = transactions.filter(direction='credit').aggregate(
        total=Sum('amount'))['total'] or 0
    
    current_balance = total_debit - total_credit
    
    context = {
        'customer': customer,
        'transactions': transactions,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'current_balance': current_balance,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'accounts/customer_statement.html', context)


class AccountTransactionListView(LoginRequiredMixin, ListView):
    """قائمة جميع المعاملات المالية"""
    model = AccountTransaction
    template_name = 'accounts/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = AccountTransaction.objects.select_related(
            'customer_supplier', 'created_by'
        ).order_by('-date', '-created_at')
        
        # البحث
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(transaction_number__icontains=search) |
                Q(customer_supplier__name__icontains=search) |
                Q(description__icontains=search)
            )
        
        # فلترة حسب نوع المعاملة
        transaction_type = self.request.GET.get('transaction_type')
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        
        # فلترة حسب الاتجاه
        direction = self.request.GET.get('direction')
        if direction:
            queryset = queryset.filter(direction=direction)
        
        # فلترة حسب التاريخ
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=date_from)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(date__lte=date_to)
            except ValueError:
                pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # إحصائيات
        all_transactions = AccountTransaction.objects.all()
        context['total_transactions'] = all_transactions.count()
        
        context['total_debit'] = all_transactions.filter(
            direction='debit').aggregate(total=Sum('amount'))['total'] or 0
        context['total_credit'] = all_transactions.filter(
            direction='credit').aggregate(total=Sum('amount'))['total'] or 0
        
        # خيارات الفلترة
        context['transaction_types'] = AccountTransaction.TRANSACTION_TYPES
        context['directions'] = AccountTransaction.DIRECTION_TYPES
        
        return context


@login_required
def create_account_transactions_for_existing_invoices(request):
    """إنشاء معاملات حسابية للفواتير الموجودة"""
    if request.method == 'POST':
        try:
            from sales.models import SalesInvoice
            from purchases.models import PurchaseInvoice
            from sales.views import create_sales_invoice_account_transaction
            from purchases.views import create_purchase_invoice_account_transaction
            
            created_count = 0
            
            # إنشاء معاملات لفواتير المبيعات
            sales_invoices = SalesInvoice.objects.filter(
                payment_type__ne='cash'
            ).exclude(
                id__in=AccountTransaction.objects.filter(
                    reference_type='sales_invoice'
                ).values_list('reference_id', flat=True)
            )
            
            for invoice in sales_invoices:
                if invoice.customer:
                    create_sales_invoice_account_transaction(invoice, request.user)
                    created_count += 1
            
            # إنشاء معاملات لفواتير المشتريات
            purchase_invoices = PurchaseInvoice.objects.filter(
                payment_type__ne='cash'
            ).exclude(
                id__in=AccountTransaction.objects.filter(
                    reference_type='purchase_invoice'
                ).values_list('reference_id', flat=True)
            )
            
            for invoice in purchase_invoices:
                if invoice.supplier:
                    create_purchase_invoice_account_transaction(invoice, request.user)
                    created_count += 1
            
            return JsonResponse({
                'success': True,
                'message': f'تم إنشاء {created_count} معاملة حسابية بنجاح',
                'created_count': created_count
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'حدث خطأ: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'طلب غير صحيح'})
