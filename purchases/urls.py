from django.urls import path
from . import views

app_name = 'purchases'

urlpatterns = [
    path('invoices/', views.PurchaseInvoiceListView.as_view(), name='invoice_list'),
    path('invoices/add/', views.PurchaseInvoiceCreateView.as_view(), name='invoice_add'),
    path('invoices/<int:pk>/', views.PurchaseInvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/edit/<int:pk>/', views.PurchaseInvoiceUpdateView.as_view(), name='invoice_edit'),
    path('invoices/delete/<int:pk>/', views.PurchaseInvoiceDeleteView.as_view(), name='invoice_delete'),
    
    # Purchase Returns URLs
    path('returns/', views.PurchaseReturnListView.as_view(), name='return_list'),
    path('returns/add/', views.PurchaseReturnCreateView.as_view(), name='return_add'),
    path('returns/<int:pk>/', views.PurchaseReturnDetailView.as_view(), name='return_detail'),
    path('returns/edit/<int:pk>/', views.PurchaseReturnUpdateView.as_view(), name='return_edit'),
    path('returns/delete/<int:pk>/', views.PurchaseReturnDeleteView.as_view(), name='return_delete'),
    
    # AJAX endpoints for returns
    path('ajax/get-invoice-items/<int:invoice_id>/', views.get_invoice_items, name='get_invoice_items'),
    
    # Reports
    path('reports/', views.PurchaseReportView.as_view(), name='purchase_report'),
]
