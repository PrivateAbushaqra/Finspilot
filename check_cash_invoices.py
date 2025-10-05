#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesInvoice
from django.db.models import Sum

# الحصول على جميع الفواتير النقدية
cash_invoices = SalesInvoice.objects.filter(payment_type='cash')
total_cash_invoices = cash_invoices.count()

# الفواتير النقدية بدون صندوق
cash_without_cashbox = cash_invoices.filter(cashbox__isnull=True)
count_without = cash_without_cashbox.count()

# الفواتير النقدية مع صندوق
cash_with_cashbox = cash_invoices.filter(cashbox__isnull=False)
count_with = cash_with_cashbox.count()

# حساب المبالغ
total_amount_all = cash_invoices.aggregate(total=Sum('total_amount'))['total'] or 0
amount_without_box = cash_without_cashbox.aggregate(total=Sum('total_amount'))['total'] or 0
amount_with_box = cash_with_cashbox.aggregate(total=Sum('total_amount'))['total'] or 0

print("=" * 70)
print("📊 تقرير الفواتير النقدية")
print("=" * 70)
print(f"\n🔢 إجمالي الفواتير النقدية: {total_cash_invoices}")
print(f"💰 إجمالي المبالغ النقدية: {total_amount_all:.3f} دينار")
print()
print(f"✅ فواتير نقدية مع صندوق محدد: {count_with}")
print(f"   💵 المبلغ: {amount_with_box:.3f} دينار")
print()
print(f"⚠️  فواتير نقدية بدون صندوق: {count_without}")
print(f"   💸 المبلغ: {amount_without_box:.3f} دينار")
print()
print("=" * 70)

# عرض تفاصيل الفواتير بدون صندوق
if count_without > 0:
    print("\n📋 تفاصيل الفواتير بدون صندوق (أول 10):")
    print("-" * 70)
    for invoice in cash_without_cashbox.order_by('-date')[:10]:
        customer_name = invoice.customer.name if invoice.customer else 'نقدي'
        print(f"   • {invoice.invoice_number} | {invoice.date} | {invoice.total_amount:.3f} د | {customer_name}")
    
    if count_without > 10:
        print(f"\n   ... و {count_without - 10} فواتير أخرى")

print("\n" + "=" * 70)

# التوصيات
if count_without > 0:
    print("\n💡 التوصية:")
    print(f"   يوجد {count_without} فاتورة نقدية بقيمة {amount_without_box:.3f} دينار")
    print("   بدون تحديد صندوق نقدي.")
    print()
    print("   🔧 الحلول المقترحة:")
    print("   1. تحديث الفواتير القديمة لتعيين صندوق افتراضي")
    print("   2. إنشاء صندوق 'مبيعات نقدية سابقة' ونقل المبالغ إليه")
    print("   3. عرض تحذير في التقارير للفواتير بدون صندوق")
    print()
else:
    print("\n✅ جميع الفواتير النقدية محددة بصندوق!")

print("=" * 70)
