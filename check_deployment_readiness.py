#!/usr/bin/env python
"""
فحص جاهزية المشروع للنشر على Render.com
"""

import os
import sys
from pathlib import Path

def check_deployment_readiness():
    """فحص جاهزية النشر"""
    
    print("🔍 فحص جاهزية المشروع للنشر على Render.com")
    print("=" * 60)
    
    issues = []
    warnings = []
    
    # 1. فحص الملفات المطلوبة
    print("\n1️⃣ فحص الملفات المطلوبة:")
    
    required_files = {
        'requirements.txt': 'ملف المكتبات المطلوبة',
        'Procfile': 'ملف تشغيل التطبيق',
        'runtime.txt': 'ملف إصدار Python',
        '.env.example': 'ملف متغيرات البيئة (مثال)',
        'manage.py': 'ملف إدارة Django'
    }
    
    for file_name, description in required_files.items():
        if os.path.exists(file_name):
            print(f"   ✅ {file_name} - {description}")
        else:
            print(f"   ❌ {file_name} - مفقود!")
            issues.append(f"ملف {file_name} مفقود")
    
    # 2. فحص محتوى requirements.txt
    print("\n2️⃣ فحص محتوى requirements.txt:")
    
    if os.path.exists('requirements.txt'):
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
        
        required_packages = {
            'Django': 'إطار العمل الأساسي',
            'gunicorn': 'خادم WSGI للإنتاج',
            'psycopg2-binary': 'مشغل PostgreSQL',
            'whitenoise': 'خدمة الملفات الثابتة',
            'dj-database-url': 'إعداد قاعدة البيانات'
        }
        
        for package, description in required_packages.items():
            if package.lower() in requirements.lower():
                print(f"   ✅ {package} - {description}")
            else:
                print(f"   ❌ {package} - مفقود!")
                issues.append(f"مكتبة {package} مفقودة من requirements.txt")
    else:
        issues.append("ملف requirements.txt مفقود")
    
    # 3. فحص محتوى Procfile
    print("\n3️⃣ فحص محتوى Procfile:")
    
    if os.path.exists('Procfile'):
        with open('Procfile', 'r') as f:
            procfile_content = f.read().strip()
        
        expected_content = "web: gunicorn finspilot.wsgi:application"
        if procfile_content == expected_content:
            print(f"   ✅ محتوى صحيح: {procfile_content}")
        else:
            print(f"   ⚠️ محتوى غير متوقع: {procfile_content}")
            print(f"   📝 المتوقع: {expected_content}")
            warnings.append("محتوى Procfile قد يحتاج مراجعة")
    
    # 4. فحص إعدادات Django
    print("\n4️⃣ فحص إعدادات Django:")
    
    settings_path = Path('finspilot/settings.py')
    if settings_path.exists():
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings_content = f.read()
        
        checks = {
            'dj_database_url': 'إعداد قاعدة البيانات للإنتاج',
            'whitenoise': 'إعداد الملفات الثابتة',
            'RENDER': 'إعدادات خاصة بـ Render',
            'ALLOWED_HOSTS': 'إعداد المضيفين المسموحين'
        }
        
        for check, description in checks.items():
            if check in settings_content:
                print(f"   ✅ {check} - {description}")
            else:
                print(f"   ❌ {check} - غير موجود!")
                issues.append(f"إعداد {check} مفقود في settings.py")
    else:
        issues.append("ملف finspilot/settings.py غير موجود")
    
    # 5. فحص structure المشروع
    print("\n5️⃣ فحص هيكل المشروع:")
    
    required_dirs = {
        'finspilot': 'مجلد إعدادات Django',
        'static': 'مجلد الملفات الثابتة',
        'templates': 'مجلد القوالب',
        'core': 'التطبيق الأساسي',
        'users': 'تطبيق المستخدمين'
    }
    
    for dir_name, description in required_dirs.items():
        if os.path.isdir(dir_name):
            print(f"   ✅ {dir_name}/ - {description}")
        else:
            print(f"   ⚠️ {dir_name}/ - غير موجود!")
            warnings.append(f"مجلد {dir_name} غير موجود")
    
    # 6. فحص ملفات الأمان
    print("\n6️⃣ فحص ملفات الأمان:")
    
    security_files = ['.env', '.env.local', 'db.sqlite3']
    gitignore_exists = os.path.exists('.gitignore')
    
    if gitignore_exists:
        with open('.gitignore', 'r') as f:
            gitignore_content = f.read()
        
        secure_files_ignored = all(
            file_name in gitignore_content 
            for file_name in security_files
        )
        
        if secure_files_ignored:
            print("   ✅ الملفات الحساسة مُستبعدة من Git")
        else:
            print("   ⚠️ بعض الملفات الحساسة قد تكون غير مُستبعدة")
            warnings.append("تأكد من استبعاد الملفات الحساسة في .gitignore")
    else:
        print("   ⚠️ ملف .gitignore غير موجود")
        warnings.append("أنشئ ملف .gitignore لحماية الملفات الحساسة")
    
    # 7. النتيجة النهائية
    print("\n" + "=" * 60)
    print("📊 نتيجة الفحص:")
    
    if not issues and not warnings:
        print("🎉 المشروع جاهز للنشر على Render.com!")
        print("\n🚀 الخطوات التالية:")
        print("   1. ارفع الكود إلى GitHub")
        print("   2. أنشئ قاعدة بيانات PostgreSQL في Render")
        print("   3. أنشئ Web Service في Render")
        print("   4. اربط Repository")
        print("   5. أعد إعداد متغيرات البيئة")
        print("   6. انشر التطبيق!")
        
    elif issues and not warnings:
        print("❌ يوجد مشاكل يجب حلها قبل النشر:")
        for issue in issues:
            print(f"   • {issue}")
            
    elif not issues and warnings:
        print("⚠️ المشروع جاهز مع تحذيرات:")
        for warning in warnings:
            print(f"   • {warning}")
        print("\n✅ يمكن النشر، لكن يُنصح بمراجعة التحذيرات")
        
    else:
        print("⚠️ يوجد مشاكل وتحذيرات:")
        print("\n❌ المشاكل:")
        for issue in issues:
            print(f"   • {issue}")
        print("\n⚠️ التحذيرات:")
        for warning in warnings:
            print(f"   • {warning}")
    
    print("\n📚 للمساعدة:")
    print("   راجع ملف RENDER_DEPLOYMENT_GUIDE.md")
    print("   راجع ملف RENDER_TROUBLESHOOTING.md")
    
    return len(issues) == 0

if __name__ == "__main__":
    try:
        ready = check_deployment_readiness()
        if ready:
            print("\n✅ جاهز للنشر!")
            sys.exit(0)
        else:
            print("\n❌ غير جاهز للنشر")
            sys.exit(1)
    except Exception as e:
        print(f"❌ خطأ في فحص الجاهزية: {e}")
        sys.exit(1)
