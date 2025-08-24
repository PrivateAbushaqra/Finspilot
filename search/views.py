from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils.translation import gettext_lazy as _
import json
from core.models import AuditLog
from core.utils import get_client_ip

# Import models from different apps
try:
    from sales.models import SalesInvoice, SalesReturn
except ImportError:
    SalesInvoice = SalesReturn = None

try:
    from purchases.models import PurchaseInvoice, PurchaseReturn
except ImportError:
    PurchaseInvoice = PurchaseReturn = None

try:
    from receipts.models import PaymentReceipt
except ImportError:
    PaymentReceipt = None

try:
    from payments.models import PaymentVoucher
except ImportError:
    PaymentVoucher = None

try:
    from customers.models import CustomerSupplier
except ImportError:
    CustomerSupplier = None

try:
    from products.models import Product
except ImportError:
    Product = None

try:
    from journal.models import JournalEntry
except ImportError:
    JournalEntry = None

try:
    from revenues_expenses.models import RevenueExpenseEntry
except ImportError:
    RevenueExpenseEntry = None

try:
    from banks.models import BankAccount, BankTransfer
except ImportError:
    BankAccount = BankTransfer = None

try:
    from cashboxes.models import Cashbox, CashboxTransfer
except ImportError:
    Cashbox = CashboxTransfer = None

@login_required
def search_view(request):
    """عرض صفحة البحث الشامل"""
    # سجل النشاط: عرض صفحة البحث
    try:
        AuditLog.objects.create(
            user=request.user,
            action_type='view',
            content_type='search',
            object_id=None,
            description=_('عرض صفحة البحث الشامل'),
            ip_address=get_client_ip(request),
        )
    except Exception:
        pass
    return render(request, 'search/search.html')

