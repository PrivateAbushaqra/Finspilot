from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Sales Invoices
    path('invoices/', views.SalesInvoiceListView.as_view(), name='invoice_list'),
    path('invoices/add/', views.sales_invoice_create, name='invoice_add'),
    path('invoices/<int:pk>/', views.SalesInvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/edit/<int:pk>/', views.SalesInvoiceUpdateView.as_view(), name='invoice_edit'),
    path('invoices/delete/<int:pk>/', views.SalesInvoiceDeleteView.as_view(), name='invoice_delete'),
    path('invoices/print/<int:pk>/', views.print_sales_invoice, name='invoice_print'),
    
    # Sales Returns
    path('returns/', views.SalesReturnListView.as_view(), name='return_list'),
    path('returns/add/', views.SalesReturnCreateView.as_view(), name='return_add'),
    path('returns/<int:pk>/', views.SalesReturnDetailView.as_view(), name='return_detail'),
    path('returns/edit/<int:pk>/', views.SalesReturnUpdateView.as_view(), name='return_edit'),
    path('returns/delete/<int:pk>/', views.SalesReturnDeleteView.as_view(), name='return_delete'),
    
    # Point of Sale
    path('pos/', views.pos_view, name='pos'),
    path('pos/create-invoice/', views.pos_create_invoice, name='pos_create_invoice'),
    path('pos/product/<int:product_id>/', views.pos_get_product, name='pos_get_product'),
    path('pos/search-products/', views.pos_search_products, name='pos_search_products'),
    
    # Reports
    path('reports/', views.SalesReportView.as_view(), name='sales_report'),
]
