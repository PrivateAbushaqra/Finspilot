from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, DetailView, View
from django.db.models import Sum, Count, Q
from django.db import models
from django.utils import timezone
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from core.signals import log_activity
import logging
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
import json
from .models import PurchaseInvoice, PurchaseInvoiceItem, PurchaseReturn, PurchaseReturnItem, PurchaseReturn, PurchaseReturnItem
from customers.models import CustomerSupplier
from products.models import Product, Category
from inventory.models import InventoryMovement, Warehouse
from cashboxes.models import Cashbox
from banks.models import BankAccount
from accounts.services import create_purchase_invoice_transaction, create_purchase_return_transaction, delete_transaction_by_reference
from journal.models import JournalEntry
from journal.services import JournalService
from core.models import DocumentSequence
from .models import PurchaseDebitNote
from decimal import Decimal
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from core.models import CompanySettings


def create_purchase_invoice_journal_entry(invoice, user):
    """إنشاء قيد محاسبي لفاتورة المشتريات"""
    try:
        # إنشاء القيد المحاسبي باستخدام JournalService
        JournalService.create_purchase_invoice_entry(invoice, user)
    except Exception as e:
        print(f"خطأ في إنشاء القيد المحاسبي لفاتورة المشتريات: {e}")
        # لا نوقف العملية في حالة فشل إنشاء القيد المحاسبي
        pass


def create_debit_note_journal_entry(debit_note, user):
    """إنشاء قيد محاسبي لمذكرة الدين"""
    try:
        from journal.services import JournalService
        from journal.models import Account
        from accounts.models import AccountTransaction
        from django.db import models
        import uuid
        
        # تسجيل بداية العملية
        logger = logging.getLogger(__name__)
        logger.info(f"إنشاء قيد محاسبي لمذكرة الدين {debit_note.note_number}")
        
        # إنشاء حركة حساب للمورد (مثل ما يحدث في فواتير المشتريات)
        transaction_number = f"DN-{uuid.uuid4().hex[:8].upper()}"
        
        # إنشاء AccountTransaction لمذكرة الدين
        account_transaction = AccountTransaction.objects.create(
            transaction_number=transaction_number,
            date=debit_note.date,
            customer_supplier=debit_note.supplier,
            transaction_type='debit_note',  # نوع مذكرة دين
            direction='debit',  # مدين (زيادة دين المورد)
            amount=debit_note.total_amount,
            reference_type='debit_note',
            reference_id=debit_note.id,
            description=f'مذكرة دين رقم {debit_note.note_number}',
            notes=debit_note.notes or '',
            created_by=user
        )
        
        logger.info(f"تم إنشاء AccountTransaction رقم {account_transaction.id} للمورد {debit_note.supplier.name}")
        
        # البحث عن حساب المورد للقيد المحاسبي
        # البحث باستخدام اسم المورد أو كود خاص
        supplier_account_name = f"حساب المورد - {debit_note.supplier.name}"
        supplier_account = Account.objects.filter(
            name__icontains=debit_note.supplier.name,
            account_type='liability'
        ).first()
        
        if not supplier_account:
            # البحث عن حساب الموردين العام
            suppliers_parent_account = Account.objects.filter(
                models.Q(code='2100') | models.Q(name__icontains='موردين')
            ).first()
            
            if not suppliers_parent_account:
                # إنشاء حساب الموردين الرئيسي إذا لم يكن موجوداً
                suppliers_parent_account = Account.objects.create(
                    code='2100',
                    name='حسابات الموردين',
                    account_type='liability',
                    description='حسابات الموردين الرئيسية'
                )
            
            # إنشاء حساب للمورد إذا لم يكن موجوداً
            supplier_account = Account.objects.create(
                code=f"2100-{debit_note.supplier.id:04d}",
                name=supplier_account_name,
                account_type='liability',
                parent=suppliers_parent_account,
                description=f'حساب المورد {debit_note.supplier.name}'
            )
        
        # إنشاء القيد المحاسبي
        journal_service = JournalService()
        
        # تحضير بيانات البنود للقيد المحاسبي
        lines_data = []
        
        # بند المورد (مدين)
        lines_data.append({
            'account_id': supplier_account.id,
            'debit': float(debit_note.total_amount),
            'credit': 0,
            'description': f'مذكرة دين رقم {debit_note.note_number}'
        })
        
        # حساب المصروفات أو الحساب المقابل (دائن)
        expenses_account = Account.objects.filter(code='4100').first()  # حساب المصروفات العامة
        if not expenses_account:
            # إنشاء حساب المصروفات إذا لم يكن موجوداً
            expenses_account = Account.objects.create(
                code='4100',
                name='مصروفات عامة',
                account_type='expense',
                description='المصروفات العامة والإدارية'
            )
        
        lines_data.append({
            'account_id': expenses_account.id,
            'debit': 0,
            'credit': float(debit_note.total_amount),
            'description': f'مذكرة دين رقم {debit_note.note_number}'
        })
        
        # إنشاء القيد المحاسبي بالتوقيع الصحيح
        journal_service.create_journal_entry(
            entry_date=debit_note.date,
            reference_type='debit_note',
            description=f'مذكرة دين رقم {debit_note.note_number} - {debit_note.supplier.name}',
            lines_data=lines_data,
            reference_id=debit_note.id,
            user=user
        )
        
        return True
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error creating debit note journal entry: {str(e)}")
        logger.error(f"خطأ تفصيلي: {e.__class__.__name__}: {str(e)}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        raise e  # إعادة رفع الخطأ لرؤيته في رسائل النظام


def create_purchase_invoice_journal_entry_old(invoice, user):
    """إنشاء قيد محاسبي لفاتورة المشتريات - الطريقة القديمة"""

def create_purchase_return_journal_entry(purchase_return, user):
    """إنشاء قيد محاسبي لمردود المشتريات"""
    try:
        # إنشاء القيد المحاسبي باستخدام JournalService
        JournalService.create_purchase_return_entry(purchase_return, user)
    except Exception as e:
        print(f"خطأ في إنشاء القيد المحاسبي لمردود المشتريات: {e}")
        # لا نوقف العملية في حالة فشل إنشاء القيد المحاسبي
        pass


def create_purchase_invoice_account_transaction(invoice, user):
    """إنشاء حركة حساب للمورد عند إنشاء فاتورة مشتريات"""
    try:
        from accounts.models import AccountTransaction
        import uuid
        
        # إنشاء معاملة لجميع فواتير المشتريات (نقدية وائتمانية)
        if invoice.supplier:
            # توليد رقم الحركة
            transaction_number = f"PURCH-{uuid.uuid4().hex[:8].upper()}"
            
            # حساب الرصيد السابق
            last_transaction = AccountTransaction.objects.filter(
                customer_supplier=invoice.supplier
            ).order_by('-created_at').first()
            
            previous_balance = last_transaction.balance_after if last_transaction else Decimal('0')
            
            # تحديد الاتجاه والوصف حسب طريقة الدفع
            if invoice.payment_type == 'cash':
                # للدفع النقدي - لا تؤثر على رصيد المورد
                direction = 'debit'
                new_balance = previous_balance
                description = f'مشتريات نقدية - فاتورة رقم {invoice.invoice_number}'
            else:
                # للدفع الائتماني - زيادة الذمم الدائنة
                direction = 'credit'
                new_balance = previous_balance + invoice.total_amount
                description = f'مشتريات ائتمانية - فاتورة رقم {invoice.invoice_number}'
            
            AccountTransaction.objects.create(
                transaction_number=transaction_number,
                date=invoice.date,
                customer_supplier=invoice.supplier,
                transaction_type='purchase_invoice',
                direction=direction,
                amount=invoice.total_amount,
                reference_type='purchase_invoice',
                reference_id=invoice.id,
                description=description,
                balance_after=new_balance,
                created_by=user
            )
            
    except ImportError:
        # في حالة عدم وجود نموذج الحسابات
        pass
    except Exception as e:
        print(f"خطأ في إنشاء حركة الحساب: {e}")
        # لا نوقف العملية في حالة فشل تسجيل الحركة المالية
        pass


def create_purchase_return_account_transaction(return_invoice, user):
    """إنشاء حركة حساب للمورد عند إنشاء مردود مشتريات"""
    try:
        from accounts.models import AccountTransaction
        from customers.models import CustomerSupplier
        from decimal import Decimal
        import uuid
        
        supplier = return_invoice.original_invoice.supplier
        
        if supplier:
            # إنشاء معاملة حساب للمورد الأصلي
            transaction_number = f"PRET-{uuid.uuid4().hex[:8].upper()}"
            
            # حساب الرصيد السابق للمورد
            last_transaction = AccountTransaction.objects.filter(
                customer_supplier=supplier
            ).order_by('-created_at').first()
            
            previous_balance = last_transaction.balance_after if last_transaction else Decimal('0')
            new_balance = previous_balance - return_invoice.total_amount
            
            # إنشاء معاملة للمورد
            AccountTransaction.objects.create(
                transaction_number=transaction_number,
                date=return_invoice.date,
                customer_supplier=supplier,
                transaction_type='purchase_return',
                direction='credit',  # دائن للمورد (تقليل دين المورد)
                amount=return_invoice.total_amount,
                reference_type='purchase_return',
                reference_id=return_invoice.id,
                description=f'مردود مشتريات - فاتورة رقم {return_invoice.return_number}',
                balance_after=new_balance,
                created_by=user
            )
            
            # إذا كان المورد من نوع "supplier" فقط، ابحث عن عميل بنفس الاسم
            if supplier.type == 'supplier':
                matching_customers = CustomerSupplier.objects.filter(
                    name=supplier.name,
                    type__in=['customer', 'both']
                ).exclude(id=supplier.id)
                
                # إنشاء معاملة للعميل المطابق أيضاً
                for customer in matching_customers:
                    customer_transaction_number = f"PRET-C-{uuid.uuid4().hex[:8].upper()}"
                    
                    # حساب الرصيد السابق للعميل
                    last_customer_transaction = AccountTransaction.objects.filter(
                        customer_supplier=customer
                    ).order_by('-created_at').first()
                    
                    customer_previous_balance = last_customer_transaction.balance_after if last_customer_transaction else Decimal('0')
                    customer_new_balance = customer_previous_balance - return_invoice.total_amount  # مدين للعميل
                    
                    AccountTransaction.objects.create(
                        transaction_number=customer_transaction_number,
                        date=return_invoice.date,
                        customer_supplier=customer,
                        transaction_type='purchase_return',
                        direction='debit',  # مدين للعميل (زيادة دين العميل)
                        amount=return_invoice.total_amount,
                        reference_type='purchase_return',
                        reference_id=return_invoice.id,
                        description=f'مردود مشتريات - فاتورة رقم {return_invoice.return_number} (عميل مرتبط)',
                        balance_after=customer_new_balance,
                        created_by=user
                    )
            
    except ImportError:
        # في حالة عدم وجود نموذج الحسابات
        pass
    except Exception as e:
        print(f"خطأ في إنشاء حركة الحساب: {e}")
        # لا نوقف العملية في حالة فشل تسجيل الحركة المالية
        pass

class PurchaseInvoiceListView(LoginRequiredMixin, ListView):
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.has_perm('purchases.can_view_purchases') or request.user.has_perm('purchases.view_purchaseinvoice') or request.user.is_superuser):
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, 'ليس لديك صلاحية لعرض فواتير المشتريات')
            return redirect('/')
        return super().dispatch(request, *args, **kwargs)
    model = PurchaseInvoice
    template_name = 'purchases/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = PurchaseInvoice.objects.select_related('supplier', 'warehouse')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(supplier_invoice_number__icontains=search) |
                Q(invoice_number__icontains=search) |
                Q(supplier__name__icontains=search)
            )
        
        # Apply filters if provided
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        payment_type = self.request.GET.get('payment_type')
        supplier_id = self.request.GET.get('supplier')
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if payment_type:
            queryset = queryset.filter(payment_type=payment_type)
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        
        # Apply ordering
        order_by = self.request.GET.get('order_by', '-date')
        if order_by.startswith('-'):
            queryset = queryset.order_by(order_by, '-id')
        else:
            queryset = queryset.order_by(order_by, 'id')
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate page total for visible invoices
        page_total = sum(invoice.total_amount for invoice in context['invoices'])
        context['page_total'] = page_total
        
        # Calculate statistics
        all_invoices = PurchaseInvoice.objects.all()
        context['total_invoices'] = all_invoices.count()
        
        # Total amount
        total_amount = all_invoices.aggregate(total=Sum('total_amount'))['total'] or 0
        context['total_amount'] = total_amount
        
        # This month's invoices
        current_month = timezone.now().replace(day=1)
        month_invoices = all_invoices.filter(date__gte=current_month).count()
        context['month_invoices'] = month_invoices
        
        # Active suppliers (suppliers with invoices)
        active_suppliers = CustomerSupplier.objects.filter(
            Q(type='supplier') | Q(type='both'),
            purchaseinvoice__isnull=False
        ).distinct().count()
        context['active_suppliers'] = active_suppliers
        
        # All suppliers for filter dropdown
        context['suppliers'] = CustomerSupplier.objects.filter(
            Q(type='supplier') | Q(type='both')
        ).order_by('name')
        
        # Current ordering
        context['current_order'] = self.request.GET.get('order_by', '-date')
        
        return context

