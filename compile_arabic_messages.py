#!/usr/bin/env python
"""
Custom script to compile only our Arabic messages
This avoids Django's default compilemessages which tries to compile ALL .po files
"""
import os
import subprocess
import sys
from pathlib import Path

def compile_our_messages():
    """Compile only our Arabic translation files"""
    
    # Get project root
    project_root = Path(__file__).parent
    locale_path = project_root / 'locale' / 'ar' / 'LC_MESSAGES'
    
    print(f"Compiling Arabic messages in: {locale_path}")
    
    if not locale_path.exists():
        print(f"Locale path does not exist: {locale_path}")
        return False
    
    # Find our django.po file
    django_po = locale_path / 'django.po'
    django_mo = locale_path / 'django.mo'
    
    if not django_po.exists():
        print(f"Django.po file not found: {django_po}")
        return False
    
    try:
        # Compile our specific .po file to .mo
        cmd = ['msgfmt', '-o', str(django_mo), str(django_po)]
        print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Successfully compiled {django_po}")
            return True
        else:
            print(f"❌ Error compiling {django_po}")
            print(f"Error output: {result.stderr}")
            return False
            
    except FileNotFoundError:
        # msgfmt not available, try using Django's compilemessages with specific locale
        print("msgfmt not found, using Django's compilemessages for ar locale only")
        try:
            cmd = [sys.executable, 'manage.py', 'compilemessages', '--locale=ar']
            result = subprocess.run(cmd, cwd=project_root)
            return result.returncode == 0
        except Exception as e:
            print(f"Error using Django compilemessages: {e}")
            return False

if __name__ == '__main__':
    success = compile_our_messages()
    sys.exit(0 if success else 1)
