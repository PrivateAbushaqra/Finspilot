#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
سكريبت لإصلاح الفواتير النقدية بدون صندوق محدد
"""
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesInvoice
from django.db.models import Sum
from decimal import Decimal

def main():
    print("=" * 70)
    print("🔧 إصلاح الفواتير النقدية بدون صندوق")
    print("=" * 70)
    
    # الحصول على الفواتير بدون صندوق
    cash_without_cashbox = SalesInvoice.objects.filter(
        payment_type='cash',
        cashbox__isnull=True
    )
    
    count = cash_without_cashbox.count()
    total_amount = cash_without_cashbox.aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0')
    
    if count == 0:
        print("\n✅ لا توجد فواتير نقدية بدون صندوق!")
        print("=" * 70)
        return
    
    print(f"\n⚠️  تم العثور على {count} فاتورة نقدية بدون صندوق")
    print(f"💰 المبلغ الإجمالي: {total_amount:.3f} دينار")
    print()
    
    # عرض الخيارات
    print("🎯 اختر الحل المناسب:")
    print()
    print("1. إنشاء صندوق 'مبيعات سابقة' وتعيينه للفواتير (موصى به)")
    print("2. تعيين صندوق موجود للفواتير")
    print("3. عرض التفاصيل فقط (بدون تعديل)")
    print("4. إلغاء")
    print()
    
    choice = input("اختيارك (1-4): ").strip()
    
    if choice == '1':
        create_historical_cashbox(cash_without_cashbox, total_amount)
    elif choice == '2':
        assign_existing_cashbox(cash_without_cashbox)
    elif choice == '3':
        show_details(cash_without_cashbox)
    else:
        print("\n❌ تم الإلغاء")
    
    print("=" * 70)

def create_historical_cashbox(invoices, total_amount):
    """إنشاء صندوق للمبيعات السابقة"""
    from cashboxes.models import Cashbox
    from django.contrib.auth import get_user_model
    
    print("\n📦 إنشاء صندوق 'مبيعات نقدية سابقة'...")
    
    # التحقق من وجود الصندوق
    cashbox, created = Cashbox.objects.get_or_create(
        name='مبيعات نقدية سابقة',
        defaults={
            'description': 'صندوق وهمي لتجميع المبيعات النقدية قبل تطبيق نظام الصناديق',
            'balance': total_amount,
            'currency': 'JOD',
            'is_active': True,
            'location': 'افتراضي'
        }
    )
    
    if created:
        print(f"✅ تم إنشاء الصندوق بنجاح")
        print(f"   الاسم: {cashbox.name}")
        print(f"   الرصيد: {cashbox.balance:.3f} دينار")
    else:
        print(f"ℹ️  الصندوق موجود مسبقاً")
        # تحديث الرصيد
        cashbox.balance = total_amount
        cashbox.save()
        print(f"   تم تحديث الرصيد إلى: {cashbox.balance:.3f} دينار")
    
    # تعيين الصندوق للفواتير
    print(f"\n🔄 تحديث {invoices.count()} فاتورة...")
    updated = invoices.update(cashbox=cashbox)
    
    print(f"✅ تم تحديث {updated} فاتورة بنجاح!")
    print()
    print("📊 النتيجة:")
    print(f"   • الصندوق: {cashbox.name}")
    print(f"   • عدد الفواتير: {updated}")
    print(f"   • المبلغ الإجمالي: {total_amount:.3f} دينار")

def assign_existing_cashbox(invoices):
    """تعيين صندوق موجود"""
    from cashboxes.models import Cashbox
    
    print("\n📦 الصناديق المتاحة:")
    print()
    
    cashboxes = Cashbox.objects.filter(is_active=True)
    
    if not cashboxes.exists():
        print("❌ لا توجد صناديق نشطة!")
        print("   يرجى إنشاء صندوق أولاً أو استخدام الخيار 1")
        return
    
    for i, cashbox in enumerate(cashboxes, 1):
        print(f"{i}. {cashbox.name}")
        print(f"   الرصيد الحالي: {cashbox.balance:.3f} دينار")
        print(f"   الموقع: {cashbox.location or 'غير محدد'}")
        print()
    
    try:
        choice = int(input(f"اختر الصندوق (1-{cashboxes.count()}): "))
        if choice < 1 or choice > cashboxes.count():
            raise ValueError
        
        selected_cashbox = list(cashboxes)[choice - 1]
        
        print(f"\n⚠️  هل أنت متأكد من تعيين '{selected_cashbox.name}'")
        print(f"   لـ {invoices.count()} فاتورة؟ (نعم/لا): ", end='')
        
        confirm = input().strip().lower()
        if confirm not in ['نعم', 'yes', 'y']:
            print("❌ تم الإلغاء")
            return
        
        # التحديث
        total_amount = invoices.aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
        updated = invoices.update(cashbox=selected_cashbox)
        
        # تحديث رصيد الصندوق
        selected_cashbox.balance += total_amount
        selected_cashbox.save()
        
        print(f"\n✅ تم التحديث بنجاح!")
        print(f"   • الصندوق: {selected_cashbox.name}")
        print(f"   • عدد الفواتير: {updated}")
        print(f"   • المبلغ المضاف: {total_amount:.3f} دينار")
        print(f"   • الرصيد الجديد: {selected_cashbox.balance:.3f} دينار")
        
    except (ValueError, IndexError):
        print("\n❌ اختيار غير صحيح!")

def show_details(invoices):
    """عرض التفاصيل فقط"""
    print("\n📋 تفاصيل الفواتير بدون صندوق:")
    print("-" * 70)
    
    for invoice in invoices.order_by('-date'):
        customer_name = invoice.customer.name if invoice.customer else 'نقدي'
        print(f"• {invoice.invoice_number:15} | {invoice.date} | "
              f"{invoice.total_amount:12.3f} د | {customer_name}")
    
    total = invoices.aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
    print("-" * 70)
    print(f"{'الإجمالي:':17} {total:29.3f} دينار")
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ تم الإلغاء بواسطة المستخدم")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