class PurchaseInvoiceCreateView(LoginRequiredMixin, View):
    template_name = 'purchases/invoice_add.html'
    
    def get_invoice_create_context(self, request, form_data=None):
        """إعداد سياق صفحة إنشاء الفاتورة مع البيانات المُدخلة إن وجدت"""
        products = Product.objects.filter(is_active=True).order_by('name')
        
        # إضافة آخر سعر شراء لكل منتج
        products_with_prices = []
        for product in products:
            product.last_purchase_price = product.get_last_purchase_price()
            products_with_prices.append(product)
        
        # إعداد بيانات المنتجات للـ JavaScript
        products_data = []
        for product in products:
            products_data.append({
                'id': product.id,
                'code': product.code,
                'name': product.name,
                'price': float(product.get_last_purchase_price() or 0),
                'tax_rate': float(product.tax_rate or 0),
                'current_stock': float(product.current_stock or 0),
                'description': product.description or ''
            })
        
        print(f"Products count: {len(products)}, products_data count: {len(products_data)}")
        
        # إضافة رقم الفاتورة التالي من DocumentSequence
        try:
            sequence = DocumentSequence.objects.get(document_type='purchase_invoice')
            next_invoice_number = sequence.get_formatted_number()
        except DocumentSequence.DoesNotExist:
            # عرض رسالة خطأ إذا لم يكن التسلسل معداً مسبقاً
            from django.contrib import messages
            messages.error(request, _('Purchase invoice sequence is not configured. Please set up the sequence first from the document sequences settings page.'))
            next_invoice_number = ''
        
        context = {
            'suppliers': CustomerSupplier.objects.filter(
                Q(type='supplier') | Q(type='both')
            ).order_by('name'),
            'warehouses': Warehouse.objects.filter(
                is_active=True
            ).exclude(code='MAIN').order_by('name'),
            'cashboxes': Cashbox.objects.filter(
                is_active=True
            ).order_by('name'),
            'bank_accounts': BankAccount.objects.filter(
                is_active=True
            ).order_by('name'),
            'default_warehouse': request.user.default_purchase_warehouse,
            'products': products_with_prices,
            'products_json': json.dumps(products_data),
            'categories': Category.objects.filter(is_active=True).order_by('name'),
            'next_invoice_number': next_invoice_number,
            'can_toggle_invoice_tax': request.user.is_superuser or request.user.has_perm('purchases.can_toggle_purchase_tax'),
            'today': timezone.now().date()
        }
        
        # إضافة البيانات المُدخلة إذا كانت موجودة
        if form_data:
            context.update(form_data)
        
        return context
    
    def get(self, request, *args, **kwargs):
        context = self.get_invoice_create_context(request)
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        try:
            # الحصول على رقم الفاتورة التالي من DocumentSequence
            try:
                sequence = DocumentSequence.objects.get(document_type='purchase_invoice')
                invoice_number = sequence.get_next_number()
            except DocumentSequence.DoesNotExist:
                # عرض رسالة خطأ إذا لم يكن التسلسل معداً مسبقاً
                messages.error(request, _('Purchase invoice sequence is not configured. Please set up the sequence first from the document sequences settings page.'))
                return redirect('purchases:invoice_add')
            
            # استلام البيانات الأساسية للفاتورة
            supplier_invoice_number = request.POST.get('supplier_invoice_number', '').strip()
            date = request.POST.get('date', '').strip()  # تنظيف التاريخ
            supplier_id = request.POST.get('supplier')
            warehouse_id = request.POST.get('warehouse')
            payment_type = request.POST.get('payment_type')
            payment_method = request.POST.get('payment_method', '').strip()
            cashbox_id = request.POST.get('cashbox')
            bank_account_id = request.POST.get('bank_account')
            check_number = request.POST.get('check_number', '').strip()
            check_date_raw = request.POST.get('check_date', '').strip()
            check_date = check_date_raw if check_date_raw else None  # تحويل السلسلة الفارغة إلى None
            # التحقق من صلاحية تغيير خيار شمول الضريبة
            if request.user.is_superuser or request.user.has_perm('purchases.can_toggle_purchase_tax'):
                is_tax_inclusive = request.POST.get('is_tax_inclusive') == 'on'  # checkbox value
            else:
                is_tax_inclusive = False  # المستخدمون العاديون لا يمكنهم تغيير هذا الخيار
            notes = request.POST.get('notes', '').strip()
            
            # جمع البيانات المُدخلة لإعادة عرضها في حالة الأخطاء
            form_data = {
                'supplier_invoice_number': supplier_invoice_number,
                'date': date,
                'supplier_id': supplier_id,
                'warehouse_id': warehouse_id,
                'payment_type': payment_type,
                'payment_method': payment_method,
                'cashbox_id': cashbox_id,
                'bank_account_id': bank_account_id,
                'check_number': check_number,
                'check_date': check_date,
                'is_tax_inclusive': is_tax_inclusive,
                'notes': notes,
            }
            
            # التحقق من صحة البيانات
            if not all([supplier_invoice_number, date, supplier_id, warehouse_id, payment_type]):
                # سجل محاولة فاشلة في سجل النشاط لتتبع أخطاء الإدخال
                try:
                    from core.signals import log_user_activity
                    dummy = PurchaseInvoice()
                    log_user_activity(
                        request,
                        'error',
                        dummy,
                        _('فشل إنشاء فاتورة شراء: الحقول المطلوبة مفقودة (رقم فاتورة المورد أو التاريخ أو المورد أو المستودع أو طريقة الدفع)')
                    )
                except Exception:
                    pass
                messages.error(request, 'جميع الحقول الأساسية مطلوبة!')
                context = self.get_invoice_create_context(request, form_data)
                return render(request, self.template_name, context)
            
            # التحقق من صحة تنسيق التاريخ
            if not date or (isinstance(date, str) and date.strip() == '') or date is None:
                messages.error(request, 'تاريخ الفاتورة مطلوب!')
                context = self.get_invoice_create_context(request, form_data)
                return render(request, self.template_name, context)
            
            # محاولة تحويل التاريخ للتأكد من صحته
            try:
                from datetime import datetime
                datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                messages.error(request, 'تنسيق التاريخ غير صحيح! يجب أن يكون بالصيغة YYYY-MM-DD')
                context = self.get_invoice_create_context(request, form_data)
                return render(request, self.template_name, context)
            
            # الحصول على المورد
            try:
                supplier = CustomerSupplier.objects.get(id=supplier_id)
            except CustomerSupplier.DoesNotExist:
                messages.error(request, 'المورد المحدد غير موجود!')
                context = self.get_invoice_create_context(request, form_data)
                return render(request, self.template_name, context)
            
            # الحصول على المستودع (اختياري)
            warehouse = None
            if warehouse_id:
                try:
                    warehouse = Warehouse.objects.get(id=warehouse_id, is_active=True)
                except Warehouse.DoesNotExist:
                    messages.error(request, 'المستودع المحدد غير موجود!')
                    context = self.get_invoice_create_context(request, form_data)
                    return render(request, self.template_name, context)
            
            # التحقق من صحة طريقة الدفع وحقولها المرتبطة
            cashbox = None
            bank_account = None
            
            if payment_method:
                if payment_method == 'cash':
                    if not cashbox_id:
                        messages.error(request, 'يجب تحديد الصندوق عند اختيار الدفع النقدي!')
                        context = self.get_invoice_create_context(request, form_data)
                        return render(request, self.template_name, context)
                    try:
                        cashbox = Cashbox.objects.get(id=cashbox_id, is_active=True)
                    except Cashbox.DoesNotExist:
                        messages.error(request, 'الصندوق المحدد غير موجود!')
                        context = self.get_invoice_create_context(request, form_data)
                        return render(request, self.template_name, context)
                elif payment_method in ['check', 'transfer']:
                    if not bank_account_id:
                        messages.error(request, f'يجب تحديد الحساب البنكي عند اختيار {dict(PurchaseInvoice.PAYMENT_METHODS)[payment_method]}!')
                        context = self.get_invoice_create_context(request, form_data)
                        return render(request, self.template_name, context)
                    try:
                        bank_account = BankAccount.objects.get(id=bank_account_id, is_active=True)
                    except BankAccount.DoesNotExist:
                        messages.error(request, 'الحساب البنكي المحدد غير موجود!')
                        context = self.get_invoice_create_context(request, form_data)
                        return render(request, self.template_name, context)
                    
                    if payment_method == 'check':
                        if not check_number:
                            messages.error(request, 'يجب إدخال رقم الشيك!')
                            context = self.get_invoice_create_context(request, form_data)
                            return render(request, self.template_name, context)
                        if not check_date:
                            messages.error(request, 'يجب إدخال تاريخ الشيك!')
                            context = self.get_invoice_create_context(request, form_data)
                            return render(request, self.template_name, context)
            
            # الحصول على المستخدم الحالي
            created_by = request.user
            
            # معالجة المنتجات أولاً للتحقق من صحة البيانات قبل إنشاء أي شيء
            products_data = []
            product_ids = request.POST.getlist('product_id[]')
            quantities = request.POST.getlist('quantity[]')
            unit_prices = request.POST.getlist('unit_price[]')
            row_taxes = request.POST.getlist('row_tax[]')
            
            # التحقق من وجود منتجات قبل إنشاء الفاتورة
            if not product_ids or not quantities or not unit_prices or not any(p for p in product_ids if p):
                try:
                    from core.signals import log_user_activity
                    dummy = PurchaseInvoice()
                    log_user_activity(
                        request,
                        'error',
                        dummy,
                        _('فشل إنشاء فاتورة شراء: لا توجد منتجات مضافة')
                    )
                except Exception:
                    pass
                messages.error(request, 'يجب إضافة منتج واحد على الأقل!')
                context = self.get_invoice_create_context(request, form_data)
                return render(request, self.template_name, context)
            
            # حساب المجاميع مسبقاً للتحقق من صحة البيانات
            if product_ids and quantities and unit_prices:
                from decimal import Decimal
                subtotal = Decimal('0')
                total_tax = Decimal('0')
                
                # حساب المجاميع مؤقتاً للتحقق من صحة البيانات
                for i, product_id in enumerate(product_ids):
                    if product_id and i < len(quantities) and i < len(unit_prices):
                        try:
                            product = Product.objects.get(id=product_id)
                            quantity = Decimal(str(quantities[i]))
                            unit_price = Decimal(str(unit_prices[i]))
                            
                            # حساب المجموع الفرعي للمنتج
                            row_subtotal = quantity * unit_price
                            
                            # الحصول على نسبة الضريبة وقيمة الضريبة
                            tax_rate = product.tax_rate or Decimal('0')
                            tax_amount = Decimal(str(row_taxes[i])) if i < len(row_taxes) and row_taxes[i] else Decimal('0')
                            
                            subtotal += row_subtotal
                            total_tax += tax_amount
                            
                        except (Product.DoesNotExist, ValueError):
                            continue
                
                # حساب الإجمالي النهائي
                if is_tax_inclusive:
                    final_total = (subtotal + total_tax).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                else:
                    final_total = subtotal.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                
                # التحقق من الحد الائتماني للمورد (إذا كان الدفع آجل)
                if payment_type == 'credit' and supplier and supplier.credit_limit > 0:
                    current_balance = supplier.current_balance
                    # الحد الائتماني المتاح = الحد الائتماني - الرصيد الدائن
                    available_credit = supplier.credit_limit - abs(current_balance) if current_balance > 0 else supplier.credit_limit
                    
                    if final_total > available_credit:
                        error_message = _(
                            'لا يمكن إنشاء الفاتورة لأن المبلغ الإجمالي (%(total)s) يتجاوز الحد الائتماني المتاح للمورد (%(available)s).\n\nاقتراحات:\n1. زيادة الحد الائتماني للمورد\n2. تسديد المستحقات المتأخرة للمورد\n3. تحويل الفاتورة إلى دفع نقدي'
                        ) % {
                            'total': f"{final_total:.3f}",
                            'available': f"{available_credit:.3f}"
                        }
                        
                        existing_messages = [msg for msg in messages.get_messages(request) if msg.message == error_message]
                        if not existing_messages:
                            messages.warning(request, error_message)
                        
                        try:
                            from core.signals import log_user_activity
                            log_user_activity(
                                request,
                                'error',
                                supplier,
                                _('فشل في إنشاء فاتورة شراء: تجاوز الحد الائتماني - المبلغ %(total)s > المتاح %(available)s') % {
                                    'total': f"{final_total:.3f}",
                                    'available': f"{available_credit:.3f}"
                                }
                            )
                        except Exception:
                            pass
                        
                        context = self.get_invoice_create_context(request, form_data)
                        return render(request, self.template_name, context)
                
                # إذا وصلنا هنا، يمكننا إنشاء الفاتورة بأمان
                # إنشاء الفاتورة
                invoice = PurchaseInvoice.objects.create(
                    invoice_number=invoice_number,
                    supplier_invoice_number=supplier_invoice_number,
                    date=date,
                    supplier=supplier,
                    warehouse=warehouse,
                    payment_type=payment_type,
                    payment_method=payment_method,
                    cashbox=cashbox,
                    bank_account=bank_account,
                    check_number=check_number,
                    check_date=check_date,
                    is_tax_inclusive=is_tax_inclusive,
                    notes=notes,
                    created_by=created_by,
                    subtotal=subtotal.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP),
                    tax_amount=total_tax.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP) if is_tax_inclusive else Decimal('0'),
                    total_amount=final_total
                )
                
                # إعادة تعيين المجاميع للحساب الفعلي
                subtotal = Decimal('0')
                total_tax = Decimal('0')
                
                # إنشاء عناصر الفاتورة وحركات المخزون
                for i, product_id in enumerate(product_ids):
                    if product_id and i < len(quantities) and i < len(unit_prices):
                        try:
                            product = Product.objects.get(id=product_id)
                            quantity = Decimal(str(quantities[i]))
                            unit_price = Decimal(str(unit_prices[i]))
                            
                            # حساب المجموع الفرعي للمنتج
                            row_subtotal = quantity * unit_price
                            
                            # الحصول على نسبة الضريبة وقيمة الضريبة
                            tax_rate = product.tax_rate or Decimal('0')
                            tax_amount = Decimal(str(row_taxes[i])) if i < len(row_taxes) and row_taxes[i] else Decimal('0')
                            
                            # المجموع الإجمالي للمنتج (المجموع الفرعي + الضريبة)
                            total_amount = row_subtotal + tax_amount
                            
                            # إنشاء عنصر الفاتورة
                            item = PurchaseInvoiceItem.objects.create(
                                invoice=invoice,
                                product=product,
                                quantity=quantity,
                                unit_price=unit_price,
                                tax_rate=tax_rate,
                                tax_amount=tax_amount,
                                total_amount=total_amount
                            )
                            
                            subtotal += row_subtotal
                            total_tax += tax_amount
                            
                        except (Product.DoesNotExist, ValueError):
                            continue
                
                # إنشاء حركة حساب للمورد - تم نقله إلى الإشارات
                # create_purchase_invoice_account_transaction(invoice, request.user)
                
                # إنشاء القيد المحاسبي - تم نقله إلى الإشارات
                # create_purchase_invoice_journal_entry(invoice, request.user)
            
            # حفظ المستودع الافتراضي إذا تم تحديده
            set_default_warehouse = request.POST.get('set_default_warehouse')
            if set_default_warehouse and warehouse:
                old_default = request.user.default_purchase_warehouse
                request.user.default_purchase_warehouse = warehouse
                request.user.save()
                
                # تسجيل التغيير في سجل الأنشطة
                try:
                    log_activity(
                        request.user,
                        'UPDATE',
                        request.user,
                        f'تم تحديث المستودع الافتراضي للمشتريات من {old_default.name if old_default else "غير محدد"} إلى {warehouse.name}',
                        request
                    )
                except Exception:
                    pass
            
            # تسجيل النشاط
            try:
                description = f'تم إنشاء فاتورة مشتريات رقم {invoice_number} للمورد {invoice.supplier.name}'
                log_activity(request.user, 'CREATE', invoice, description, request)
            except Exception as log_error:
                print(f"Warning: Failed to log activity: {log_error}")
            
            messages.success(request, f'تم إنشاء فاتورة المشتريات رقم {invoice_number} بنجاح!')
            return redirect('purchases:invoice_detail', pk=invoice.pk)
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء إنشاء الفاتورة: {str(e)}')
            return self.get(request)


