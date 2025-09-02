import urllib.request
import urllib.error

def simple_translation_check():
    """اختبار بسيط للترجمة"""
    
    print("🔍 اختبار ترجمة Global Search")
    print("=" * 40)
    
    try:
        # محاولة الوصول للصفحة العربية
        url = "http://127.0.0.1:8000/ar/"
        
        req = urllib.request.Request(url)
        req.add_header('Accept-Language', 'ar')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8')
            
            print(f"📡 تم الوصول إلى: {url}")
            print(f"📊 حجم المحتوى: {len(content)} حرف")
            
            # البحث عن النصوص
            if "البحث العام" in content:
                print("✅ وجدت 'البحث العام' في الصفحة")
                
                # عد مرات الظهور
                count = content.count("البحث العام")
                print(f"📈 عدد مرات الظهور: {count}")
                
                return True
                
            elif "Global Search" in content:
                print("❌ وجدت 'Global Search' (لم يترجم)")
                
                # موقع النص
                pos = content.find("Global Search")
                start = max(0, pos - 50)
                end = min(len(content), pos + 100)
                context = content[start:end]
                
                print(f"📍 السياق: ...{context}...")
                
                return False
                
            else:
                print("⚠️ لم أجد أي من النصين")
                
                # البحث عن كلمة "search" عموماً
                if "search" in content.lower():
                    print("🔍 وجدت كلمة 'search' في الصفحة")
                else:
                    print("❓ لا توجد كلمة 'search' في الصفحة")
                    
                return False
                
    except urllib.error.URLError as e:
        print(f"❌ خطأ في الاتصال: {e}")
        print("💡 تأكد من تشغيل خادم Django")
        return False
        
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")
        return False

if __name__ == "__main__":
    print("بدء اختبار الترجمة...")
    
    result = simple_translation_check()
    
    print("\n" + "=" * 40)
    if result:
        print("🎉 النتيجة: الترجمة تعمل بشكل مثالي!")
        print("✅ Global Search مترجم إلى 'البحث العام'")
    else:
        print("⚠️ النتيجة: الترجمة تحتاج مراجعة")
    
    print("\nانتهى الاختبار.")
