from django.urls import path
from . import views

app_name = 'receipts'

urlpatterns = [
    # سندات القبض
    path('', views.receipt_list, name='receipt_list'),
    path('add/', views.receipt_add, name='receipt_add'),
    path('<int:receipt_id>/', views.receipt_detail, name='receipt_detail'),
    path('<int:receipt_id>/edit/', views.receipt_edit, name='receipt_edit'),
    path('<int:receipt_id>/reverse/', views.receipt_reverse, name='receipt_reverse'),
    
    # تحصيل الشيكات
    path('checks/', views.check_list, name='check_list'),
    path('checks/export/excel/', views.check_list_export_excel, name='check_list_export_excel'),
    path('checks/<int:receipt_id>/collect/', views.check_collect, name='check_collect'),
    
    # Ajax APIs
    path('api/customer/<int:customer_id>/balance/', views.get_customer_balance, name='get_customer_balance'),
]