class PurchaseDebitNoteListView(LoginRequiredMixin, ListView):
    def dispatch(self, request, *args, **kwargs):
        if not (
            request.user.has_perm('purchases.can_view_debitnote') or
            request.user.has_perm('purchases.view_purchasedebitnote') or
            request.user.is_superuser
        ):
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, _('ليس لديك صلاحية لعرض اشعارات المدين'))
            return redirect('/')
        return super().dispatch(request, *args, **kwargs)
    model = PurchaseDebitNote
    template_name = 'purchases/debitnote_list.html'
    context_object_name = 'debitnotes'

    def get_queryset(self):
        queryset = PurchaseDebitNote.objects.all()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(Q(note_number__icontains=search) | Q(supplier__name__icontains=search))
        return queryset.select_related('supplier', 'created_by')


@login_required
def purchase_debitnote_create(request):
    from django.contrib import messages
    from django.shortcuts import redirect
    
    if not (
        request.user.has_perm('purchases.can_view_debitnote') or
        request.user.has_perm('purchases.add_purchasedebitnote') or
        request.user.is_superuser
    ):
        messages.error(request, _('ليس لديك صلاحية لإنشاء مذكرة دين'))
        return redirect('/')
    if request.method == 'POST':
        try:
            with transaction.atomic():
                supplier_id = request.POST.get('supplier')
                if not supplier_id:
                    messages.error(request, _('يرجى اختيار مورد'))
                    return redirect('purchases:debitnote_add')

                supplier = get_object_or_404(CustomerSupplier, id=supplier_id)

                supplier_debit_note_number = request.POST.get('supplier_debit_note_number', '').strip()
                if not supplier_debit_note_number:
                    messages.error(request, _('يرجى إدخال رقم إشعار المدين (مصدر)'))
                    return redirect('purchases:debitnote_add')

                # توليد الرقم
                try:
                    seq = DocumentSequence.objects.get(document_type='debit_note')
                    note_number = seq.get_next_number()
                except DocumentSequence.DoesNotExist:
                    messages.error(request, _('يجب إعداد تسلسل "إشعار مدين" أولاً قبل إنشاء إشعارات مدين جديدة'))
                    return redirect('purchases:debitnote_add')

                debit = PurchaseDebitNote.objects.create(
                    note_number=note_number,
                    date=request.POST.get('date', date.today()),
                    supplier=supplier,
                    supplier_debit_note_number=supplier_debit_note_number,
                    subtotal=Decimal(request.POST.get('subtotal', '0') or '0'),
                    notes=request.POST.get('notes', ''),
                    created_by=request.user
                )

                # إنشاء القيد المحاسبي
                try:
                    create_debit_note_journal_entry(debit, request.user)
                    messages.success(request, f'تم إنشاء القيد المحاسبي لمذكرة الدين رقم {debit.note_number}')
                except Exception as e:
                    error_msg = f"Error creating journal entry for debit note: {str(e)}"
                    logging.getLogger(__name__).error(error_msg)
                    messages.warning(request, f'تم إنشاء مذكرة الدين ولكن حدث خطأ في القيد المحاسبي: {str(e)}')

                try:
                    from core.signals import log_user_activity
                    log_user_activity(request, 'create', debit, _('إنشاء اشعار مدين رقم %(number)s') % {'number': debit.note_number})
                except Exception:
                    pass

                messages.success(request, _('تم إنشاء اشعار مدين رقم %(number)s') % {'number': debit.note_number})
                return redirect('purchases:debitnote_detail', pk=debit.pk)
        except Exception as e:
            messages.error(request, _('حدث خطأ أثناء حفظ الإشعار: %(error)s') % {'error': str(e)})
            return redirect('purchases:debitnote_add')

    context = {
        'suppliers': CustomerSupplier.objects.filter(Q(type='supplier')|Q(type='both')),
        'today_date': date.today().isoformat(),
    }
    try:
        seq = DocumentSequence.objects.get(document_type='debit_note')
        context['next_note_number'] = seq.peek_next_number() if hasattr(seq, 'peek_next_number') else seq.get_formatted_number()
    except DocumentSequence.DoesNotExist:
        context['sequence_error'] = _('يجب إعداد تسلسل "إشعار مدين" أولاً قبل إنشاء إشعارات مدين جديدة')

    return render(request, 'purchases/debitnote_add.html', context)


