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
    path('statement/', views.PurchaseStatementView.as_view(), name='purchase_statement'),
    path('returns-statement/', views.PurchaseReturnStatementView.as_view(), name='purchase_return_statement'),
    # Debit Notes (separate section)
    path('debit-notes/', views.PurchaseDebitNoteListView.as_view(), name='debitnote_list'),
    path('debit-notes/add/', views.purchase_debitnote_create, name='debitnote_add'),
    path('debit-notes/<int:pk>/', views.PurchaseDebitNoteDetailView.as_view(), name='debitnote_detail'),
    path('debit-notes/edit/<int:pk>/', views.PurchaseDebitNoteUpdateView.as_view(), name='debitnote_edit'),
    path('debit-notes/delete/<int:pk>/', views.PurchaseDebitNoteDeleteView.as_view(), name='debitnote_delete'),
    path('debit-notes/report/', views.PurchaseDebitNoteReportView.as_view(), name='debitnote_report'),
    path('debit-notes/<int:pk>/send-to-jofotara/', views.send_debitnote_to_jofotara, name='send_debitnote_to_jofotara'),
]
