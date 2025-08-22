from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, DetailView, View
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from .models import PurchaseInvoice, PurchaseInvoiceItem, PurchaseReturn, PurchaseReturnItem, PurchaseReturn, PurchaseReturnItem
from customers.models import CustomerSupplier
from products.models import Product
from inventory.models import InventoryMovement, Warehouse
from accounts.services import create_purchase_invoice_transaction, create_purchase_return_transaction, delete_transaction_by_reference
from journal.services import JournalService
from core.models import DocumentSequence


def create_purchase_invoice_journal_entry(invoice, user):
    """إنشاء قيد محاسبي لفاتورة المشتريات"""
    try:
        # إنشاء القيد المحاسبي باستخدام JournalService
        JournalService.create_purchase_invoice_entry(invoice, user)
    except Exception as e:
        print(f"خطأ في إنشاء القيد المحاسبي لفاتورة المشتريات: {e}")
        # لا نوقف العملية في حالة فشل إنشاء القيد المحاسبي
        pass

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
        
        # إذا كانت طريقة الدفع ليست نقداً، نسجل حركة في حساب المورد
        if invoice.payment_type != 'cash' and invoice.supplier:
            # توليد رقم الحركة
            transaction_number = f"PURCH-{uuid.uuid4().hex[:8].upper()}"
            
            # حساب الرصيد السابق
            last_transaction = AccountTransaction.objects.filter(
                customer_supplier=invoice.supplier
            ).order_by('-created_at').first()
            
            previous_balance = last_transaction.balance_after if last_transaction else Decimal('0')
            
            # إنشاء حركة دائنة للمورد (زيادة الذمم الدائنة)
            new_balance = previous_balance + invoice.total_amount
            
            AccountTransaction.objects.create(
                transaction_number=transaction_number,
                date=invoice.date,
                customer_supplier=invoice.supplier,
                transaction_type='purchase_invoice',
                direction='credit',
                amount=invoice.total_amount,
                reference_type='purchase_invoice',
                reference_id=invoice.id,
                description=f'مشتريات - فاتورة رقم {invoice.invoice_number}',
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
        import uuid
        
        # إذا كان هناك مورد، نسجل حركة مدينة (تقليل الذمم الدائنة)
        if return_invoice.supplier:
            # توليد رقم الحركة
            transaction_number = f"PRET-{uuid.uuid4().hex[:8].upper()}"
            
            # حساب الرصيد السابق
            last_transaction = AccountTransaction.objects.filter(
                customer_supplier=return_invoice.supplier
            ).order_by('-created_at').first()
            
            previous_balance = last_transaction.balance_after if last_transaction else Decimal('0')
            
            # إنشاء حركة مدينة للمورد (تقليل الذمم الدائنة)
            new_balance = previous_balance - return_invoice.total_amount
            
            AccountTransaction.objects.create(
                transaction_number=transaction_number,
                date=return_invoice.date,
                customer_supplier=return_invoice.supplier,
                transaction_type='purchase_return',
                direction='debit',
                amount=return_invoice.total_amount,
                reference_type='purchase_return',
                reference_id=return_invoice.id,
                description=f'مردود مشتريات - فاتورة رقم {return_invoice.return_number}',
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

class PurchaseInvoiceListView(LoginRequiredMixin, ListView):
    model = PurchaseInvoice
    template_name = 'purchases/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = PurchaseInvoice.objects.select_related('supplier', 'warehouse').order_by('-date', '-id')
        
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
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
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
        
        return context

class PurchaseInvoiceCreateView(LoginRequiredMixin, View):
    template_name = 'purchases/invoice_add.html'
    
    def get(self, request, *args, **kwargs):
        products = Product.objects.filter(is_active=True).order_by('name')
        
        # إضافة آخر سعر شراء لكل منتج
        products_with_prices = []
        for product in products:
            product.last_purchase_price = product.get_last_purchase_price()
            products_with_prices.append(product)
        
        # إضافة رقم الفاتورة التالي من DocumentSequence
        try:
            sequence = DocumentSequence.objects.get(document_type='purchase_invoice')
            next_invoice_number = sequence.get_formatted_number()
        except DocumentSequence.DoesNotExist:
            # إنشاء تسلسل جديد إذا لم يكن موجوداً
            sequence = DocumentSequence.objects.create(
                document_type='purchase_invoice',
                prefix='PUR-',
                digits=6,
                current_number=1
            )
            next_invoice_number = sequence.get_formatted_number()
        
        context = {
            'suppliers': CustomerSupplier.objects.filter(
                Q(type='supplier') | Q(type='both')
            ).order_by('name'),
            'warehouses': Warehouse.objects.filter(is_active=True).order_by('name'),
            'products': products_with_prices,
            'next_invoice_number': next_invoice_number
        }
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        try:
            # الحصول على رقم الفاتورة التالي من DocumentSequence
            try:
                sequence = DocumentSequence.objects.get(document_type='purchase_invoice')
                invoice_number = sequence.get_next_number()
            except DocumentSequence.DoesNotExist:
                # إنشاء تسلسل جديد إذا لم يكن موجوداً
                sequence = DocumentSequence.objects.create(
                    document_type='purchase_invoice',
                    prefix='PUR-',
                    digits=6,
                    current_number=1
                )
                invoice_number = sequence.get_next_number()
            
            # استلام البيانات الأساسية للفاتورة
            supplier_invoice_number = request.POST.get('supplier_invoice_number', '').strip()
            date = request.POST.get('date')
            supplier_id = request.POST.get('supplier')
            warehouse_id = request.POST.get('warehouse')
            payment_type = request.POST.get('payment_type')
            notes = request.POST.get('notes', '').strip()
            
            # التحقق من صحة البيانات
            if not all([supplier_invoice_number, date, supplier_id, payment_type]):
                messages.error(request, 'جميع الحقول الأساسية مطلوبة!')
                return self.get(request)
            
            # الحصول على المورد
            try:
                supplier = CustomerSupplier.objects.get(id=supplier_id)
            except CustomerSupplier.DoesNotExist:
                messages.error(request, 'المورد المحدد غير موجود!')
                return self.get(request)
            
            # الحصول على المستودع (اختياري)
            warehouse = None
            if warehouse_id:
                try:
                    warehouse = Warehouse.objects.get(id=warehouse_id, is_active=True)
                except Warehouse.DoesNotExist:
                    messages.error(request, 'المستودع المحدد غير موجود!')
                    return self.get(request)
            
            # الحصول على المستخدم الحالي
            created_by = request.user
            
            # إنشاء الفاتورة
            invoice = PurchaseInvoice.objects.create(
                invoice_number=invoice_number,
                supplier_invoice_number=supplier_invoice_number,
                date=date,
                supplier=supplier,
                warehouse=warehouse,
                payment_type=payment_type,
                notes=notes,
                created_by=created_by,
                subtotal=0,
                tax_amount=0,
                total_amount=0
            )
            
            # معالجة المنتجات
            products_data = []
            product_ids = request.POST.getlist('product_id[]')
            quantities = request.POST.getlist('quantity[]')
            unit_prices = request.POST.getlist('unit_price[]')
            tax_rates = request.POST.getlist('tax_rate[]')
            row_taxes = request.POST.getlist('row_tax[]')
            
            if product_ids and quantities and unit_prices:
                subtotal = 0
                total_tax = 0
                for i, product_id in enumerate(product_ids):
                    if product_id and i < len(quantities) and i < len(unit_prices):
                        try:
                            from decimal import Decimal
                            product = Product.objects.get(id=product_id)
                            quantity = Decimal(str(quantities[i]))
                            unit_price = Decimal(str(unit_prices[i]))
                            
                            # حساب المجموع الفرعي للمنتج
                            row_subtotal = quantity * unit_price
                            
                            # الحصول على نسبة الضريبة وقيمة الضريبة
                            tax_rate = Decimal(str(tax_rates[i])) if i < len(tax_rates) and tax_rates[i] else Decimal('0')
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
                            
                            # إنشاء حركة مخزون (إضافة الكمية المشتراة)
                            try:
                                # استخدام المستودع المحدد في الفاتورة أو المستودع الافتراضي
                                warehouse = invoice.warehouse if invoice.warehouse else Warehouse.objects.filter(is_active=True).first()
                                if warehouse:
                                    InventoryMovement.objects.create(
                                        movement_number=f"PUR-{invoice.invoice_number}-{i+1}",
                                        date=invoice.date,
                                        product=product,
                                        warehouse=warehouse,
                                        movement_type='in',
                                        reference_type='purchase_invoice',
                                        reference_id=invoice.id,
                                        quantity=quantity,
                                        unit_cost=unit_price,
                                        total_cost=row_subtotal,
                                        notes=f"شراء من فاتورة رقم {invoice.invoice_number}",
                                        created_by=created_by
                                    )
                            except Exception as inventory_error:
                                # في حالة فشل إنشاء حركة المخزون، نسجل الخطأ لكن لا نوقف العملية
                                messages.warning(request, f'تم حفظ الفاتورة لكن حدث خطأ في تحديث المخزون للمنتج {product.name}: {str(inventory_error)}')
                            
                            subtotal += row_subtotal
                            total_tax += tax_amount
                            
                        except (Product.DoesNotExist, ValueError):
                            continue
                
                # تحديث مجاميع الفاتورة
                invoice.subtotal = subtotal
                invoice.tax_amount = total_tax
                invoice.total_amount = subtotal + total_tax
                invoice.save()
                
                # إنشاء حركة حساب للمورد
                create_purchase_invoice_account_transaction(invoice, request.user)
                
                # إنشاء القيد المحاسبي
                create_purchase_invoice_journal_entry(invoice, request.user)
            
            messages.success(request, f'تم إنشاء فاتورة المشتريات رقم {invoice_number} بنجاح!')
            return redirect('purchases:invoice_detail', pk=invoice.pk)
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء إنشاء الفاتورة: {str(e)}')
            return self.get(request)

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
                'warehouses': Warehouse.objects.filter(is_active=True).order_by('name'),
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
            
            # تحديث بيانات الفاتورة الأساسية
            invoice.supplier_invoice_number = supplier_invoice_number
            invoice.date = date
            invoice.supplier = supplier
            invoice.warehouse = warehouse
            invoice.payment_type = payment_type
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
                            
                            # إنشاء حركة مخزون جديدة
                            warehouse_to_use = invoice.warehouse if invoice.warehouse else Warehouse.objects.filter(is_active=True).first()
                            if warehouse_to_use:
                                InventoryMovement.objects.create(
                                    movement_number=f"PUR-{invoice.invoice_number}-{i+1}",
                                    movement_type='purchase',
                                    movement_date=invoice.date,
                                    product=product,
                                    warehouse=warehouse_to_use,
                                    quantity=quantity,
                                    unit_price=unit_price,
                                    reference_type='purchase_invoice',
                                    reference_id=invoice.id,
                                    notes=f'تعديل فاتورة مشتريات {invoice.invoice_number}',
                                    created_by=request.user
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
                
                # إنشاء المعاملات المحاسبية الجديدة
                create_purchase_invoice_account_transaction(invoice, request.user)
                create_purchase_invoice_journal_entry(invoice, request.user)
                
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
            # حذف حركة حساب المورد المرتبطة بالفاتورة
            delete_transaction_by_reference('purchase_invoice', invoice.id)
            
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
    model = PurchaseReturn
    template_name = 'purchases/return_list.html'
    context_object_name = 'returns'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = PurchaseReturn.objects.select_related('original_invoice__supplier').order_by('-date', '-id')
        
        # Apply filters if provided
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        return_type = self.request.GET.get('return_type')
        supplier_id = self.request.GET.get('supplier')
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if return_type:
            queryset = queryset.filter(return_type=return_type)
        if supplier_id:
            queryset = queryset.filter(original_invoice__supplier_id=supplier_id)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate statistics
        all_returns = PurchaseReturn.objects.all()
        context['total_returns'] = all_returns.count()
        
        # Total amount
        total_amount = all_returns.aggregate(total=Sum('total_amount'))['total'] or 0
        context['total_amount'] = total_amount
        
        # Get suppliers for filter
        context['suppliers'] = CustomerSupplier.objects.filter(
            type__in=['supplier', 'both']
        ).order_by('name')
        
        # Current filters
        context['current_filters'] = {
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'return_type': self.request.GET.get('return_type', ''),
            'supplier': self.request.GET.get('supplier', ''),
        }
        
        return context


class PurchaseReturnCreateView(LoginRequiredMixin, CreateView):
    model = PurchaseReturn
    template_name = 'purchases/return_add.html'
    fields = ['return_number', 'original_invoice', 'date', 'return_type', 'return_reason', 'notes']
    success_url = reverse_lazy('purchases:return_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all purchase invoices for selection
        context['invoices'] = PurchaseInvoice.objects.select_related('supplier').order_by('-date')
        
        # Generate next return number
        last_return = PurchaseReturn.objects.order_by('-id').first()
        if last_return:
            try:
                last_number = int(last_return.return_number.split('-')[-1])
                next_number = last_number + 1
            except:
                next_number = 1
        else:
            next_number = 1
        
        context['suggested_return_number'] = f"RET-{next_number:06d}"
        
        return context
    
    def form_valid(self, form):
        # Set the user who created the return
        form.instance.created_by = self.request.user
        
        # Save the return
        response = super().form_valid(form)
        
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
        
        # التواريخ الافتراضية (الشهر الحالي)
        today = timezone.now().date()
        if not start_date:
            start_date = today.replace(day=1).strftime('%Y-%m-%d')
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
            running_balance += debit_amount
            
            statement_data.append({
                'date': invoice.date,
                'document_number': invoice.invoice_number,
                'description': 'فاتورة مشتريات',
                'debit': debit_amount,
                'balance': running_balance,
                'invoice': invoice
            })
        
        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'statement_data': statement_data,
            'final_balance': running_balance,
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
