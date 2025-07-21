from django.urls import path
from . import views

app_name = 'settings'

urlpatterns = [
    path('', views.SettingsView.as_view(), name='index'),
    path('document-sequences/', views.DocumentSequenceView.as_view(), name='document_sequences'),
    path('document-sequences/edit/<int:seq_id>/', views.DocumentSequenceEditView.as_view(), name='document_sequence_edit'),
    path('document-sequences/add/', views.DocumentSequenceAddView.as_view(), name='document_sequence_add'),
    path('document-sequences/delete/<int:seq_id>/', views.DocumentSequenceDeleteView.as_view(), name='document_sequence_delete'),
    path('company/', views.CompanySettingsView.as_view(), name='company'),
    
    # إدارة العملات
    path('currencies/', views.CurrencyListView.as_view(), name='currency_list'),
    path('currencies/add/', views.CurrencyAddView.as_view(), name='currency_add'),
    path('currencies/edit/<int:currency_id>/', views.CurrencyEditView.as_view(), name='currency_edit'),
    path('currencies/delete/<int:currency_id>/', views.CurrencyDeleteView.as_view(), name='currency_delete'),
    path('currencies/set-base/<int:currency_id>/', views.SetBaseCurrencyView.as_view(), name='set_base_currency'),
]
