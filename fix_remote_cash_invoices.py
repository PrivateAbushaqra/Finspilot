#!/usr/bin/env python
"""
سكريبت إصلاح الفواتير النقدية بدون صندوق - للخادم المباشر
يمكن تشغيله مباشرة على الخادم عبر SSH أو Django Shell
"""

import os
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.db import transaction
from sales.models import SalesInvoice
from cashboxes.models import Cashbox
from django.contrib.auth import get_user_model

User = get_user_model()

def fix_cash_invoices():
    """
    إصلاح الفواتير النقدية بدون صندوق
    """
    print("=" * 70)
    print("🔧 إصلاح الفواتير النقدية بدون صندوق")
    print("=" * 70)
    
    # الحصول على الفواتير النقدية بدون صندوق
    invoices = SalesInvoice.objects.filter(
        payment_type='cash',
        cashbox__isnull=True
    )
    
    count = invoices.count()
    
    if count == 0:
        print("\n✅ جميع الفواتير النقدية محددة بصندوق!")
        print("لا يوجد شيء للإصلاح.")
        return
    
    # حساب المبلغ الإجمالي
    total_amount = sum(invoice.total_amount for invoice in invoices)
    
    print(f"\n⚠️  تم العثور على {count} فاتورة نقدية بدون صندوق")
    print(f"💰 المبلغ الإجمالي: {total_amount:.3f} دينار")
    
    # السؤال عن التأكيد
    print("\n" + "=" * 70)
    print("سيتم:")
    print("1. إنشاء صندوق نقدي باسم 'مبيعات نقدية سابقة'")
    print(f"2. ربط {count} فاتورة بهذا الصندوق")
    print(f"3. تحديث رصيد الصندوق بـ {total_amount:.3f} دينار")
    print("=" * 70)
    
    confirm = input("\n⚠️  هل تريد المتابعة؟ (نعم/لا): ").strip().lower()
    
    if confirm not in ['نعم', 'yes', 'y']:
        print("\n❌ تم الإلغاء")
        return
    
    # تنفيذ الإصلاح
    try:
        with transaction.atomic():
            # الحصول على أول مستخدم كمسؤول افتراضي
            default_user = User.objects.filter(is_active=True).first()
            
            if not default_user:
                print("\n❌ خطأ: لا يوجد مستخدمين نشطين في النظام")
                return
            
            # البحث عن الصندوق أو إنشاءه
            cashbox, created = Cashbox.objects.get_or_create(
                name='مبيعات نقدية سابقة',
                defaults={
                    'balance': 0,  # سيتم تحديثه لاحقاً
                    'currency': 'JOD',
                    'responsible_user': default_user,
                    'is_active': True,
                    'description': 'صندوق تاريخي للفواتير النقدية السابقة التي لم يتم تحديد صندوق لها'
                }
            )
            
            if created:
                print(f"\n📦 تم إنشاء الصندوق: {cashbox.name}")
            else:
                print(f"\n📦 تم العثور على الصندوق: {cashbox.name}")
            
            # تحديث الفواتير
            updated = invoices.update(cashbox=cashbox)
            print(f"🔄 تم تحديث {updated} فاتورة")
            
            # تحديث رصيد الصندوق
            if created:
                cashbox.balance = total_amount
            else:
                cashbox.balance += total_amount
            cashbox.save()
            
            print(f"💰 تم تحديث رصيد الصندوق: {cashbox.balance:.3f} دينار")
            
            print("\n" + "=" * 70)
            print("✅ تم الإصلاح بنجاح!")
            print("=" * 70)
            print(f"📊 النتيجة:")
            print(f"   • الصندوق: {cashbox.name}")
            print(f"   • عدد الفواتير: {updated}")
            print(f"   • المبلغ الإجمالي: {total_amount:.3f} دينار")
            print(f"   • الرصيد الحالي للصندوق: {cashbox.balance:.3f} دينار")
            print("=" * 70)
            
    except Exception as e:
        print(f"\n❌ خطأ أثناء الإصلاح: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    fix_cash_invoices()
