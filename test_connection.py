import requests
import time

print("🔍 اختبار الاتصال بالخادم...")

try:
    # انتظار قصير
    time.sleep(2)
    
    # اختبار بسيط للاتصال
    response = requests.get('http://127.0.0.1:8000/', timeout=5)
    print(f"✅ الخادم يعمل! الاستجابة: {response.status_code}")
    
    # اختبار الصفحة العربية
    ar_response = requests.get('http://127.0.0.1:8000/ar/', timeout=5)
    print(f"✅ الصفحة العربية تعمل! الاستجابة: {ar_response.status_code}")
    
    # عد الكلمات الإنجليزية بشكل مبسط
    import re
    text = ar_response.text
    english_words = re.findall(r'\b[A-Za-z]+\b', text)
    
    # تصفية بسيطة
    filtered = [w for w in english_words if len(w) > 2 and w not in ['FinsPilot', 'Super', 'Administrator']]
    unique_words = list(set(filtered))
    
    print(f"📊 كلمات إنجليزية موجودة: {len(unique_words)}")
    print(f"📈 إجمالي التكرارات: {len(filtered)}")
    
    if len(unique_words) <= 20:
        print("🎉 تحسن ممتاز! قريب من الإكمال")
    
    # عرض أهم الكلمات
    if unique_words:
        from collections import Counter
        word_counts = Counter(filtered)
        top_words = word_counts.most_common(10)
        print("\n📝 أهم الكلمات المتبقية:")
        for word, count in top_words:
            print(f"   {word}: {count} مرة")
    
except requests.exceptions.ConnectionError:
    print("❌ لا يمكن الاتصال بالخادم. تأكد من تشغيل: python manage.py runserver")
except Exception as e:
    print(f"❌ خطأ: {e}")