class PurchaseDebitNoteDetailView(LoginRequiredMixin, DetailView):
    model = PurchaseDebitNote
    template_name = 'purchases/debitnote_detail.html'
    context_object_name = 'debitnote'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                context['base_currency'] = company_settings.base_currency
        except Exception:
            pass
        
        # إضافة القيود المحاسبية المرتبطة
        from journal.models import JournalEntry
        context['journal_entries'] = JournalEntry.objects.filter(
            reference_type='debit_note',
            reference_id=self.object.id
        ).select_related('created_by')
        
        return context

class PurchaseInvoiceDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'purchases/invoice_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        invoice_id = kwargs.get('pk')
        try:
            invoice = PurchaseInvoice.objects.select_related('supplier', 'created_by').get(id=invoice_id)
            invoice_items = invoice.items.select_related('product').all()
            
            # إضافة المجموع بدون الضريبة لكل عنصر
            for item in invoice_items:
                item.subtotal = item.quantity * item.unit_price
            
            # إذا كانت مجاميع الفاتورة تساوي صفر، احسبها من العناصر
            if invoice.subtotal == 0 and invoice.tax_amount == 0 and invoice.total_amount == 0 and invoice_items.exists():
                from decimal import Decimal, ROUND_HALF_UP
                
                subtotal = Decimal('0')
                tax_amount = Decimal('0') 
                total_amount = Decimal('0')
                
                for item in invoice_items:
                    item_subtotal = item.quantity * item.unit_price
                    subtotal += item_subtotal
                    tax_amount += item.tax_amount
                    total_amount += item.total_amount
                
                # تحديث مجاميع الفاتورة في قاعدة البيانات
                invoice.subtotal = subtotal.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                invoice.tax_amount = tax_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                invoice.total_amount = total_amount.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                invoice.save()
            
            context.update({
                'invoice': invoice,
                'invoice_items': invoice_items,
                'items_count': invoice_items.count(),
                'journal_entries': JournalEntry.objects.filter(purchase_invoice=invoice).select_related('created_by'),
            })
            
        except PurchaseInvoice.DoesNotExist:
            context['error'] = 'الفاتورة غير موجودة'
        
        return context

