import requests
import re
from bs4 import BeautifulSoup
import time

def test_translations():
    """فحص سريع للترجمات الجديدة"""
    print("🔍 فحص الترجمات الجديدة...")
    
    try:
        # انتظار لتأكد من تشغيل الخادم
        time.sleep(3)
        
        session = requests.Session()
        
        # الوصول لصفحة تسجيل الدخول
        login_url = 'http://127.0.0.1:8000/ar/auth/login/'
        response = session.get(login_url, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ خطأ في الاتصال: {response.status_code}")
            return
            
        print("✅ تم الاتصال بالخادم")
        
        # استخراج CSRF token
        soup = BeautifulSoup(response.content, 'html.parser')
        csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if not csrf_input:
            print("❌ لم يتم العثور على CSRF token")
            return
            
        csrf_token = csrf_input['value']
        
        # تسجيل الدخول
        login_data = {
            'username': 'super',
            'password': 'super',
            'csrfmiddlewaretoken': csrf_token
        }
        
        dashboard_response = session.post(login_url, data=login_data, timeout=10)
        
        if dashboard_response.status_code == 200:
            print("✅ تم تسجيل الدخول بنجاح")
            
            # تحليل المحتوى
            soup = BeautifulSoup(dashboard_response.content, 'html.parser')
            page_text = soup.get_text()
            
            # البحث عن الكلمات الإنجليزية
            english_pattern = r'\b[A-Za-z]+\b'
            english_words = re.findall(english_pattern, page_text)
            
            # تصفية الكلمات المستثناة
            excluded_words = {
                'FinsPilot', 'Super', 'Administrator', 'CSRF', 'HTML', 'CSS', 'JS', 
                'UTF', 'HTTP', 'Django', 'Python', 'GET', 'POST', 'API', 'URL',
                'ID', 'UUID', 'JSON', 'XML', 'SQL', 'DB', 'www', 'com', 'org',
                'net', 'io', 'ai', 'vs', 'px', 'em', 'rem', 'rgb', 'rgba'
            }
            
            filtered_words = [
                word for word in english_words 
                if word not in excluded_words and len(word) > 1
            ]
            
            unique_words = list(set(filtered_words))
            
            print(f"📊 عدد المصطلحات الإنجليزية المتبقية: {len(unique_words)}")
            print(f"📈 إجمالي التكرارات: {len(filtered_words)}")
            
            if len(unique_words) > 0:
                print(f"\n📝 أهم المصطلحات المتبقية:")
                word_counts = {word: filtered_words.count(word) for word in unique_words}
                sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
                
                for i, (word, count) in enumerate(sorted_words[:15]):
                    print(f"   {i+1:2d}. {word:<15} : {count} مرة")
                    
                if len(unique_words) <= 10:
                    print("🎯 قريب جداً من الإكمال!")
                elif len(unique_words) <= 25:
                    print("✨ تقدم ممتاز في الترجمة!")
                else:
                    print("📈 تحسن ملحوظ، يحتاج المزيد من العمل")
            else:
                print("🎉 ممتاز! لا توجد مصطلحات إنجليزية متبقية!")
                
        else:
            print(f"❌ فشل في تسجيل الدخول: {dashboard_response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ خطأ في الشبكة: {e}")
    except Exception as e:
        print(f"❌ خطأ عام: {e}")

if __name__ == "__main__":
    test_translations()