@login_required
def search_api(request):
    """API للبحث الشامل في جميع المستندات"""
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        # سجل النشاط لمحاولة بحث قصيرة
        try:
            AuditLog.objects.create(
                user=request.user,
                action_type='view',
                content_type='search',
                object_id=None,
                description=_('محاولة بحث بدون كلمة كافية'),
                ip_address=get_client_ip(request),
            )
        except Exception:
            pass
        return JsonResponse({
            'results': [],
            'message': 'يرجى إدخال كلمة بحث أكثر من حرفين'
        })
    
    results = []
    
    try:
        # البحث في فواتير المبيعات
        if SalesInvoice:
            sales_invoices = SalesInvoice.objects.filter(
                Q(customer__name__icontains=query) |
                Q(invoice_number__icontains=query) |
                Q(notes__icontains=query)
            ).select_related('customer')[:10]
            
            for invoice in sales_invoices:
                results.append({
                    'type': 'sales_invoice',
                    'type_display': 'فاتورة مبيعات',
                    'title': f'فاتورة مبيعات #{invoice.invoice_number}',
                    'description': f'العميل: {invoice.customer.name} - التاريخ: {invoice.date} - المبلغ: {invoice.total_amount}',
                    'url': f'/sales/invoices/{invoice.id}/',
                    'date': invoice.date.strftime('%Y-%m-%d'),
                    'icon': 'fas fa-file-invoice'
                })
    except Exception as e:
        print(f"خطأ في البحث في فواتير المبيعات: {e}")
    
    try:
        # البحث في مردودات المبيعات
        if SalesReturn:
            sales_returns = SalesReturn.objects.filter(
                Q(customer__name__icontains=query) |
                Q(return_number__icontains=query) |
                Q(notes__icontains=query)
            ).select_related('customer')[:10]
            
            for return_doc in sales_returns:
                results.append({
                    'type': 'sales_return',
                    'type_display': 'مردود مبيعات',
                    'title': f'مردود مبيعات #{return_doc.return_number}',
                    'description': f'العميل: {return_doc.customer.name} - التاريخ: {return_doc.date} - المبلغ: {return_doc.total_amount}',
                    'url': f'/sales/returns/{return_doc.id}/',
                    'date': return_doc.date.strftime('%Y-%m-%d'),
                    'icon': 'fas fa-undo-alt'
                })
    except Exception as e:
        print(f"خطأ في البحث في مردودات المبيعات: {e}")
    
    try:
        # البحث في فواتير المشتريات
        if PurchaseInvoice:
            purchase_invoices = PurchaseInvoice.objects.filter(
                Q(supplier__name__icontains=query) |
                Q(invoice_number__icontains=query) |
                Q(notes__icontains=query)
            ).select_related('supplier')[:10]
            
            for invoice in purchase_invoices:
                results.append({
                    'type': 'purchase_invoice',
                    'type_display': 'فاتورة مشتريات',
                    'title': f'فاتورة مشتريات #{invoice.invoice_number}',
                    'description': f'المورد: {invoice.supplier.name} - التاريخ: {invoice.date} - المبلغ: {invoice.total_amount}',
                    'url': f'/purchases/invoices/{invoice.id}/',
                    'date': invoice.date.strftime('%Y-%m-%d'),
                    'icon': 'fas fa-shopping-cart'
                })
    except Exception as e:
        print(f"خطأ في البحث في فواتير المشتريات: {e}")
    
    try:
        # البحث في مردودات المشتريات
        if PurchaseReturn:
            purchase_returns = PurchaseReturn.objects.filter(
                Q(original_invoice__supplier__name__icontains=query) |
                Q(return_number__icontains=query) |
                Q(notes__icontains=query)
            ).select_related('original_invoice__supplier')[:10]
            
            for return_doc in purchase_returns:
                results.append({
                    'type': 'purchase_return',
                    'type_display': 'مردود مشتريات',
                    'title': f'مردود مشتريات #{return_doc.return_number}',
                    'description': f'المورد: {return_doc.original_invoice.supplier.name} - التاريخ: {return_doc.date} - المبلغ: {return_doc.total_amount}',
                    'url': f'/purchases/returns/{return_doc.id}/',
                    'date': return_doc.date.strftime('%Y-%m-%d'),
                    'icon': 'fas fa-undo-alt'
                })
    except Exception as e:
        print(f"خطأ في البحث في مردودات المشتريات: {e}")
    
    try:
        # البحث في سندات القبض
        if PaymentReceipt:
            receipts = PaymentReceipt.objects.filter(
                Q(customer__name__icontains=query) |
                Q(receipt_number__icontains=query) |
                Q(description__icontains=query)
            ).select_related('customer')[:10]
            
            for receipt in receipts:
                results.append({
                    'type': 'receipt',
                    'type_display': 'سند قبض',
                    'title': f'سند قبض #{receipt.receipt_number}',
                    'description': f'من: {receipt.customer.name} - التاريخ: {receipt.date} - المبلغ: {receipt.amount}',
                    'url': f'/receipts/{receipt.id}/',
                    'date': receipt.date.strftime('%Y-%m-%d'),
                    'icon': 'fas fa-receipt'
                })
    except Exception as e:
        print(f"خطأ في البحث في سندات القبض: {e}")
    
    try:
        # البحث في سندات الصرف
        if PaymentVoucher:
            payment_vouchers = PaymentVoucher.objects.filter(
                Q(beneficiary_name__icontains=query) |
                Q(supplier__name__icontains=query) |
                Q(voucher_number__icontains=query) |
                Q(description__icontains=query)
            ).select_related('supplier')[:10]
            
            for voucher in payment_vouchers:
                recipient_name = voucher.supplier.name if voucher.supplier else voucher.beneficiary_name
                results.append({
                    'type': 'payment_voucher',
                    'type_display': 'سند صرف',
                    'title': f'سند صرف #{voucher.voucher_number}',
                    'description': f'إلى: {recipient_name} - التاريخ: {voucher.date} - المبلغ: {voucher.amount}',
                    'url': f'/payments/vouchers/{voucher.id}/',
                    'date': voucher.date.strftime('%Y-%m-%d'),
                    'icon': 'fas fa-money-bill-wave'
                })
    except Exception as e:
        print(f"خطأ في البحث في سندات الصرف: {e}")
    
    try:
        # البحث في العملاء والموردين
        if CustomerSupplier:
            customers = CustomerSupplier.objects.filter(
                Q(name__icontains=query) |
                Q(phone__icontains=query) |
                Q(email__icontains=query) |
                Q(city__icontains=query)
            )[:10]
            
            for customer in customers:
                type_display = 'عميل' if customer.type == 'customer' else 'مورد' if customer.type == 'supplier' else 'عميل ومورد'
                results.append({
                    'type': 'customer',
                    'type_display': type_display,
                    'title': customer.name,
                    'description': f'الهاتف: {customer.phone or "غير محدد"} - المدينة: {customer.city or "غير محددة"} - الرصيد: {customer.current_balance}',
                    'url': f'/customers/{customer.id}/',
                    'date': customer.created_at.strftime('%Y-%m-%d') if hasattr(customer, 'created_at') else '',
                    'icon': 'fas fa-users'
                })
    except Exception as e:
        print(f"خطأ في البحث في العملاء والموردين: {e}")
    
    try:
        # البحث في المنتجات
        if Product:
            products = Product.objects.filter(
                Q(name__icontains=query) |
                Q(code__icontains=query) |
                Q(description__icontains=query)
            )[:10]
            
            for product in products:
                results.append({
                    'type': 'product',
                    'type_display': 'منتج',
                    'title': f'{product.name} ({product.code})',
                    'description': f'الفئة: {product.category.name if product.category else "غير محددة"} - السعر: {product.sale_price} - المخزون: {product.current_stock}',
                    'url': f'/products/detail/{product.id}/',
                    'date': '',
                    'icon': 'fas fa-box'
                })
    except Exception as e:
        print(f"خطأ في البحث في المنتجات: {e}")
    
    try:
        # البحث في القيود المحاسبية
        if JournalEntry:
            journal_entries = JournalEntry.objects.filter(
                Q(description__icontains=query) |
                Q(entry_number__icontains=query)
            )[:10]
            
            for entry in journal_entries:
                results.append({
                    'type': 'journal_entry',
                    'type_display': 'قيد محاسبي',
                    'title': f'قيد محاسبي #{entry.entry_number or entry.id}',
                    'description': f'الوصف: {entry.description} - التاريخ: {entry.entry_date} - المبلغ: {entry.total_amount}',
                    'url': f'/journal/entries/{entry.id}/',
                    'date': entry.entry_date.strftime('%Y-%m-%d'),
                    'icon': 'fas fa-book'
                })
    except Exception as e:
        print(f"خطأ في البحث في القيود المحاسبية: {e}")
    
    # البحث في قيود الإيرادات والمصروفات
    try:
        if RevenueExpenseEntry:
            revenue_expense_entries = RevenueExpenseEntry.objects.filter(
                Q(description__icontains=query) |
                Q(category__name__icontains=query)
            ).select_related('category')[:10]
            
            for entry in revenue_expense_entries:
                entry_type = 'إيراد' if entry.type == 'revenue' else 'مصروف'
                results.append({
                    'type': 'revenue_expense',
                    'type_display': entry_type,
                    'title': f'{entry_type} - {entry.category.name if entry.category else "غير محدد"}',
                    'description': f'الوصف: {entry.description} - التاريخ: {entry.date} - المبلغ: {entry.amount}',
                    'url': f'/revenues-expenses/entries/{entry.id}/',
                    'date': entry.date.strftime('%Y-%m-%d'),
                    'icon': 'fas fa-chart-line'
                })
    except Exception as e:
        print(f"خطأ في البحث في الإيرادات والمصروفات: {e}")
        pass  # في حالة وجود مشكلة في النموذج
    
    # ترتيب النتائج حسب التاريخ (الأحدث أولاً)
    results.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    # سجل النشاط لعملية البحث
    try:
        AuditLog.objects.create(
            user=request.user,
            action_type='view',
            content_type='search',
            object_id=None,
            description=_('تنفيذ بحث شامل') + f": '{query}' (نتائج: {len(results)})",
            ip_address=get_client_ip(request),
        )
    except Exception:
        pass

    return JsonResponse({
        'results': results,
        'total': len(results),
        'message': f'تم العثور على {len(results)} نتيجة'
    })
