from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from sales.models import SalesInvoice, SalesReturn
from purchases.models import PurchaseInvoice, PurchaseReturn
from inventory.models import InventoryMovement
from banks.models import BankTransfer
from cashboxes.models import CashboxTransfer
from receipts.models import Receipt
from revenues_expenses.models import RevenueExpenseEntry
from products.models import Product, ProductCategory
from customers.models import Customer
from accounts.models import Account
from auditlog.models import LogEntry

User = get_user_model()


class Command(BaseCommand):
    help = 'تنظيف البيانات التجريبية والاحتفاظ بالبيانات الأساسية فقط'

    def handle(self, *args, **options):
        self.stdout.write('بدء عملية تنظيف البيانات التجريبية...')
        
        with transaction.atomic():
            # حذف البيانات التجريبية (الاحتفاظ بالبيانات الأساسية)
            self.clean_test_data()
            
            # إعادة تعيين كلمات مرور المستخدمين للقيم الصحيحة
            self.reset_user_passwords()
            
            # تنظيف سجلات النشاط القديمة (الاحتفاظ بآخر 100 سجل فقط)
            self.clean_audit_logs()
        
        self.stdout.write(
            self.style.SUCCESS('تم تنظيف البيانات التجريبية بنجاح')
        )

    def clean_test_data(self):
        """حذف البيانات التجريبية"""
        
        # حذف الفواتير التجريبية (أي فاتورة تحتوي على "TEST" في الملاحظات)
        test_sales = SalesInvoice.objects.filter(notes__icontains='TEST')
        deleted_count = test_sales.count()
        test_sales.delete()
        if deleted_count > 0:
            self.stdout.write(f'تم حذف {deleted_count} فاتورة مبيعات تجريبية')
        
        test_purchases = PurchaseInvoice.objects.filter(notes__icontains='TEST')
        deleted_count = test_purchases.count()
        test_purchases.delete()
        if deleted_count > 0:
            self.stdout.write(f'تم حذف {deleted_count} فاتورة مشتريات تجريبية')
        
        # حذف المردودات التجريبية
        test_sales_returns = SalesReturn.objects.filter(notes__icontains='TEST')
        deleted_count = test_sales_returns.count()
        test_sales_returns.delete()
        if deleted_count > 0:
            self.stdout.write(f'تم حذف {deleted_count} مردود مبيعات تجريبي')
        
        test_purchase_returns = PurchaseReturn.objects.filter(notes__icontains='TEST')
        deleted_count = test_purchase_returns.count()
        test_purchase_returns.delete()
        if deleted_count > 0:
            self.stdout.write(f'تم حذف {deleted_count} مردود مشتريات تجريبي')
        
        # حذف العملاء التجريبين
        test_customers = Customer.objects.filter(name__icontains='TEST')
        deleted_count = test_customers.count()
        test_customers.delete()
        if deleted_count > 0:
            self.stdout.write(f'تم حذف {deleted_count} عميل تجريبي')
        
        # حذف المنتجات التجريبية
        test_products = Product.objects.filter(name__icontains='TEST')
        deleted_count = test_products.count()
        test_products.delete()
        if deleted_count > 0:
            self.stdout.write(f'تم حذف {deleted_count} منتج تجريبي')
        
        # حذف حركات المخزون التجريبية
        test_movements = InventoryMovement.objects.filter(notes__icontains='TEST')
        deleted_count = test_movements.count()
        test_movements.delete()
        if deleted_count > 0:
            self.stdout.write(f'تم حذف {deleted_count} حركة مخزون تجريبية')

    def reset_user_passwords(self):
        """إعادة تعيين كلمات مرور المستخدمين للقيم الصحيحة"""
        
        # Super Admin
        try:
            super_user = User.objects.get(username='super')
            super_user.set_password('password')
            super_user.save()
            self.stdout.write('تم تحديث كلمة مرور Super Admin')
        except User.DoesNotExist:
            pass
        
        # Admin Manager
        try:
            admin_user = User.objects.get(username='admin')
            admin_user.set_password('adminadmin123')
            admin_user.save()
            self.stdout.write('تم تحديث كلمة مرور Admin')
        except User.DoesNotExist:
            pass
        
        # Regular User
        try:
            regular_user = User.objects.get(username='user')
            regular_user.set_password('useruser123')
            regular_user.save()
            self.stdout.write('تم تحديث كلمة مرور User')
        except User.DoesNotExist:
            pass
        
        # POS User
        try:
            pos_user = User.objects.get(username='posuser')
            pos_user.set_password('posuser123')
            pos_user.save()
            self.stdout.write('تم تحديث كلمة مرور POS User')
        except User.DoesNotExist:
            pass

    def clean_audit_logs(self):
        """تنظيف سجلات النشاط القديمة والاحتفاظ بآخر 100 سجل فقط"""
        try:
            # احتفظ بآخر 100 سجل فقط
            logs_to_keep = LogEntry.objects.order_by('-timestamp')[:100]
            keep_ids = list(logs_to_keep.values_list('id', flat=True))
            
            old_logs = LogEntry.objects.exclude(id__in=keep_ids)
            deleted_count = old_logs.count()
            old_logs.delete()
            
            if deleted_count > 0:
                self.stdout.write(f'تم حذف {deleted_count} سجل نشاط قديم')
        except Exception as e:
            self.stdout.write(f'تحذير: مشكلة في تنظيف سجلات النشاط: {e}')