class PurchaseInvoiceUpdateView(LoginRequiredMixin, View):
    template_name = 'purchases/invoice_edit.html'
    
    def get(self, request, pk):
        """عرض نموذج تعديل الفاتورة مع البيانات الحالية"""
        try:
            invoice = get_object_or_404(PurchaseInvoice, pk=pk)
            
            # الحصول على المنتجات والموردين والمستودعات
            products = Product.objects.filter(is_active=True).order_by('name')
            products_with_prices = []
            for product in products:
                product.last_purchase_price = product.get_last_purchase_price()
                products_with_prices.append(product)
            
            context = {
                'invoice': invoice,
                'suppliers': CustomerSupplier.objects.filter(
                    Q(type='supplier') | Q(type='both')
                ).order_by('name'),
                'warehouses': Warehouse.objects.filter(
                    is_active=True
                ).exclude(code='MAIN').order_by('name'),
                'cashboxes': Cashbox.objects.filter(
                    is_active=True
                ).order_by('name'),
                'bank_accounts': BankAccount.objects.filter(
                    is_active=True
                ).order_by('name'),
                'default_warehouse': Warehouse.get_default_warehouse(),
                'products': products_with_prices,
                'invoice_items': invoice.items.select_related('product').all()
            }
            return render(request, self.template_name, context)
            
        except Exception as e:
            messages.error(request, f'خطأ في تحميل الفاتورة: {str(e)}')
            return redirect('purchases:invoice_list')
    
    def post(self, request, pk):
        """حفظ تعديلات الفاتورة"""
        try:
            invoice = get_object_or_404(PurchaseInvoice, pk=pk)
            
            # استلام البيانات الأساسية للفاتورة
            supplier_invoice_number = request.POST.get('supplier_invoice_number', '').strip()
            date = request.POST.get('date')
            supplier_id = request.POST.get('supplier')
            warehouse_id = request.POST.get('warehouse')
            payment_type = request.POST.get('payment_type')
            payment_method = request.POST.get('payment_method', '').strip()
            cashbox_id = request.POST.get('cashbox')
            bank_account_id = request.POST.get('bank_account')
            check_number = request.POST.get('check_number', '').strip()
            check_date_raw = request.POST.get('check_date', '').strip()
            check_date = check_date_raw if check_date_raw else None  # تحويل السلسلة الفارغة إلى None
            is_tax_inclusive = request.POST.get('is_tax_inclusive') == 'on'  # checkbox value
            notes = request.POST.get('notes', '').strip()
            
            # التحقق من صحة البيانات
            if not all([supplier_invoice_number, date, supplier_id, payment_type]):
                messages.error(request, 'جميع الحقول الأساسية مطلوبة!')
                return self.get(request, pk)
            
            # الحصول على المورد
            try:
                supplier = CustomerSupplier.objects.get(id=supplier_id)
            except CustomerSupplier.DoesNotExist:
                messages.error(request, 'المورد المحدد غير موجود!')
                return self.get(request, pk)
            
            # الحصول على المستودع (اختياري)
            warehouse = None
            if warehouse_id:
                try:
                    warehouse = Warehouse.objects.get(id=warehouse_id, is_active=True)
                except Warehouse.DoesNotExist:
                    messages.error(request, 'المستودع المحدد غير موجود!')
                    return self.get(request, pk)
            
            # التحقق من صحة طريقة الدفع وحقولها المرتبطة
            cashbox = None
            bank_account = None
            
            if payment_method:
                if payment_method == 'cash':
                    if not cashbox_id:
                        messages.error(request, 'يجب تحديد الصندوق عند اختيار الدفع النقدي!')
                        return self.get(request, pk)
                    try:
                        cashbox = Cashbox.objects.get(id=cashbox_id, is_active=True)
                    except Cashbox.DoesNotExist:
                        messages.error(request, 'الصندوق المحدد غير موجود!')
                        return self.get(request, pk)
                elif payment_method in ['check', 'transfer']:
                    if not bank_account_id:
                        messages.error(request, f'يجب تحديد الحساب البنكي عند اختيار {dict(PurchaseInvoice.PAYMENT_METHODS)[payment_method]}!')
                        return self.get(request, pk)
                    try:
                        bank_account = BankAccount.objects.get(id=bank_account_id, is_active=True)
                    except BankAccount.DoesNotExist:
                        messages.error(request, 'الحساب البنكي المحدد غير موجود!')
                        return self.get(request, pk)
                    
                    if payment_method == 'check':
                        if not check_number:
                            messages.error(request, 'يجب إدخال رقم الشيك!')
                            return self.get(request, pk)
                        if not check_date:
                            messages.error(request, 'يجب إدخال تاريخ الشيك!')
                            return self.get(request, pk)
            
            # تحديث بيانات الفاتورة الأساسية
            invoice.supplier_invoice_number = supplier_invoice_number
            invoice.date = date
            invoice.supplier = supplier
            invoice.warehouse = warehouse
            invoice.payment_type = payment_type
            invoice.payment_method = payment_method
            invoice.cashbox = cashbox
            invoice.bank_account = bank_account
            invoice.check_number = check_number
            invoice.check_date = check_date
            invoice.is_tax_inclusive = is_tax_inclusive
            invoice.notes = notes
            
            # حذف عناصر الفاتورة القديمة
            old_items = invoice.items.all()
            for item in old_items:
                # حذف حركات المخزون المرتبطة
                InventoryMovement.objects.filter(
                    reference_type='purchase_invoice',
                    reference_id=invoice.id,
                    product=item.product
                ).delete()
            
            # حذف العناصر القديمة
            invoice.items.all().delete()
            
            # معالجة المنتجات الجديدة
            product_ids = request.POST.getlist('product_id[]')
            quantities = request.POST.getlist('quantity[]')
            unit_prices = request.POST.getlist('unit_price[]')
            tax_rates = request.POST.getlist('tax_rate[]')
            row_taxes = request.POST.getlist('row_tax[]')
            
            if product_ids and quantities and unit_prices:
                subtotal = Decimal('0')
                total_tax = Decimal('0')
                
                for i, product_id in enumerate(product_ids):
                    if product_id and i < len(quantities) and i < len(unit_prices):
                        try:
                            product = Product.objects.get(id=product_id)
                            quantity = Decimal(str(quantities[i]))
                            unit_price = Decimal(str(unit_prices[i]))
                            
                            # حساب المجموع الفرعي للمنتج
                            row_subtotal = quantity * unit_price
                            
                            # الحصول على نسبة الضريبة وقيمة الضريبة
                            tax_rate = Decimal(str(tax_rates[i])) if i < len(tax_rates) and tax_rates[i] else Decimal('0')
                            tax_amount = Decimal(str(row_taxes[i])) if i < len(row_taxes) and row_taxes[i] else Decimal('0')
                            
                            # المجموع الإجمالي للمنتج
                            total_amount = row_subtotal + tax_amount
                            
                            # إنشاء عنصر الفاتورة الجديد
                            item = PurchaseInvoiceItem.objects.create(
                                invoice=invoice,
                                product=product,
                                quantity=quantity,
                                unit_price=unit_price,
                                tax_rate=tax_rate,
                                tax_amount=tax_amount,
                                total_amount=total_amount
                            )
                            
                            subtotal += row_subtotal
                            total_tax += tax_amount
                            
                        except (Product.DoesNotExist, ValueError, TypeError) as e:
                            continue
                
                # تحديث مجاميع الفاتورة
                invoice.subtotal = subtotal.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                invoice.tax_amount = total_tax.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                invoice.total_amount = (subtotal + total_tax).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
                invoice.save()
                
                # حذف المعاملات المحاسبية القديمة
                delete_transaction_by_reference('purchase_invoice', invoice.id)
                
                # حذف القيود المحاسبية القديمة
                try:
                    from journal.models import JournalEntry
                    JournalEntry.objects.filter(
                        reference_type='purchase_invoice',
                        reference_id=invoice.id
                    ).delete()
                except Exception as e:
                    print(f"تحذير: فشل في حذف القيود المحاسبية القديمة: {e}")
                
                # إنشاء المعاملات المحاسبية الجديدة - تم نقله إلى الإشارات
                # create_purchase_invoice_account_transaction(invoice, request.user)
                # create_purchase_invoice_journal_entry(invoice, request.user)
                
                # تسجيل النشاط
                try:
                    description = f'تم تحديث فاتورة مشتريات رقم {invoice.invoice_number} للمورد {invoice.supplier.name}'
                    log_activity(request.user, 'UPDATE', invoice, description, request)
                except Exception as log_error:
                    print(f"Warning: Failed to log activity: {log_error}")
                
                messages.success(request, f'تم تحديث فاتورة المشتريات رقم {invoice.invoice_number} بنجاح')
                return redirect('purchases:invoice_detail', pk=invoice.pk)
            else:
                messages.error(request, 'يجب إضافة منتج واحد على الأقل للفاتورة!')
                return self.get(request, pk)
                
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تحديث الفاتورة: {str(e)}')
            return self.get(request, pk)

