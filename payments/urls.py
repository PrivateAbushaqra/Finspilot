from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # سندات الصرف
    path('', views.payment_voucher_list, name='voucher_list'),
    path('create/', views.payment_voucher_create, name='voucher_create'),
    path('<int:pk>/', views.payment_voucher_detail, name='voucher_detail'),
    path('<int:pk>/edit/', views.payment_voucher_edit, name='voucher_edit'),
    path('<int:pk>/reverse/', views.payment_voucher_reverse, name='voucher_reverse'),
    path('<int:pk>/delete/', views.payment_voucher_delete, name='voucher_delete'),
    
    # AJAX
    path('ajax/supplier-data/', views.get_supplier_data, name='get_supplier_data'),
]
