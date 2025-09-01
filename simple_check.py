import requests
import re

def check_arabic_page():
    try:
        response = requests.get('http://127.0.0.1:8000/ar/')
        content = response.text
        
        # البحث عن المصطلحات الإنجليزية الأساسية
        english_terms = ['Dashboard', 'Settings', 'Logout']
        
        found_terms = []
        for term in english_terms:
            if term in content:
                # عد عدد المرات
                count = len(re.findall(re.escape(term), content, re.IGNORECASE))
                found_terms.append(f"{term} ({count})")
        
        if found_terms:
            print(f"❌ وُجدت نصوص إنجليزية: {', '.join(found_terms)}")
            return False
        else:
            print("✅ لا توجد نصوص إنجليزية في النسخة العربية")
            return True
            
    except Exception as e:
        print(f"خطأ في الاتصال: {e}")
        return False

if __name__ == "__main__":
    check_arabic_page()
