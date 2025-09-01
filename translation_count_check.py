#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def check_translation_count():
    """فحص عدد الترجمات في الملف"""
    
    try:
        # قراءة ملف الترجمة
        with open('locale/ar/LC_MESSAGES/django.po', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # عد الترجمات
        import re
        
        # البحث عن msgid entries
        msgid_pattern = r'msgid\s+"([^"]+)"'
        msgids = re.findall(msgid_pattern, content)
        
        # تصفية msgids الفارغة
        valid_msgids = [msgid for msgid in msgids if msgid.strip() and msgid != ""]
        
        print(f"📊 إجمالي الترجمات في الملف: {len(valid_msgids)}")
        
        # إظهار عينة من الترجمات المضافة حديثاً
        recent_translations = [
            "Sale", "Purchase", "List", "Dashboard", "Admin", "Administrator",
            "Permission", "Permissions", "Groups", "Journal", "Revenues", 
            "Expense", "Expenses", "Profit", "Loss", "Stock", "Performance",
            "Date", "Monthly", "Pending", "Alert", "Alerts", "Number", "Type",
            "Available", "HR", "login", "logout", "help", "about", "contact"
        ]
        
        found_translations = []
        for term in recent_translations:
            if f'msgid "{term}"' in content:
                found_translations.append(term)
        
        print(f"✅ الترجمات المضافة مؤخراً: {len(found_translations)}/{len(recent_translations)}")
        
        if found_translations:
            print("📝 عينة من الترجمات المؤكدة:")
            for i, term in enumerate(found_translations[:10]):
                print(f"   {i+1}. {term}")
                
        # فحص الترجمات المتكررة
        from collections import Counter
        msgid_counts = Counter(valid_msgids)
        duplicates = {k: v for k, v in msgid_counts.items() if v > 1}
        
        if duplicates:
            print(f"⚠️  ترجمات متكررة: {len(duplicates)}")
            for term, count in list(duplicates.items())[:5]:
                print(f"   {term}: {count} مرات")
        else:
            print("✅ لا توجد ترجمات متكررة")
            
        return len(valid_msgids)
        
    except Exception as e:
        print(f"❌ خطأ في فحص الملف: {e}")
        return 0

if __name__ == "__main__":
    print("🔍 فحص ملف الترجمة...")
    count = check_translation_count()
    print(f"\n📈 النتيجة النهائية: {count} ترجمة في الملف")
