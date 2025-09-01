import requests
import re
from bs4 import BeautifulSoup

def check_english_terms():
    try:
        print("🔍 Checking English terms...")
        session = requests.Session()
        
        # الحصول على صفحة تسجيل الدخول
        login_response = session.get('http://127.0.0.1:8000/ar/auth/login/')
        if login_response.status_code != 200:
            print(f"❌ Error: {login_response.status_code}")
            return
            
        soup = BeautifulSoup(login_response.content, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
        
        # تسجيل الدخول
        login_data = {
            'username': 'super',
            'password': 'super', 
            'csrfmiddlewaretoken': csrf_token
        }
        
        dashboard_response = session.post('http://127.0.0.1:8000/ar/auth/login/', data=login_data)
        
        if dashboard_response.status_code == 200:
            print("✅ Login successful")
            soup = BeautifulSoup(dashboard_response.content, 'html.parser')
            text = soup.get_text()
            
            # البحث عن الكلمات الإنجليزية
            english_words = re.findall(r'\b[A-Za-z]+\b', text)
            
            # تصفية الكلمات
            excluded = {'FinsPilot', 'Super', 'Administrator', 'CSRF', 'HTML', 'CSS', 'JS', 'UTF', 'HTTP'}
            filtered_words = [word for word in english_words if word not in excluded and len(word) > 1]
            
            unique_words = list(set(filtered_words))
            
            print(f"📊 English terms found: {len(unique_words)}")
            print(f"📈 Total occurrences: {len(filtered_words)}")
            
            if unique_words:
                print("\n📝 Top terms:")
                word_counts = {word: filtered_words.count(word) for word in unique_words}
                sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
                
                for word, count in sorted_words[:25]:
                    print(f"  {word}: {count} times")
            else:
                print("🎉 No English terms found!")
            
        else:
            print("❌ Login failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_english_terms()
