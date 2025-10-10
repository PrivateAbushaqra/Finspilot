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
    path('invoices/<int:pk>/send-to-jofotara/', views.send_invoice_to_jofotara, name='send_invoice_to_jofotara'),
    
    # Print Invoice
    path('invoices/print/<int:pk>/', views.print_sales_invoice, name='print_invoice'),
    path('invoices/pos-print/<int:pk>/', views.print_pos_invoice, name='print_pos_invoice'),
    
    # Invoice Item Management (AJAX)
    path('invoices/<int:invoice_id>/items/add/', views.invoice_add_item, name='invoice_add_item'),
    path('invoices/<int:invoice_id>/items/<int:item_id>/update/', views.invoice_update_item, name='invoice_update_item'),
    path('invoices/<int:invoice_id>/items/<int:item_id>/delete/', views.invoice_delete_item, name='invoice_delete_item'),
    
    # Sales Returns
    path('returns/', views.SalesReturnListView.as_view(), name='return_list'),
    path('returns/add/', views.sales_return_create, name='return_add'),
    # path('returns/<int:pk>/', views.SalesReturnDetailView.as_view(), name='return_detail'),
    # path('returns/edit/<int:pk>/', views.SalesReturnUpdateView.as_view(), name='return_edit'),
    path('returns/delete/<int:pk>/', views.SalesReturnDeleteView.as_view(), name='return_delete'),
    
    # API endpoints  
    path('api/invoices-for-returns/', views.get_invoices_for_returns, name='api_invoices_for_returns'),
    path('ajax/get-invoice-items/<int:invoice_id>/', views.get_invoice_items, name='get_invoice_items'),
    
    # Point of Sale
    path('pos/', views.pos_view, name='pos'),
    path('pos/create-invoice/', views.pos_create_invoice, name='pos_create_invoice'),
    path('pos/product/<int:product_id>/', views.pos_get_product, name='pos_get_product'),
    path('pos/search-products/', views.pos_search_products, name='pos_search_products'),
    
    # Reports
    path('reports/', views.SalesReportView.as_view(), name='sales_report'),
    path('statement/', views.SalesStatementView.as_view(), name='sales_statement'),
    path('returns-statement/', views.SalesReturnStatementView.as_view(), name='sales_return_statement'),
    # Credit Notes (separate section)
    path('credit-notes/', views.SalesCreditNoteListView.as_view(), name='creditnote_list'),
    # path('credit-notes/add/', views.sales_creditnote_create, name='creditnote_add'),
    path('credit-notes/<int:pk>/', views.SalesCreditNoteDetailView.as_view(), name='creditnote_detail'),
    path('credit-notes/edit/<int:pk>/', views.SalesCreditNoteUpdateView.as_view(), name='creditnote_edit'),
    path('credit-notes/delete/<int:pk>/', views.SalesCreditNoteDeleteView.as_view(), name='creditnote_delete'),
    path('credit-notes/report/', views.SalesCreditNoteReportView.as_view(), name='creditnote_report'),
    path('credit-notes/<int:pk>/send-to-jofotara/', views.send_creditnote_to_jofotara, name='send_creditnote_to_jofotara'),
]
