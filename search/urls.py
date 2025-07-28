from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    path('', views.search_view, name='search'),
    path('api/search/', views.search_api, name='search_api'),
]
