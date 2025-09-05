from django.urls import path
from . import views

app_name = 'assets_liabilities'

urlpatterns = [
    # لوحة التحكم
    path('', views.assets_liabilities_dashboard, name='dashboard'),
    
    # الأصول
    path('assets/', views.asset_list, name='asset_list'),
    path('assets/create/', views.asset_create, name='asset_create'),
    path('assets/<int:pk>/', views.asset_detail, name='asset_detail'),
    # path('assets/<int:pk>/edit/', views.asset_edit, name='asset_edit'),
    # path('assets/<int:pk>/delete/', views.asset_delete, name='asset_delete'),
    
    # إدارة الفئات
    path('categories/create-ajax/', views.category_create_ajax, name='category_create_ajax'),
    path('liability-categories/create-ajax/', views.liability_category_create_ajax, name='liability_category_create_ajax'),
    
    # الخصوم
    path('liabilities/', views.liability_list, name='liability_list'),
    path('liabilities/create/', views.liability_create, name='liability_create'),
    # path('liabilities/<int:pk>/', views.liability_detail, name='liability_detail'),
    # path('liabilities/<int:pk>/edit/', views.liability_edit, name='liability_edit'),
    # path('liabilities/<int:pk>/delete/', views.liability_delete, name='liability_delete'),
]
