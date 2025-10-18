#!/usr/bin/env python
"""
فحص syntax errors في JavaScript
"""
import re

# قراءة الملف
with open(r'c:\Accounting_soft\finspilot\templates\sales\invoice_edit.html', 'r', encoding='utf-8') as f:
    content = f.read()

# استخراج كل كود JavaScript
js_pattern = r'<script[^>]*>(.*?)</script>'
js_blocks = re.findall(js_pattern, content, re.DOTALL)

print(f"عدد كتل JavaScript: {len(js_blocks)}")

for i, js_code in enumerate(js_blocks, 1):
    print(f"\n{'='*80}")
    print(f"كتلة JavaScript #{i}")
    print(f"{'='*80}")
    
    # عد الأقواس
    open_braces = js_code.count('{')
    close_braces = js_code.count('}')
    open_parens = js_code.count('(')
    close_parens = js_code.count(')')
    open_brackets = js_code.count('[')
    close_brackets = js_code.count(']')
    
    print(f"{{ : {open_braces}")
    print(f"}} : {close_braces}")
    print(f"الفرق: {open_braces - close_braces}")
    print()
    print(f"( : {open_parens}")
    print(f") : {close_parens}")
    print(f"الفرق: {open_parens - close_parens}")
    print()
    print(f"[ : {open_brackets}")
    print(f"] : {close_brackets}")
    print(f"الفرق: {open_brackets - close_brackets}")
    
    if open_braces != close_braces:
        print(f"\n⚠️ خطأ: الأقواس {{ }} غير متوازنة!")
    if open_parens != close_parens:
        print(f"\n⚠️ خطأ: الأقواس ( ) غير متوازنة!")
    if open_brackets != close_brackets:
        print(f"\n⚠️ خطأ: الأقواس [ ] غير متوازنة!")
    
    # عرض آخر 20 سطراً
    lines = js_code.strip().split('\n')
    print(f"\nآخر 20 سطر:")
    print("-" * 80)
    for j, line in enumerate(lines[-20:], len(lines) - 19):
        print(f"{j:4d}: {line}")
