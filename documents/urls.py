from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('upload/<int:content_type_id>/<int:object_id>/', views.upload_document, name='upload'),
    path('list/<int:content_type_id>/<int:object_id>/', views.document_list, name='list'),
    path('delete/<int:document_id>/', views.delete_document, name='delete'),
    path('report/', views.document_report, name='report'),
]