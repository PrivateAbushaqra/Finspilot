#!/usr/bin/env python3
import subprocess
import sys

try:
    result = subprocess.run([
        sys.executable, '-c', 
        '''
import requests
try:
    r = requests.get("http://127.0.0.1:8000/ar/", timeout=5)
    import re
    words = re.findall(r"\\b[A-Za-z]+\\b", r.text)
    filtered = [w for w in words if len(w) > 2 and w not in ["FinsPilot", "Super", "Administrator"]]
    unique = list(set(filtered))
    print(f"Status: {r.status_code}")
    print(f"English terms: {len(unique)}")
    print(f"Total words: {len(filtered)}")
    if len(unique) <= 20:
        print("EXCELLENT: Very close to completion!")
    elif len(unique) <= 50:
        print("GOOD: Significant improvement!")
    else:
        print("OK: More work needed")
    # Show top words
    from collections import Counter
    counts = Counter(filtered)
    print("Top words:", list(counts.most_common(5)))
except Exception as e:
    print(f"Error: {e}")
        '''
    ], capture_output=True, text=True, timeout=10)
    
    print("🔍 نتائج الفحص:")
    print(result.stdout)
    
    if result.stderr:
        print("⚠️ تحذيرات:")
        print(result.stderr)
        
except Exception as e:
    print(f"❌ خطأ في التشغيل: {e}")
