from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/add/', views.CategoryCreateView.as_view(), name='category_add'),
    path('categories/edit/<int:pk>/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('categories/delete/<int:pk>/', views.CategoryDeleteView.as_view(), name='category_delete'),
    
    # Products
    path('', views.ProductListView.as_view(), name='product_list'),
    path('add/', views.ProductCreateView.as_view(), name='product_add'),
    path('detail/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('edit/<int:pk>/', views.ProductUpdateView.as_view(), name='product_edit'),
    path('delete/<int:pk>/', views.ProductDeleteView.as_view(), name='product_delete'),
    path('api/search/', views.product_search_api, name='product_search_api'),
    path('api/category/add/', views.category_add_ajax, name='category_add_ajax'),
    path('api/product/add/', views.product_add_ajax, name='product_add_ajax'),
]
