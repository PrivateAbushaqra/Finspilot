"""
اختبار تسجيل الدخول والجلسة
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.conf import settings

User = get_user_model()

print("=" * 80)
print("اختبار تسجيل الدخول والجلسة")
print("=" * 80)

# إنشاء عميل اختبار
client = Client()

# محاولة تسجيل الدخول
print("\n1. محاولة تسجيل الدخول بالمستخدم 'super'...")
try:
    # التحقق من وجود المستخدم
    user = User.objects.filter(username='super').first()
    if user:
        print(f"   ✅ المستخدم موجود: {user.username}")
        print(f"   - نوع المستخدم: {getattr(user, 'user_type', 'غير محدد')}")
        print(f"   - نشط: {user.is_active}")
        print(f"   - موظف: {user.is_staff}")
        print(f"   - مدير: {user.is_superuser}")
    else:
        print("   ❌ المستخدم 'super' غير موجود")
        print("   📝 جاري البحث عن مستخدمين آخرين...")
        users = User.objects.all()[:5]
        for u in users:
            print(f"      - {u.username}")
        
    # محاولة تسجيل الدخول
    response = client.post('/ar/auth/login/', {
        'username': 'super',
        'password': 'password'
    }, follow=True)
    
    if response.status_code == 200:
        # التحقق من الجلسة
        if client.session.get('_auth_user_id'):
            print(f"\n   ✅ تم تسجيل الدخول بنجاح!")
            print(f"   - معرف المستخدم في الجلسة: {client.session.get('_auth_user_id')}")
            print(f"   - مفتاح الجلسة موجود: {'sessionid' in client.cookies or 'finspilot_sessionid' in client.cookies}")
            
            # فحص كوكيز الجلسة
            session_cookie = client.cookies.get('finspilot_sessionid') or client.cookies.get('sessionid')
            if session_cookie:
                print(f"   - كوكيز الجلسة:")
                print(f"     * القيمة: {session_cookie.value[:20]}...")
                print(f"     * المجال: {session_cookie.get('domain', 'None')}")
                print(f"     * المسار: {session_cookie.get('path', '/')}")
                print(f"     * SameSite: {session_cookie.get('samesite', 'غير محدد')}")
                print(f"     * Secure: {session_cookie.get('secure', False)}")
                print(f"     * HttpOnly: {session_cookie.get('httponly', True)}")
                print(f"     * Max-Age: {session_cookie.get('max-age', 'غير محدد')}")
            
            # محاولة الوصول لصفحة محمية
            print(f"\n2. محاولة الوصول للصفحة الرئيسية...")
            response2 = client.get('/ar/')
            if response2.status_code == 200:
                print(f"   ✅ تم الوصول للصفحة الرئيسية بنجاح (لا حاجة لإعادة تسجيل الدخول)")
            else:
                print(f"   ❌ فشل الوصول للصفحة الرئيسية: {response2.status_code}")
            
            # محاكاة فتح تبويب جديد (استخدام نفس الكوكيز)
            print(f"\n3. محاكاة فتح تبويب جديد...")
            client2 = Client()
            # نسخ الكوكيز من العميل الأول
            for cookie_name, cookie_value in client.cookies.items():
                client2.cookies[cookie_name] = cookie_value
            
            response3 = client2.get('/ar/sales/')
            if response3.status_code == 200:
                print(f"   ✅ تم الوصول لصفحة المبيعات من التبويب الجديد بنجاح!")
                print(f"   ✅ الجلسة تعمل بشكل صحيح مع التبويبات الجديدة")
            elif response3.status_code == 302 and '/auth/login/' in response3.url:
                print(f"   ❌ تم إعادة التوجيه لصفحة تسجيل الدخول")
                print(f"   ❌ المشكلة لا تزال موجودة")
            else:
                print(f"   ⚠️  حالة غير متوقعة: {response3.status_code}")
        else:
            print(f"   ❌ فشل تسجيل الدخول (لم يتم إنشاء جلسة)")
            print(f"   - رسالة الخطأ: تحقق من بيانات الاعتماد")
    else:
        print(f"   ❌ فشل الطلب: {response.status_code}")
        
except Exception as e:
    print(f"   ❌ خطأ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("انتهى الاختبار")
print("=" * 80)
