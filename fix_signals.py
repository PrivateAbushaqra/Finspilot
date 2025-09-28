#!/usr/bin/env python
# قراءة الملف
with open('sales/signals.py', 'r', encoding='utf-8') as f:
    content = f.read()

# البحث عن الدالة وتعديلها
old_text = '''    try:
        if created and instance.product.product_type == 'physical':
            from time import sleep
            sleep(0.5)  # انتظار لحفظ حركات المخزون
            
            from journal.services import JournalService
            cogs_entry = JournalService.create_cogs_entry(instance.invoice, instance.invoice.created_by)
            if cogs_entry:
                print(f"تم إنشاء قيد COGS {cogs_entry.entry_number} لفاتورة المبيعات {instance.invoice.invoice_number}")
            else:
                print(f"لم يتم إنشاء قيد COGS لفاتورة المبيعات {instance.invoice.invoice_number}")
    except Exception as e:
        print(f"خطأ في إنشاء قيد COGS لفاتورة المبيعات {instance.invoice.invoice_number}: {e}")
        pass'''

new_text = '''    try:
        if created and instance.product.product_type == 'physical':
            from time import sleep
            sleep(0.5)  # انتظار لحفظ حركات المخزون
            
            # التحقق من عدم وجود قيد COGS مسبقاً
            from journal.models import JournalEntry
            existing_cogs = JournalEntry.objects.filter(
                reference_type='sales_invoice_cogs',
                reference_id=instance.invoice.id
            ).exists()
            
            if not existing_cogs:
                from journal.services import JournalService
                cogs_entry = JournalService.create_cogs_entry(instance.invoice, instance.invoice.created_by)
                if cogs_entry:
                    print(f"تم إنشاء قيد COGS {cogs_entry.entry_number} لفاتورة المبيعات {instance.invoice.invoice_number}")
                else:
                    print(f"لم يتم إنشاء قيد COGS لفاتورة المبيعات {instance.invoice.invoice_number}")
    except Exception as e:
        print(f"خطأ في إنشاء قيد COGS لفاتورة المبيعات {instance.invoice.invoice_number}: {e}")
        pass'''

content = content.replace(old_text, new_text)

# كتابة الملف مرة أخرى
with open('sales/signals.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('تم تعديل الدالة لتتحقق من عدم وجود قيد COGS مسبقاً')