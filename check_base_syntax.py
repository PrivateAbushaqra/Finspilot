#!/usr/bin/env python
"""
فحص syntax errors في base.html
"""
import re

# قراءة الملف
with open(r'c:\Accounting_soft\finspilot\templates\base.html', 'r', encoding='utf-8') as f:
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
    
    print(f"{{ : {open_braces}")
    print(f"}} : {close_braces}")
    print(f"الفرق: {open_braces - close_braces}")
    
    if open_braces != close_braces:
        print(f"\n⚠️ خطأ: الأقواس {{ }} غير متوازنة!")
        
        # ابحث عن الموقع
        depth = 0
        for j, char in enumerate(js_code):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth < 0:
                    # وجدنا } زائدة
                    lines_before = js_code[:j].count('\n')
                    line_start = js_code.rfind('\n', 0, j) + 1
                    line_end = js_code.find('\n', j)
                    if line_end == -1:
                        line_end = len(js_code)
                    print(f"\n❌ وجدت }} زائدة في السطر {lines_before + 1}:")
                    print(f"   {js_code[line_start:line_end]}")
                    break