class PurchaseInvoiceDeleteView(LoginRequiredMixin, DeleteView):
    model = PurchaseInvoice
    template_name = 'purchases/invoice_delete.html'
    success_url = reverse_lazy('purchases:invoice_list')
    context_object_name = 'invoice'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = self.get_object()
        
        # Get invoice items for display using related_name
        context['invoice_items'] = invoice.items.select_related('product')
        
        return context
    
    def delete(self, request, *args, **kwargs):
        invoice = self.get_object()
        invoice_number = invoice.invoice_number
        
        try:
            # حذف حركات المخزون المرتبطة بالفاتورة (فقط إذا كانت موجودة)
            try:
                from inventory.models import InventoryMovement
                inventory_movements = InventoryMovement.objects.filter(
                    reference_type='purchase_invoice',
                    reference_id=invoice.id
                )
                if inventory_movements.exists():
                    movement_count = inventory_movements.count()
                    inventory_movements.delete()
                    print(f"تم حذف {movement_count} حركة مخزون لفاتورة المشتريات {invoice_number}")
                else:
                    print(f"لا توجد حركات مخزون لفاتورة المشتريات {invoice_number} (فاتورة قديمة)")
            except ImportError:
                pass
            except Exception as e:
                print(f"خطأ في حذف حركات المخزون: {e}")
            
            # حذف حركة حساب المورد المرتبطة بالفاتورة
            delete_transaction_by_reference('purchase_invoice', invoice.id)
            
            # تسجيل النشاط قبل الحذف
            from core.signals import log_activity
            log_activity(
                user=request.user,
                action_type='DELETE',
                obj=invoice,
                description=f'تم حذف فاتورة مشتريات رقم: {invoice_number}',
                request=request
            )
            
            # The items will be deleted automatically due to CASCADE relationship
            # Delete the invoice
            result = super().delete(request, *args, **kwargs)
            
            messages.success(
                request, 
                f'تم حذف فاتورة المشتريات رقم {invoice_number} بنجاح'
            )
            
            return result
            
        except Exception as e:
            messages.error(
                request, 
                f'حدث خطأ أثناء حذف الفاتورة: {str(e)}'
            )
            return redirect('purchases:invoice_list')


# =================== Purchase Returns Views ===================

