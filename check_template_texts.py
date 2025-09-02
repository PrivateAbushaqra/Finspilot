#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
سكريبت للتحقق من النصوص الإنجليزية في القوالب والملفات
"""
import os
import sys
import django
import re
from pathlib import Path

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

def find_english_in_templates():
    """البحث عن النصوص الإنجليزية في القوالب"""
    
    print("🔍 فحص قوالب HTML للبحث عن النصوص الإنجليزية...")
    
    template_dirs = [
        'templates',
        'accounting/templates',
        'hr/templates',
        'employees/templates',
        'reports/templates',
        'users/templates'
    ]
    
    english_texts = []
    english_pattern = re.compile(r'\b[A-Za-z]{3,}\b')
    
    for template_dir in template_dirs:
        if os.path.exists(template_dir):
            for root, dirs, files in os.walk(template_dir):
                for file in files:
                    if file.endswith('.html'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                
                                # البحث عن النصوص الإنجليزية خارج علامات Django
                                lines = content.split('\n')
                                for line_num, line in enumerate(lines, 1):
                                    # تجاهل السطور التي تحتوي على كود Django
                                    if '{% ' in line or '{{ ' in line or '{% load ' in line:
                                        continue
                                    
                                    # تجاهل السطور التي تحتوي على HTML tags فقط
                                    clean_line = re.sub(r'<[^>]+>', '', line).strip()
                                    
                                    if clean_line and english_pattern.search(clean_line):
                                        # التأكد من أن النص ليس مجرد كلمات برمجية
                                        words = english_pattern.findall(clean_line)
                                        meaningful_words = [w for w in words if len(w) > 2 and w not in ['div', 'span', 'class', 'style', 'href', 'src', 'alt', 'title']]
                                        
                                        if meaningful_words:
                                            english_texts.append({
                                                'file': file_path,
                                                'line': line_num,
                                                'text': clean_line.strip(),
                                                'words': meaningful_words
                                            })
                        except Exception as e:
                            continue
    
    print("\n📋 النصوص الإنجليزية الموجودة في القوالب:")
    print("=" * 60)
    
    if english_texts:
        for i, item in enumerate(english_texts, 1):
            print(f"{i}. الملف: {item['file']}")
            print(f"   السطر: {item['line']}")
            print(f"   النص: '{item['text']}'")
            print(f"   الكلمات الإنجليزية: {', '.join(item['words'])}")
            print("-" * 40)
    else:
        print("✅ لم يتم العثور على نصوص إنجليزية في القوالب!")
    
    print(f"\n📊 إجمالي النصوص الإنجليزية: {len(english_texts)}")
    
    # حفظ النتائج
    with open('english_templates_report.txt', 'w', encoding='utf-8') as f:
        f.write("تقرير النصوص الإنجليزية في القوالب\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"عدد النصوص الإنجليزية: {len(english_texts)}\n\n")
        
        for i, item in enumerate(english_texts, 1):
            f.write(f"{i}. الملف: {item['file']}\n")
            f.write(f"   السطر: {item['line']}\n")
            f.write(f"   النص: '{item['text']}'\n")
            f.write(f"   الكلمات الإنجليزية: {', '.join(item['words'])}\n")
            f.write("-" * 40 + "\n")
    
    return english_texts

def check_main_template():
    """فحص القالب الأساسي"""
    print("\n🔍 فحص القالب الأساسي...")
    
    main_templates = [
        'templates/base.html',
        'templates/dashboard.html',
        'templates/index.html'
    ]
    
    for template in main_templates:
        if os.path.exists(template):
            print(f"\n📄 فحص {template}:")
            with open(template, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # البحث عن النصوص المرئية
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    # البحث عن النصوص خارج العلامات
                    if any(word in line.lower() for word in ['dashboard', 'home', 'menu', 'login', 'logout', 'profile', 'settings']):
                        print(f"   السطر {line_num}: {line.strip()}")

if __name__ == "__main__":
    english_texts = find_english_in_templates()
    check_main_template()
