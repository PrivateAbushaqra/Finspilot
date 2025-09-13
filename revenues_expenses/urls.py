from django.urls import path
from . import views

app_name = 'revenues_expenses'

urlpatterns = [
    path('categories/<int:category_id>/delete/', views.category_delete, name='category_delete'),
    path('entries/<int:entry_id>/delete/', views.entry_delete, name='entry_delete'),
    path('entries/<int:entry_id>/edit/', views.entry_edit, name='entry_edit'),
    # لوحة التحكم
    path('', views.revenue_expense_dashboard, name='dashboard'),
    
    # فئات الإيرادات والمصروفات
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:category_id>/edit/', views.category_edit, name='category_edit'),
    
    # قيود الإيرادات والمصروفات
    path('entries/', views.entry_list, name='entry_list'),
    path('entries/create/', views.entry_create, name='entry_create'),
    path('entries/<int:entry_id>/', views.entry_detail, name='entry_detail'),
    path('entries/<int:entry_id>/approve/', views.entry_approve, name='entry_approve'),
    
    # الإيرادات والمصروفات المتكررة
    path('recurring/', views.recurring_list, name='recurring_list'),
    path('recurring/create/', views.recurring_create, name='recurring_create'),
    path('recurring/<int:recurring_id>/', views.recurring_detail, name='recurring_detail'),
    path('recurring/<int:recurring_id>/edit/', views.recurring_edit, name='recurring_edit'),
    path('recurring/<int:recurring_id>/delete/', views.recurring_delete, name='recurring_delete'),
    path('recurring/<int:recurring_id>/toggle-status/', views.recurring_toggle_status, name='recurring_toggle_status'),
    path('recurring/<int:recurring_id>/generate/', views.recurring_generate_entry, name='recurring_generate_entry'),
    
    # API endpoints
    path('api/categories/<str:entry_type>/', views.get_categories_by_type, name='api_categories_by_type'),
    path('api/today-stats/', views.get_today_stats, name='api_today_stats'),
]