class PurchaseReturnListView(LoginRequiredMixin, ListView):
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.has_perm('purchases.can_view_purchasereturn') or request.user.has_perm('purchases.view_purchasereturn') or request.user.is_superuser):
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, 'ليس لديك صلاحية لعرض مردودات المشتريات')
            return redirect('/')
        return super().dispatch(request, *args, **kwargs)
    model = PurchaseReturn
    template_name = 'purchases/return_list.html'
    context_object_name = 'returns'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = PurchaseReturn.objects.select_related('original_invoice__supplier', 'created_by')
        
        # Apply filters if provided
        search = self.request.GET.get('search')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        return_type = self.request.GET.get('return_type')
        supplier_id = self.request.GET.get('supplier')
        order_by = self.request.GET.get('order_by', '-date')
        
        if search:
            queryset = queryset.filter(
                Q(return_number__icontains=search) |
                Q(original_invoice__supplier__name__icontains=search)
            )
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if return_type:
            queryset = queryset.filter(return_type=return_type)
        if supplier_id:
            queryset = queryset.filter(original_invoice__supplier_id=supplier_id)
        
        # Apply ordering
        if order_by.startswith('-'):
            queryset = queryset.order_by(order_by, '-id')
        else:
            queryset = queryset.order_by(order_by, 'id')
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate statistics
        all_returns = PurchaseReturn.objects.all()
        context['total_returns'] = all_returns.count()
        
        # Total amount
        total_amount = all_returns.aggregate(total=Sum('total_amount'))['total'] or 0
        context['total_returns_amount'] = total_amount
        
        # This month's returns
        current_month = timezone.now().replace(day=1)
        month_returns = all_returns.filter(date__gte=current_month).count()
        context['monthly_returns'] = month_returns
        
        # Today's returns
        today = timezone.now().date()
        daily_returns = all_returns.filter(date=today).count()
        context['daily_returns'] = daily_returns
        
        # Get suppliers for filter
        context['suppliers'] = CustomerSupplier.objects.filter(
            type__in=['supplier', 'both']
        ).order_by('name')
        
        # Current filters
        context['current_filters'] = {
            'search': self.request.GET.get('search', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'supplier': self.request.GET.get('supplier', ''),
        }
        
        # Current ordering
        context['current_order'] = self.request.GET.get('order_by', '-date')
        
        return context


class PurchaseReturnCreateView(LoginRequiredMixin, CreateView):
    model = PurchaseReturn
    template_name = 'purchases/return_add.html'
    fields = ['return_number', 'original_invoice', 'supplier_return_number', 'date', 'return_type', 'return_reason', 'notes']
    success_url = reverse_lazy('purchases:return_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get only purchase invoices that can have returns
        from django.db.models import Q, Sum
        
        # Get invoices with full returns (should be excluded completely)
        invoices_with_full_returns = PurchaseReturn.objects.filter(
            return_type='full'
        ).values_list('original_invoice_id', flat=True)
        
        # Get all purchase invoices excluding those with full returns
        all_invoices = PurchaseInvoice.objects.select_related('supplier').exclude(
            id__in=invoices_with_full_returns
        ).order_by('-date')
        
        # Filter out invoices where the sum of partial returns equals the original total
        available_invoices = []
        
        for invoice in all_invoices:
            # Check if this invoice has any items that can still be returned
            partial_returns = PurchaseReturn.objects.filter(
                original_invoice=invoice,
                return_type='partial'
            )
            total_returned = partial_returns.aggregate(total=Sum('total_amount'))['total'] or 0
            
            # If the total returned is less than the invoice total, it can have more returns
            if total_returned < invoice.total_amount:
                available_invoices.append(invoice)
        
        context['invoices'] = available_invoices
        
        # Generate suggested return number
        try:
            from core.models import DocumentSequence
            seq = DocumentSequence.objects.get(document_type='purchase_return')
            # Calculate next number without saving
            next_num = seq.current_number
            # Format the number
            formatted_number = f"{seq.prefix}{next_num:0{seq.digits}d}"
            context['suggested_return_number'] = formatted_number
        except DocumentSequence.DoesNotExist:
            context['suggested_return_number'] = "يجب إعداد تسلسل أرقام المستندات لمردود المشتريات أولاً"
        
        return context
    
    def form_valid(self, form):
        # Set the user who created the return
        form.instance.created_by = self.request.user
        
        # Save the return
        try:
            response = super().form_valid(form)
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        
        # Process return items from POST data
        self.process_return_items()
        
        # Update totals
        self.update_return_totals()
        
        # Create inventory movements (subtract returned items)
        self.create_inventory_movements()
        
        # إنشاء حركة حساب للمورد
        create_purchase_return_account_transaction(self.object, self.request.user)
        
        # إنشاء القيد المحاسبي
        create_purchase_return_journal_entry(self.object, self.request.user)
        
        # تسجيل النشاط
        from core.signals import log_activity
        log_activity(
            user=self.request.user,
            action_type='CREATE',
            obj=self.object,
            description=f'تم إنشاء مردود مشتريات رقم: {self.object.return_number} للفاتورة: {self.object.original_invoice.supplier_invoice_number}',
            request=self.request
        )
        
        messages.success(self.request, f'تم إنشاء مردود المشتريات رقم {self.object.return_number} بنجاح')
        return response
    
    def process_return_items(self):
        """معالجة عناصر المردود من البيانات المرسلة"""
        from .models import PurchaseReturnItem
        
        # Get items data from POST
        item_ids = self.request.POST.getlist('item_id[]')
        returned_quantities = self.request.POST.getlist('returned_quantity[]')
        
        for i, item_id in enumerate(item_ids):
            if item_id and returned_quantities[i]:
                try:
                    from decimal import Decimal
                    original_item = PurchaseInvoiceItem.objects.get(id=item_id)
                    returned_qty = Decimal(str(returned_quantities[i]))
                    
                    if returned_qty > 0:
                        PurchaseReturnItem.objects.create(
                            return_invoice=self.object,
                            original_item=original_item,
                            product=original_item.product,
                            returned_quantity=returned_qty,
                            unit_price=original_item.unit_price,
                            tax_rate=original_item.tax_rate
                        )
                except (PurchaseInvoiceItem.DoesNotExist, ValueError):
                    continue
    
    def update_return_totals(self):
        """تحديث إجماليات المردود"""
        from .models import PurchaseReturnItem
        
        items = PurchaseReturnItem.objects.filter(return_invoice=self.object)
        
        subtotal = sum(item.returned_quantity * item.unit_price for item in items)
        tax_amount = sum(item.tax_amount for item in items)
        total_amount = subtotal + tax_amount
        
        self.object.subtotal = subtotal
        self.object.tax_amount = tax_amount
        self.object.total_amount = total_amount
        self.object.save()
        # 🔧 إعادة تحميل الكائن من قاعدة البيانات لضمان استخدام القيم المحدثة في القيد المحاسبي
        self.object.refresh_from_db()
    
    def create_inventory_movements(self):
        """إنشاء حركات المخزون للمردود (طرح)"""
        for item in self.object.items.all():
            # استخدام مستودع الفاتورة الأصلية أو المستودع الافتراضي
            warehouse = self.object.original_invoice.warehouse if self.object.original_invoice.warehouse else Warehouse.objects.first()
            if warehouse:
                InventoryMovement.objects.create(
                    movement_number=f"RTN-{self.object.return_number}-{item.id}",
                    date=self.object.date,
                    product=item.product,
                    warehouse=warehouse,
                    movement_type='out',  # طرح من المخزون
                    quantity=item.returned_quantity,
                    unit_cost=item.unit_price,
                    total_cost=item.returned_quantity * item.unit_price,
                    reference_type='purchase_return',
                    reference_id=self.object.id,
                    notes=f'مردود مشتريات رقم {self.object.return_number}',
                    created_by=self.request.user
                )


class PurchaseReturnDetailView(LoginRequiredMixin, DetailView):
    model = PurchaseReturn
    template_name = 'purchases/return_detail.html'
    context_object_name = 'return_invoice'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get return items
        context['items'] = self.object.items.select_related('product', 'original_item').all()
        
        # Calculate subtotal without tax for each item
        items_with_subtotal = []
        for item in context['items']:
            item.subtotal = item.returned_quantity * item.unit_price
            items_with_subtotal.append(item)
        context['items'] = items_with_subtotal
        
        # إضافة القيود المحاسبية المرتبطة
        from journal.models import JournalEntry
        context['journal_entries'] = JournalEntry.objects.filter(purchase_return=self.object).select_related('created_by')
        
        return context


class PurchaseReturnUpdateView(LoginRequiredMixin, UpdateView):
    model = PurchaseReturn
    template_name = 'purchases/return_edit.html'
    fields = ['return_number', 'date', 'return_type', 'return_reason', 'notes']
    
    def get_success_url(self):
        return reverse_lazy('purchases:return_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get return items
        context['items'] = self.object.items.select_related('product', 'original_item').all()
        
        return context
    
    def form_valid(self, form):
        # تسجيل النشاط
        from core.signals import log_activity
        log_activity(
            user=self.request.user,
            action='UPDATE',
            model_name='PurchaseReturn',
            object_id=self.object.id,
            details=f'تم تحديث مردود مشتريات رقم: {self.object.return_number}'
        )
        
        response = super().form_valid(form)
        messages.success(self.request, f'تم تحديث مردود المشتريات رقم {self.object.return_number} بنجاح')
        return response


class PurchaseReturnDeleteView(LoginRequiredMixin, DeleteView):
    model = PurchaseReturn
    template_name = 'purchases/return_delete.html'
    success_url = reverse_lazy('purchases:return_list')
    context_object_name = 'return_invoice'
    
    def delete(self, request, *args, **kwargs):
        try:
            return_obj = self.get_object()
            return_number = return_obj.return_number
            
            # حذف حركة حساب المورد المرتبطة بالمردود
            delete_transaction_by_reference('purchase_return', return_obj.id)
            
            # Delete related inventory movements
            InventoryMovement.objects.filter(
                reference_type='purchase_return',
                reference_id=return_obj.id
            ).delete()
            
            # تسجيل النشاط قبل الحذف
            from core.signals import log_activity
            log_activity(
                user=request.user,
                action_type='DELETE',
                obj=return_obj,
                description=f'تم حذف مردود مشتريات رقم: {return_number}',
                request=request
            )
            
            # Delete the return
            result = super().delete(request, *args, **kwargs)
            
            messages.success(
                request, 
                f'تم حذف مردود المشتريات رقم {return_number} بنجاح'
            )
            
            return result
            
        except Exception as e:
            messages.error(
                request, 
                f'حدث خطأ أثناء حذف المردود: {str(e)}'
            )
            return redirect('purchases:return_list')


# =================== AJAX Views ===================

from django.http import JsonResponse
from .models import PurchaseReturn, PurchaseReturnItem

@csrf_exempt
def get_invoice_items(request, invoice_id):
    """جلب عناصر الفاتورة عبر AJAX"""
    try:
        print(f"طلب جلب عناصر الفاتورة رقم: {invoice_id}")
        
        invoice = PurchaseInvoice.objects.get(id=invoice_id)
        items = invoice.items.select_related('product').all()
        
        print(f"تم العثور على {items.count()} عنصر في الفاتورة")
        
        items_data = []
        for item in items:
            # Calculate total returned quantity for this item
            total_returned = PurchaseReturnItem.objects.filter(
                original_item=item
            ).aggregate(total=Sum('returned_quantity'))['total'] or 0
            
            remaining_quantity = item.quantity - total_returned
            
            print(f"المنتج {item.product.name}: الكمية الأصلية={item.quantity}, المرتجع={total_returned}, المتبقي={remaining_quantity}")
            
            if remaining_quantity > 0:  # Only show items that can still be returned
                items_data.append({
                    'id': item.id,
                    'product_id': item.product.id,
                    'product_name': item.product.name,
                    'product_code': item.product.code,
                    'original_quantity': float(item.quantity),
                    'returned_quantity': float(total_returned),
                    'remaining_quantity': float(remaining_quantity),
                    'unit_price': float(item.unit_price),
                    'tax_rate': float(item.tax_rate),
                })
        
        print(f"عدد العناصر المتاحة للإرجاع: {len(items_data)}")
        
        return JsonResponse({
            'success': True,
            'items': items_data,
            'invoice_number': invoice.supplier_invoice_number,
            'supplier_name': invoice.supplier.name,
            'invoice_date': invoice.date.strftime('%Y-%m-%d'),
        })
        
    except PurchaseInvoice.DoesNotExist:
        print(f"الفاتورة رقم {invoice_id} غير موجودة")
        return JsonResponse({
            'success': False,
            'message': 'الفاتورة غير موجودة'
        })
    except Exception as e:
        print(f"خطأ في جلب عناصر الفاتورة: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'حدث خطأ: {str(e)}'
        })

class PurchaseReportView(LoginRequiredMixin, TemplateView):
    template_name = 'purchases/purchase_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from django.utils import timezone
        from datetime import datetime, timedelta
        from django.db.models import Sum, Count
        
        # الحصول على التواريخ من الطلب
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        # التواريخ الافتراضية (بداية السنة الحالية إلى اليوم)
        today = timezone.now().date()
        if not start_date:
            # بداية السنة الحالية
            start_date = today.replace(month=1, day=1).strftime('%Y-%m-%d')
        if not end_date:
            end_date = today.strftime('%Y-%m-%d')
        
        # تحويل التواريخ لاستخدامها في الاستعلامات
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # فواتير المشتريات في الفترة المحددة
        purchase_invoices = PurchaseInvoice.objects.filter(
            date__gte=start_date_obj,
            date__lte=end_date_obj
        ).select_related('supplier').order_by('-date')
        
        # إحصائيات المشتريات
        stats = {
            'total_invoices': purchase_invoices.count(),
            'total_amount': purchase_invoices.aggregate(total=Sum('total_amount'))['total'] or 0,
            'total_tax': purchase_invoices.aggregate(total=Sum('tax_amount'))['total'] or 0,
            'cash_purchases': purchase_invoices.filter(payment_type='cash').aggregate(total=Sum('total_amount'))['total'] or 0,
            'credit_purchases': purchase_invoices.filter(payment_type='credit').aggregate(total=Sum('total_amount'))['total'] or 0,
        }
        
        # مشتريات حسب الموردين
        supplier_purchases_data = purchase_invoices.values('supplier__name').annotate(
            total_amount=Sum('total_amount'),
            invoice_count=Count('id')
        ).order_by('-total_amount')[:10]  # أفضل 10 موردين
        
        # تحويل البيانات لتنسيق JavaScript
        supplier_purchases = []
        for item in supplier_purchases_data:
            supplier_purchases.append({
                'name': item['supplier__name'] or 'غير محدد',
                'amount': float(item['total_amount'] or 0),
                'count': item['invoice_count']
            })
        
        # مشتريات حسب اليوم  
        daily_purchases_data = purchase_invoices.extra({'date': "date(date)"}).values('date').annotate(
            total_amount=Sum('total_amount'),
            invoice_count=Count('id')
        ).order_by('date')
        
        # تحويل البيانات لتنسيق JavaScript
        daily_purchases = []
        for item in daily_purchases_data:
            daily_purchases.append({
                'date': item['date'].strftime('%Y-%m-%d') if item['date'] else '',
                'amount': float(item['total_amount'] or 0),
                'count': item['invoice_count']
            })
        
        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'purchase_invoices': purchase_invoices,
            'stats': stats,
            'supplier_purchases': supplier_purchases,
            'daily_purchases': daily_purchases,
        })
        
        return context


