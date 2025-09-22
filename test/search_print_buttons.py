import os
import re
from pathlib import Path

def find_print_buttons(project_root):
    results = []
    
    # امتدادات الملفات التي سنفحصها
    extensions = ['.html', '.py']
    
    for root, dirs, files in os.walk(project_root):
        # استثناء مجلدات غير مطلوبة
        dirs[:] = [d for d in dirs if d not in ['test', 'media', '__pycache__', 'migrations', 'staticfiles']]
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # البحث عن أزرار تحتوي على "طباعة" أو "Print" أو {% trans %}
                        buttons = re.findall(r'<button[^>]*>.*?(طباعة|Print|{%\s*trans\s+"طباعة"\s*%}|{%\s*trans\s+"Print"\s*%}).*?</button>', content, re.IGNORECASE | re.DOTALL)
                        links = re.findall(r'<a[^>]*>.*?(طباعة|Print|{%\s*trans\s+"طباعة"\s*%}|{%\s*trans\s+"Print"\s*%}).*?</a>', content, re.IGNORECASE | re.DOTALL)
                        
                        if buttons or links:
                            print(f"Found in {file_path}: buttons={len(buttons)}, links={len(links)}")
                            # العثور على الأسطر
                            lines = content.split('\n')
                            for i, line in enumerate(lines):
                                if 'طباعة' in line or 'Print' in line or '{% trans "طباعة" %}' in line or '{% trans "Print" %}' in line:
                                    # التحقق من السياق (الأسطر السابقة واللاحقة)
                                    context_start = max(0, i-2)
                                    context_end = min(len(lines), i+3)
                                    context = '\n'.join(lines[context_start:context_end])
                                    if '<button' in context or '<a' in context:
                                        if 'journal/entry_detail.html' in file_path:
                                            url = 'journal:entry_detail'
                                        else:
                                            url = extract_url(context, file_path)
                                        results.append({
                                            'file_path': file_path,
                                            'line': i + 1,
                                            'line_content': line.strip(),
                                            'url': url
                                        })
                except Exception as e:
                    print(f"خطأ في قراءة الملف {file_path}: {e}")
    
    return results

def extract_url(line, file_path):
    # محاولة استخراج href من <a>
    href_match = re.search(r'href=["\']([^"\']+)["\']', line)
    if href_match:
        return href_match.group(1)
    
    # محاولة استخراج onclick أو data-url
    onclick_match = re.search(r'onclick=["\']([^"\']+)["\']', line)
    if onclick_match:
        onclick = onclick_match.group(1)
        # إذا كان يحتوي على window.open أو location.href
        url_match = re.search(r'(?:window\.open|location\.href)\s*\(\s*["\']([^"\']+)["\']', onclick)
        if url_match:
            return url_match.group(1)
    
    # إذا كان في template، محاولة البحث عن name في urls
    if file_path.endswith('.html'):
        # هذا معقد، لكن للبساطة، نعيد None
        pass
    
    return None

def generate_report(results, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("تقرير البحث عن أزرار الطباعة\n")
        f.write("=" * 50 + "\n\n")
        
        if not results:
            f.write("لم يتم العثور على أي أزرار تحتوي على كلمة 'طباعة'.\n")
        else:
            f.write(f"تم العثور على {len(results)} نتيجة:\n\n")
            
            for i, result in enumerate(results, 1):
                f.write(f"{i}. الملف: {result['file_path']}\n")
                f.write(f"   السطر: {result['line']}\n")
                f.write(f"   المحتوى: {result['line_content']}\n")
                if result['url']:
                    f.write(f"   الرابط: {result['url']}\n")
                else:
                    f.write("   الرابط: غير محدد\n")
                f.write("\n")

if __name__ == "__main__":
    project_root = r"C:\Accounting_soft\finspilot"
    output_file = r"C:\Accounting_soft\finspilot\test\print_buttons_report.txt"
    
    results = find_print_buttons(project_root)
    generate_report(results, output_file)
    
    print(f"تم إنشاء التقرير في: {output_file}")