#!/usr/bin/env python
"""
Check sales returns and credit notes
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from sales.models import SalesReturn, SalesCreditNote

print("=" * 70)
print("فحص مردودات المبيعات والإشعارات الدائنة")
print("=" * 70)

# Check Sales Returns
print("\n📦 مردودات المبيعات:")
returns = SalesReturn.objects.all().order_by('-created_at')[:5]

if returns.count() == 0:
    print("  ❌ لا توجد مردودات مبيعات")
else:
    print(f"  وجدت {returns.count()} مردود:\n")
    for ret in returns:
        print(f"  📄 {ret.return_number}")
        print(f"     Posted: {ret.is_posted_to_tax}")
        print(f"     UUID: {ret.jofotara_uuid or 'غير موجود'}")
        print(f"     QR Code: {'✅ موجود' if ret.jofotara_qr_code else '❌ غير موجود'}")
        print()

# Check Credit Notes
print("\n💳 إشعارات دائنة:")
notes = SalesCreditNote.objects.all().order_by('-created_at')[:5]

if notes.count() == 0:
    print("  ❌ لا توجد إشعارات دائنة")
else:
    print(f"  وجدت {notes.count()} إشعار:\n")
    for note in notes:
        print(f"  📄 {note.note_number}")
        print(f"     Posted: {note.is_posted_to_tax}")
        print(f"     UUID: {note.jofotara_uuid or 'غير موجود'}")
        print(f"     QR Code: {'✅ موجود' if note.jofotara_qr_code else '❌ غير موجود'}")
        print()

print("=" * 70)
