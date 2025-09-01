#!/usr/bin/env python3
"""
فحص مركز للمصطلحات الإنجليزية الأكثر تكراراً في لوحة التحكم العربية
"""

import requests
import re
from collections import Counter
from bs4 import BeautifulSoup

def get_english_terms_focused():
    """فحص مركز للمصطلحات الأكثر تكراراً"""
    
    print("=" * 80)
    print("🎯 فحص مركز للمصطلحات الأكثر تكراراً في لوحة التحكم العربية")
    print("=" * 80)
    
    try:
        # الحصول على صفحة تسجيل الدخول
        login_url = 'http://127.0.0.1:8000/ar/accounts/login/'
        session = requests.Session()
        login_response = session.get(login_url)
        
        if login_response.status_code != 200:
            print(f"❌ خطأ في الوصول لصفحة تسجيل الدخول: {login_response.status_code}")
            return
            
        # استخراج CSRF token
        soup = BeautifulSoup(login_response.content, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        
        if not csrf_token:
            print("❌ لم يتم العثور على CSRF token")
            return
            
        csrf_value = csrf_token.get('value')
        print("✅ تم الحصول على CSRF token")
        
        # تسجيل الدخول
        login_data = {
            'username': 'super',
            'password': 'super123',
            'csrfmiddlewaretoken': csrf_value
        }
        
        login_submit = session.post(login_url, data=login_data)
        print(f"✅ استجابة تسجيل الدخول: {login_submit.status_code}")
        print(f"📍 الرابط النهائي: {login_submit.url}")
        
        # الوصول لصفحة لوحة التحكم العربية
        dashboard_url = 'http://127.0.0.1:8000/ar/'
        dashboard_response = session.get(dashboard_url)
        
        if dashboard_response.status_code != 200:
            print(f"❌ خطأ في الوصول للوحة التحكم: {dashboard_response.status_code}")
            return
            
        # تحليل المحتوى
        soup = BeautifulSoup(dashboard_response.content, 'html.parser')
        
        # استخراج النص المرئي فقط
        visible_text = soup.get_text()
        
        print(f"\n📊 معلومات الصفحة:")
        print(f"   📋 العنوان: {soup.title.string if soup.title else 'غير محدد'}")
        print(f"   📄 حجم المحتوى: {len(dashboard_response.content)} حرف")
        print(f"   👁️ حجم النص المرئي: {len(visible_text)} حرف")
        
        # البحث عن المصطلحات الإنجليزية الأكثر تكراراً (أعلى من 3 مرات)
        english_pattern = r'\b[A-Za-z]+\b'
        english_words = re.findall(english_pattern, visible_text)
        
        # حساب التكرارات
        word_counts = Counter(english_words)
        
        # فلترة المصطلحات عالية التكرار (أكثر من 3 مرات)
        high_frequency_terms = {word: count for word, count in word_counts.items() if count > 3}
        
        print(f"\n🔍 البحث المركز عن المصطلحات عالية التكرار...")
        print(f"\n📊 نتائج البحث:")
        print("-" * 60)
        
        if high_frequency_terms:
            print(f"⚠️ تم العثور على {len(high_frequency_terms)} مصطلحاً إنجليزياً عالي التكرار")
            total_high_freq_words = sum(high_frequency_terms.values())
            print(f"📈 إجمالي الكلمات عالية التكرار: {total_high_freq_words}")
            
            print(f"\n📝 المصطلحات عالية التكرار (أكثر من 3 مرات):")
            print("-" * 60)
            
            # ترتيب حسب التكرار
            sorted_terms = sorted(high_frequency_terms.items(), key=lambda x: x[1], reverse=True)
            
            for i, (term, count) in enumerate(sorted_terms, 1):
                print(f"{i:2d}. {term:<20} : {count} مرة")
                
            # اقتراحات للترجمة
            print(f"\n💡 اقتراحات الترجمة المطلوبة عاجلاً:")
            print("-" * 60)
            
            translation_suggestions = {
                'Sale': 'مبيعة',
                'Sales': 'المبيعات',
                'Purchase': 'مشترى',
                'List': 'قائمة',
                'To': 'إلى',
                'Return': 'إرجاع',
                'Invoice': 'فاتورة',
                'Report': 'تقرير',
                'On': 'في',
                'Create': 'إنشاء',
                'Cash': 'النقد',
                'State': 'الحالة',
                'Entries': 'القيود',
                'Balance': 'الرصيد'
            }
            
            for term, arabic in translation_suggestions.items():
                if term in high_frequency_terms:
                    count = high_frequency_terms[term]
                    print(f"   • {term} ({count}×) → {arabic}")
                    
        else:
            print("✅ لا توجد مصطلحات إنجليزية عالية التكرار!")
            
        # إحصائيات إضافية
        total_english_words = len(english_words)
        unique_english_terms = len(word_counts)
        
        print(f"\n📈 إحصائيات إضافية:")
        print("-" * 60)
        print(f"   📊 إجمالي الكلمات الإنجليزية: {total_english_words}")
        print(f"   🔤 المصطلحات الفريدة: {unique_english_terms}")
        print(f"   🎯 المصطلحات عالية التكرار: {len(high_frequency_terms)}")
        if total_english_words > 0:
            high_freq_percentage = (total_high_freq_words / total_english_words) * 100
            print(f"   📊 نسبة المصطلحات عالية التكرار: {high_freq_percentage:.1f}%")
        
    except Exception as e:
        print(f"❌ خطأ أثناء التحليل: {e}")
        
    print("\n" + "=" * 80)
    print("🔚 انتهى الفحص المركز")
    print("=" * 80)

if __name__ == "__main__":
    get_english_terms_focused()
