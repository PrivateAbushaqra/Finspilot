from django.urls import path
from . import views

app_name = 'assets_liabilities'

urlpatterns = [
    # لوحة التحكم
    path('', views.assets_liabilities_dashboard, name='dashboard'),
    
    # الأصول
    path('assets/', views.asset_list, name='asset_list'),
    
    # الخصوم
    path('liabilities/', views.liability_list, name='liability_list'),
]
