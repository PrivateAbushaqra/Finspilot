#!/usr/bin/env python
"""
سكريبت تطبيق إصلاح أولوية الصندوق في sales/views.py
"""

import os
import sys

def apply_views_fix():
    """
    تطبيق الإصلاح على ملف sales/views.py
    """
    print("=" * 70)
    print("🔧 إصلاح أولوية اختيار الصندوق في sales/views.py")
    print("=" * 70)
    
    file_path = 'sales/views.py'
    
    # التحقق من وجود الملف
    if not os.path.exists(file_path):
        print(f"\n❌ خطأ: الملف {file_path} غير موجود")
        return False
    
    # قراءة محتوى الملف
    print(f"\n📖 قراءة الملف: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # التحقق من أن الملف لم يتم تعديله مسبقاً
    if 'إعطاء الأولوية للصندوق المُختار من المستخدم' in content:
        print("\n✅ الإصلاح مُطبّق مسبقاً! لا حاجة لتطبيقه مرة أخرى.")
        return True
    
    # الكود القديم
    old_code = '''                        # الحصول على الصندوق فقط للدفع النقدي (الشيكات تُعالج من خلال سند القبض)
                        cashbox = None
                        if payment_type == 'cash':
                            # إذا كان المستخدم يمكنه الوصول لنقطة البيع، استخدم صندوقه الخاص تلقائياً
                            if user.has_perm('users.can_access_pos'):
                                try:
                                    from cashboxes.models import Cashbox
                                    cashbox = Cashbox.objects.filter(responsible_user=user).first()
                                    if not cashbox:
                                        # إذا لم يكن له صندوق، سيتم إنشاؤه تلقائياً في signals.py
                                        pass
                                except ImportError:
                                    pass
                            elif cashbox_id:
                                # للمستخدمين العاديين، استخدم الصندوق المحدد
                                try:
                                    from cashboxes.models import Cashbox
                                    cashbox = Cashbox.objects.get(id=cashbox_id, is_active=True)
                                except (ImportError, Cashbox.DoesNotExist):
                                    # إذا لم يتم العثور على الصندوق، نبلغ عن خطأ
                                    messages.error(request, _('الصندوق النقدي المحدد غير موجود أو غير نشط'))
                                    context = get_invoice_create_context(request, form_data)
                                    return render(request, 'sales/invoice_add.html', context)'''
    
    # الكود الجديد
    new_code = '''                        # الحصول على الصندوق فقط للدفع النقدي (الشيكات تُعالج من خلال سند القبض)
                        cashbox = None
                        if payment_type == 'cash':
                            # 🔧 إعطاء الأولوية للصندوق المُختار من المستخدم
                            if cashbox_id:
                                try:
                                    from cashboxes.models import Cashbox
                                    cashbox = Cashbox.objects.get(id=cashbox_id, is_active=True)
                                except (ImportError, Cashbox.DoesNotExist):
                                    messages.error(request, _('الصندوق النقدي المحدد غير موجود أو غير نشط'))
                                    context = get_invoice_create_context(request, form_data)
                                    return render(request, 'sales/invoice_add.html', context)
                            # إذا لم يتم اختيار صندوق، استخدم صندوق المستخدم التلقائي (POS)
                            elif user.has_perm('users.can_access_pos'):
                                try:
                                    from cashboxes.models import Cashbox
                                    cashbox = Cashbox.objects.filter(responsible_user=user).first()
                                    if not cashbox:
                                        # إذا لم يكن له صندوق، سيتم إنشاؤه تلقائياً في signals.py
                                        pass
                                except ImportError:
                                    pass'''
    
    # البحث عن الكود القديم
    if old_code not in content:
        print("\n⚠️  تحذير: لم يتم العثور على الكود القديم المتوقع")
        print("قد يكون الملف مُعدّل بالفعل أو تم تحديثه")
        return False
    
    print("\n✅ تم العثور على الكود القديم")
    
    # السؤال عن التأكيد
    print("\n" + "=" * 70)
    print("سيتم تعديل الملف:")
    print(f"  📄 {file_path}")
    print("\nالتعديل:")
    print("  ✅ تغيير الأولوية: الصندوق المُختار أولاً")
    print("  ✅ ثم صندوق المستخدم التلقائي (POS)")
    print("=" * 70)
    
    confirm = input("\n⚠️  هل تريد المتابعة؟ (نعم/لا): ").strip().lower()
    
    if confirm not in ['نعم', 'yes', 'y']:
        print("\n❌ تم الإلغاء")
        return False
    
    # إنشاء نسخة احتياطية
    backup_path = file_path + '.backup_views'
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
    print("")
    print("2. ✅ اختبر الإصلاح:")
    print("   - أنشئ فاتورة مبيعات نقدية")
    print("   - اختر صندوق محدد")
    print("   - تحقق من حفظ الصندوق الصحيح")
    print("=" * 70)
    
    return True

if __name__ == '__main__':
    try:
        success = apply_views_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ خطأ غير متوقع: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