class PurchaseStatementView(LoginRequiredMixin, TemplateView):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('purchases.can_view_purchase_statement') and not request.user.is_superuser:
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, 'ليس لديك صلاحية لعرض كشف المشتريات')
            return redirect('/')
        # تسجيل الدخول إلى سجل الأنشطة عند عرض كشف المشتريات
        from core.signals import log_activity
        log_activity(request.user, 'VIEW', None, 'عرض كشف المشتريات', request)
        return super().dispatch(request, *args, **kwargs)
    """عرض كشف المشتريات"""
    template_name = 'purchases/purchase_statement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # فترة البحث الافتراضية (الشهر الحالي)
        today = timezone.now().date()
        start_date = today.replace(day=1)
        end_date = today
        
        # تطبيق الفلاتر من الطلب
        if self.request.GET.get('start_date'):
            start_date = datetime.strptime(self.request.GET.get('start_date'), '%Y-%m-%d').date()
        if self.request.GET.get('end_date'):
            end_date = datetime.strptime(self.request.GET.get('end_date'), '%Y-%m-%d').date()
        
        # معالجة الترتيب
        sort_by = self.request.GET.get('sort', 'date')
        sort_direction = self.request.GET.get('dir', 'asc')
        
        # جلب فواتير المشتريات مرتبة حسب التاريخ
        purchase_invoices = PurchaseInvoice.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('date', 'invoice_number')
        
        # حساب الرصيد التراكمي
        running_balance = Decimal('0')
        statement_data = []
        
        for invoice in purchase_invoices:
            # قيمة الفاتورة قبل الضريبة وبعد الخصم
            debit_amount = invoice.subtotal
            # قيمة الفاتورة شامل الضريبة
            total_with_tax = invoice.total_amount
            running_balance += debit_amount
            
            statement_data.append({
                'date': invoice.date,
                'document_number': invoice.invoice_number,
                'description': 'فاتورة مشتريات',
                'debit': debit_amount,
                'total_with_tax': total_with_tax,
                'balance': running_balance,
                'invoice': invoice
            })
        
        # تطبيق الترتيب على البيانات
        if sort_by in ['date', 'document_number', 'description', 'debit', 'total_with_tax', 'balance']:
            reverse_sort = sort_direction == 'desc'
            if sort_by == 'date':
                statement_data = sorted(statement_data, key=lambda x: x['date'], reverse=reverse_sort)
            elif sort_by == 'document_number':
                statement_data = sorted(statement_data, key=lambda x: x['document_number'], reverse=reverse_sort)
            elif sort_by == 'description':
                statement_data = sorted(statement_data, key=lambda x: x['description'], reverse=reverse_sort)
            elif sort_by == 'debit':
                statement_data = sorted(statement_data, key=lambda x: x['debit'], reverse=reverse_sort)
            elif sort_by == 'total_with_tax':
                statement_data = sorted(statement_data, key=lambda x: x['total_with_tax'], reverse=reverse_sort)
            elif sort_by == 'balance':
                statement_data = sorted(statement_data, key=lambda x: x['balance'], reverse=reverse_sort)
        
        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'statement_data': statement_data,
            'final_balance': running_balance,
            'current_sort': sort_by,
            'sort_direction': sort_direction,
        })
        
        return context


class PurchaseReturnStatementView(LoginRequiredMixin, TemplateView):
    """عرض كشف مردودات المشتريات"""
    template_name = 'purchases/purchase_return_statement.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # فترة البحث الافتراضية (الشهر الحالي)
        today = timezone.now().date()
        start_date = today.replace(day=1)
        end_date = today
        
        # تطبيق الفلاتر من الطلب
        if self.request.GET.get('start_date'):
            start_date = datetime.strptime(self.request.GET.get('start_date'), '%Y-%m-%d').date()
        if self.request.GET.get('end_date'):
            end_date = datetime.strptime(self.request.GET.get('end_date'), '%Y-%m-%d').date()
        
        # جلب مردودات المشتريات مرتبة حسب التاريخ
        purchase_returns = PurchaseReturn.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('date', 'return_number')
        
        # حساب الرصيد التراكمي (دائن - يقلل من المديونية)
        running_balance = Decimal('0')
        statement_data = []
        
        for return_item in purchase_returns:
            # قيمة المردود قبل الضريبة وبعد الخصم
            credit_amount = return_item.subtotal
            running_balance += credit_amount
            
            statement_data.append({
                'date': return_item.date,
                'document_number': return_item.return_number,
                'description': 'مردود مشتريات',
                'credit': credit_amount,
                'balance': running_balance,
                'return_item': return_item
            })
        
        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'statement_data': statement_data,
            'final_balance': running_balance,
        })
        
        return context


@login_required
@require_POST
def send_debitnote_to_jofotara(request, pk):
    """إرسال إشعار خصم إلى JoFotara"""
    # للطلبات AJAX، نتحقق من الـ header ونعيد JSON response
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if not is_ajax:
        return JsonResponse({
            'success': False,
            'error': 'هذه الدالة تستخدم للطلبات AJAX فقط'
        }, status=400)
    
    try:
        # Get the debit note
        debit_note = get_object_or_404(PurchaseDebitNote, pk=pk)
        
        # Check if user has permission to send debit notes
        if not request.user.has_perm('purchases.can_send_to_jofotara'):
            return JsonResponse({
                'success': False,
                'error': 'ليس لديك صلاحية إرسال الإشعارات الخصومات إلى JoFotara'
            })
        
        # Import the utility function
        from settings.utils import send_debit_note_to_jofotara
        
        # Send the debit note
        result = send_debit_note_to_jofotara(debit_note, request.user)
        
        if result['success']:
            # Update debit note with JoFotara UUID if available
            if 'uuid' in result:
                debit_note.jofotara_uuid = result['uuid']
                debit_note.jofotara_sent_at = timezone.now()
                debit_note.jofotara_verification_url = result.get('verification_url')
                debit_note.save()
            
            messages.success(request, f'تم إرسال الإشعار الخصم {debit_note.note_number} إلى JoFotara بنجاح')
        else:
            messages.error(request, f'فشل في إرسال الإشعار الخصم: {result.get("error", "خطأ غير معروف")}')
        
        return JsonResponse(result)
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending debit note to JoFotara: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'خطأ في النظام: {str(e)}'
        })


class PurchaseDebitNoteReportView(LoginRequiredMixin, ListView):
    """كشف مذكرات الدين"""
    model = PurchaseDebitNote
    template_name = 'purchases/debitnote_report.html'
    context_object_name = 'debitnotes'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = PurchaseDebitNote.objects.select_related('supplier', 'created_by').all()
        
        # فلترة حسب التاريخ
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        supplier = self.request.GET.get('supplier')
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if supplier:
            queryset = queryset.filter(supplier_id=supplier)
            
        return queryset.order_by('-date', '-note_number')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # إضافة إجماليات
        queryset = self.get_queryset()
        context['total_amount'] = queryset.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        context['total_count'] = queryset.count()
        
        # إضافة قائمة الموردين للفلترة
        from customers.models import CustomerSupplier
        context['suppliers'] = CustomerSupplier.objects.filter(
            type__in=['supplier', 'both']
        ).order_by('name')
        
        # إضافة قيم الفلترة الحالية
        context['filters'] = {
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'supplier': self.request.GET.get('supplier', ''),
        }
        
        try:
            company_settings = CompanySettings.objects.first()
            if company_settings and company_settings.base_currency:
                context['base_currency'] = company_settings.base_currency
        except Exception:
            pass
            
        return context


class PurchaseDebitNoteUpdateView(LoginRequiredMixin, UpdateView):
    model = PurchaseDebitNote
    fields = ['supplier', 'date', 'description', 'subtotal', 'tax_rate', 'tax_amount', 'total_amount']
    template_name = 'purchases/debitnote_form.html'
    context_object_name = 'debitnote'
    
    def get_success_url(self):
        return reverse_lazy('purchases:debitnote_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        
        # Update journal entry if exists
        if hasattr(self.object, 'journal_entry') and self.object.journal_entry:
            try:
                # Update supplier account balance
                create_debit_note_journal_entry(self.object, self.request.user)
            except Exception as e:
                messages.error(self.request, f'خطأ في تحديث القيد المحاسبي: {str(e)}')
        
        messages.success(self.request, 'تم تحديث مذكرة الدين بنجاح')
        return response


class PurchaseDebitNoteDeleteView(LoginRequiredMixin, DeleteView):
    model = PurchaseDebitNote
    template_name = 'purchases/debitnote_confirm_delete.html'
    context_object_name = 'debitnote'
    success_url = reverse_lazy('purchases:debitnote_list')
    
    def delete(self, request, *args, **kwargs):
        # Delete associated journal entry if exists
        if hasattr(self.get_object(), 'journal_entry') and self.get_object().journal_entry:
            try:
                self.get_object().journal_entry.delete()
            except Exception as e:
                messages.error(request, f'خطأ في حذف القيد المحاسبي: {str(e)}')
        
        messages.success(request, 'تم حذف مذكرة الدين بنجاح')
        return super().delete(request, *args, **kwargs)
