#!/usr/bin/env python
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finspilot.settings')
django.setup()

from search.views import search_api
from django.http import HttpRequest
from django.contrib.auth import get_user_model

# إنشاء request مزيف للاختبار
request = HttpRequest()
request.GET = {'q': 'test'}
request.method = 'GET'

# إنشاء مستخدم مزيف
User = get_user_model()
if User.objects.exists():
    request.user = User.objects.first()
    print("البحث يعمل، تم العثور على مستخدم للاختبار")
    
    # اختبار البحث
    try:
        response = search_api(request)
        print("البحث نجح!")
        print(f"عدد النتائج: {len(response.content)}")
    except Exception as e:
        print(f"خطأ في البحث: {e}")
else:
    print("لا يوجد مستخدمين للاختبار")
