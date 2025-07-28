from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('', views.CustomerSupplierListView.as_view(), name='list'),
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('suppliers/', views.SupplierListView.as_view(), name='supplier_list'),
    path('add/', views.CustomerSupplierCreateView.as_view(), name='add'),
    path('edit/<int:pk>/', views.CustomerSupplierUpdateView.as_view(), name='edit'),
    path('delete/<int:pk>/', views.CustomerSupplierDeleteView.as_view(), name='delete'),
    path('<int:pk>/transactions/', views.CustomerSupplierTransactionsView.as_view(), name='transactions'),
    path('<int:customer_pk>/transactions/<int:transaction_id>/delete/', views.delete_transaction, name='delete_transaction'),
    path('api/customer/<int:customer_id>/', views.get_customer_supplier_ajax, name='customer_ajax'),
    path('ajax/add-supplier/', views.ajax_add_supplier, name='ajax_add_supplier'),
    path('ajax/add-customer/', views.ajax_add_customer, name='ajax_add_customer'),
]
