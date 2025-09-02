#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup

def check_login_page():
    """Check the login page structure"""
    
    try:
        response = requests.get("http://127.0.0.1:8000/ar/auth/login/")
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all forms
            forms = soup.find_all('form')
            print(f"عدد النماذج الموجودة: {len(forms)}")
            
            for i, form in enumerate(forms):
                print(f"\n--- نموذج {i+1} ---")
                print(f"Action: {form.get('action', 'None')}")
                print(f"Method: {form.get('method', 'GET')}")
                
                inputs = form.find_all('input')
                print(f"عدد الحقول: {len(inputs)}")
                
                for inp in inputs:
                    name = inp.get('name', 'unnamed')
                    input_type = inp.get('type', 'text')
                    value = inp.get('value', '')
                    placeholder = inp.get('placeholder', '')
                    print(f"  - {name} ({input_type}): '{value}' placeholder='{placeholder}'")
                
                # Check for textarea
                textareas = form.find_all('textarea')
                for ta in textareas:
                    name = ta.get('name', 'unnamed')
                    print(f"  - {name} (textarea)")
                
                # Check for select
                selects = form.find_all('select')
                for sel in selects:
                    name = sel.get('name', 'unnamed')
                    print(f"  - {name} (select)")
            
            # Also look for any input outside of forms
            all_inputs = soup.find_all('input')
            print(f"\nجميع الحقول في الصفحة: {len(all_inputs)}")
            
            username_fields = []
            password_fields = []
            
            for inp in all_inputs:
                name = inp.get('name', '')
                input_type = inp.get('type', '')
                placeholder = inp.get('placeholder', '').lower()
                
                if ('user' in name.lower() or 'email' in name.lower() or 
                    'user' in placeholder or 'email' in placeholder):
                    username_fields.append(inp)
                elif input_type.lower() == 'password' or 'password' in placeholder:
                    password_fields.append(inp)
            
            print(f"\nحقول اسم المستخدم المحتملة: {len(username_fields)}")
            for uf in username_fields:
                print(f"  - {uf.get('name', 'unnamed')} ({uf.get('type', 'text')})")
            
            print(f"\nحقول كلمة المرور المحتملة: {len(password_fields)}")
            for pf in password_fields:
                print(f"  - {pf.get('name', 'unnamed')} ({pf.get('type', 'password')})")
                
        else:
            print(f"خطأ في الوصول للصفحة: {response.status_code}")
            
    except Exception as e:
        print(f"خطأ: {e}")

if __name__ == "__main__":
    check_login_page()
