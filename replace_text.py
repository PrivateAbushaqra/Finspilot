import re

with open('templates/sales/return_add.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'خطأ في جلب الفواتير:', 'Error fetching invoices:', content)
content = re.sub(r'خطأ في تحميل الفواتير:', 'Error loading invoices:', content)
content = re.sub(r'خطأ في الشبكة:', 'Network error:', content)
content = re.sub(r'خطأ في الاتصال مع الخادم', 'Error connecting to server', content)

with open('templates/sales/return_add.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('تم استبدال النصوص العربية بالإنجليزية')