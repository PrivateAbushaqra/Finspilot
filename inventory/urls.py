from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.InventoryListView.as_view(), name='list'),
    path('product/<int:product_id>/', views.ProductInventoryDetailView.as_view(), name='product_detail'),
    path('api/product/', views.get_product_inventory_ajax, name='product_ajax'),
    path('warehouses/', views.WarehouseListView.as_view(), name='warehouse_list'),
    path('warehouses/add/', views.WarehouseCreateView.as_view(), name='warehouse_add'),
    path('warehouses/<int:pk>/', views.WarehouseDetailView.as_view(), name='warehouse_detail'),
    path('warehouses/edit/<int:pk>/', views.WarehouseEditView.as_view(), name='warehouse_edit'),
    path('warehouses/delete/<int:pk>/', views.WarehouseDeleteView.as_view(), name='warehouse_delete'),
    path('movements/', views.MovementListView.as_view(), name='movement_list'),
    path('movements/<int:pk>/delete/', views.MovementDeleteView.as_view(), name='movement_delete'),
    path('movements/bulk-delete/', views.MovementBulkDeleteView.as_view(), name='movement_bulk_delete'),
    path('transfers/', views.TransferListView.as_view(), name='transfer_list'),
    path('transfers/add/', views.TransferCreateView.as_view(), name='transfer_add'),
    path('transfers/get-product-stock/', views.get_product_stock, name='get_product_stock'),
    path('low-stock/', views.LowStockView.as_view(), name='low_stock'),
    path('export/excel/', views.export_inventory_excel, name='export_excel'),
]
