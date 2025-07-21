from django.urls import path
from . import views

app_name = 'revenues_expenses'

urlpatterns = [
    # لوحة التحكم
    path('', views.revenue_expense_dashboard, name='dashboard'),
    
    # فئات الإيرادات والمصروفات
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    
    # قيود الإيرادات والمصروفات
    path('entries/', views.entry_list, name='entry_list'),
    path('entries/create/', views.entry_create, name='entry_create'),
    path('entries/<int:entry_id>/', views.entry_detail, name='entry_detail'),
    path('entries/<int:entry_id>/approve/', views.entry_approve, name='entry_approve'),
    
    # الإيرادات والمصروفات المتكررة
    path('recurring/', views.recurring_list, name='recurring_list'),
]
