#!/usr/bin/env python
"""
سكريبت تطبيق إصلاح الصندوق على sales/signals.py
يمكن تشغيله مباشرة على الخادم المباشر
"""

import os
import sys

def apply_fix():
    """
    تطبيق الإصلاح على ملف sales/signals.py
    """
    print("=" * 70)
    print("🔧 تطبيق إصلاح حفظ الصندوق في الفواتير النقدية")
    print("=" * 70)
    
    file_path = 'sales/signals.py'
    
    # التحقق من وجود الملف
    if not os.path.exists(file_path):
        print(f"\n❌ خطأ: الملف {file_path} غير موجود")
        print("تأكد من أنك في مجلد المشروع الصحيح")
        return False
    
    # قراءة محتوى الملف
    print(f"\n📖 قراءة الملف: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # التحقق من أن الملف لم يتم تعديله مسبقاً
    if 'استخدام الصندوق المحدد في الفاتورة أولاً' in content:
        print("\n✅ الإصلاح مُطبّق مسبقاً! لا حاجة لتطبيقه مرة أخرى.")
        return True
    
    # الكود القديم
    old_code = '''        # التحقق من أن الفاتورة جديدة ونقدية
        if created and instance.payment_type == 'cash' and instance.total_amount > 0:
            # تحديد الصندوق المناسب
            cashbox = None
            
            # إذا كان المستخدم يستطيع الوصول لنقطة البيع، استخدم صندوقه الخاص
            if instance.created_by.has_perm('users.can_access_pos'):'''
    
    # الكود الجديد
    new_code = '''        # التحقق من أن الفاتورة جديدة ونقدية
        if created and instance.payment_type == 'cash' and instance.total_amount > 0:
            # 🔧 استخدام الصندوق المحدد في الفاتورة أولاً (إن وُجد)
            cashbox = instance.cashbox
            
            # إذا لم يكن هناك صندوق محدد، حدد واحد حسب المستخدم
            if not cashbox:
                # إذا كان المستخدم يستطيع الوصول لنقطة البيع، استخدم صندوقه الخاص
                if instance.created_by.has_perm('users.can_access_pos'):'''
    
    # البحث عن الكود القديم
    if old_code not in content:
        print("\n⚠️  تحذير: لم يتم العثور على الكود القديم المتوقع")
        print("قد يكون الملف مُعدّل بالفعل أو تم تحديثه")
        
        # محاولة بحث بديلة
        if 'cashbox = None' in content and 'تحديد الصندوق المناسب' in content:
            print("\n💡 تم العثور على الكود بصيغة مختلفة")
            print("يرجى تطبيق الإصلاح يدوياً باستخدام دليل CASHBOX_SAVE_FIX.md")
        
        return False
    
    print("\n✅ تم العثور على الكود القديم")
    
    # السؤال عن التأكيد
    print("\n" + "=" * 70)
    print("سيتم تعديل الملف:")
    print(f"  📄 {file_path}")
    print("\nالتعديل:")
    print("  ✅ إضافة: cashbox = instance.cashbox")
    print("  ✅ إضافة: if not cashbox:")
    print("  ✅ إزالة: cashbox = None")
    print("=" * 70)
    
    confirm = input("\n⚠️  هل تريد المتابعة؟ (نعم/لا): ").strip().lower()
    
    if confirm not in ['نعم', 'yes', 'y']:
        print("\n❌ تم الإلغاء")
        return False
    
    # إنشاء نسخة احتياطية
    backup_path = file_path + '.backup'
    print(f"\n💾 إنشاء نسخة احتياطية: {backup_path}")
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # تطبيق التعديل
    print("\n🔄 تطبيق التعديل...")
    new_content = content.replace(old_code, new_code)
    
    # حفظ الملف المُعدّل
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("\n✅ تم تطبيق الإصلاح بنجاح!")
    print("\n" + "=" * 70)
    print("📋 الخطوات التالية:")
    print("=" * 70)
    print("1. ✅ أعد تشغيل الخادم:")
    print("   sudo systemctl restart gunicorn")
    print("   # أو")
    print("   sudo systemctl restart finspilot")
    print("")
    print("2. ✅ اختبر الإصلاح:")
    print("   - أنشئ فاتورة مبيعات نقدية")
    print("   - اختر صندوق محدد")
    print("   - تحقق من حفظ الصندوق في قائمة الفواتير")
    print("")
    print("3. ✅ (اختياري) أصلح الفواتير القديمة:")
    print("   python fix_remote_cash_invoices.py")
    print("=" * 70)
    
    return True

if __name__ == '__main__':
    try:
        success = apply_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ خطأ غير متوقع: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
