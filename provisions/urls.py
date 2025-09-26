from django.urls import path
from . import views

app_name = 'provisions'

urlpatterns = [
    # Provision Types
    path('types/', views.ProvisionTypeListView.as_view(), name='provision_type_list'),
    path('types/create/', views.ProvisionTypeCreateView.as_view(), name='provision_type_create'),
    path('types/<int:pk>/update/', views.ProvisionTypeUpdateView.as_view(), name='provision_type_update'),
    path('types/<int:pk>/delete/', views.ProvisionTypeDeleteView.as_view(), name='provision_type_delete'),

    # Provisions
    path('', views.ProvisionListView.as_view(), name='provision_list'),
    path('<int:pk>/', views.ProvisionDetailView.as_view(), name='provision_detail'),
    path('create/', views.ProvisionCreateView.as_view(), name='provision_create'),
    path('<int:pk>/update/', views.ProvisionUpdateView.as_view(), name='provision_update'),
    path('<int:pk>/delete/', views.ProvisionDeleteView.as_view(), name='provision_delete'),

    # Provision Entries
    path('<int:provision_id>/entries/create/', views.provision_entry_create, name='provision_entry_create'),
    path('entries/<int:entry_id>/update/', views.provision_entry_update, name='provision_entry_update'),
    path('entries/<int:entry_id>/delete/', views.provision_entry_delete, name='provision_entry_delete'),

    # Reports
    path('reports/', views.provision_report, name='provision_report'),
    path('reports/movements/', views.provision_movement_report, name='provision_movement_report'),

    # AJAX
    path('<int:provision_id>/balance/', views.ajax_provision_balance, name='ajax_provision_balance'),
]