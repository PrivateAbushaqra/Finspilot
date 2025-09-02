import time
import requests
from bs4 import BeautifulSoup

def test_live_translation():
    """اختبار ترجمة Global Search في النسخة المعيشة"""
    
    print("🔍 اختبار ترجمة Global Search في النسخة المعيشة")
    print("=" * 55)
    
    # انتظار قليل للتأكد من تشغيل الخادم
    time.sleep(2)
    
    try:
        # طلب الصفحة العربية
        url = "http://127.0.0.1:8001/ar/"
        headers = {
            'Accept-Language': 'ar',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        print(f"📡 محاولة الوصول إلى: {url}")
        
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"📊 كود الاستجابة: {response.status_code}")
        
        if response.status_code == 200:
            # تحليل HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # البحث عن العنصر المحدد
            search_link = soup.find('a', href='/ar/search/')
            
            if search_link:
                link_text = search_link.get_text(strip=True)
                print(f"🔍 نص رابط البحث: '{link_text}'")
                
                # فحص الأيقونة والنص
                icon = search_link.find('i')
                if icon:
                    print(f"✅ وجدت أيقونة البحث: {icon.get('class', [])}")
                
                # التحقق من الترجمة
                if "البحث العام" in link_text:
                    print("🎉 ممتاز! Global Search مترجم إلى 'البحث العام'")
                    return True
                elif "Global Search" in link_text:
                    print("❌ المشكلة: النص لا يزال بالإنجليزية")
                    print(f"   النص الحالي: '{link_text}'")
                    return False
                else:
                    print(f"⚠️ نص غير متوقع: '{link_text}'")
                    
            else:
                print("❌ لم يتم العثور على رابط البحث في /ar/search/")
                
                # البحث في جميع الروابط
                all_links = soup.find_all('a')
                search_links = [link for link in all_links if 'search' in link.get('href', '').lower()]
                
                if search_links:
                    print(f"🔍 وجدت {len(search_links)} رابط بحث:")
                    for link in search_links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        print(f"   • {href}: '{text}'")
                        
            # فحص إضافي في محتوى الصفحة
            page_content = response.text
            if "البحث العام" in page_content:
                print("✅ 'البحث العام' موجود في محتوى الصفحة")
                return True
            elif "Global Search" in page_content:
                print("❌ 'Global Search' موجود في محتوى الصفحة (غير مترجم)")
                return False
                
        else:
            print(f"❌ خطأ HTTP: {response.status_code}")
            if response.status_code == 404:
                print("   الصفحة غير موجودة - تحقق من URL")
            elif response.status_code == 500:
                print("   خطأ في الخادم - تحقق من إعدادات Django")
                
    except requests.exceptions.ConnectionError:
        print("❌ فشل الاتصال بالخادم")
        print("   تأكد من أن Django يعمل على المنفذ 8001")
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")
    
    return False

if __name__ == "__main__":
    success = test_live_translation()
    
    print("\n" + "=" * 55)
    if success:
        print("🎉 النتيجة: الترجمة تعمل بشكل صحيح!")
    else:
        print("⚠️ النتيجة: الترجمة تحتاج إصلاح")
        print("💡 اقتراحات:")
        print("   1. تأكد من تجميع ملفات الترجمة")
        print("   2. أعد تشغيل خادم Django")
        print("   3. تحقق من إعدادات اللغة")
