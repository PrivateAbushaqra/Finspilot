from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.UserListView.as_view(), name='user_list'),
    path('add/', views.UserCreateView.as_view(), name='user_add'),
    path('edit/<int:pk>/', views.UserUpdateView.as_view(), name='user_edit'),
    path('delete/<int:pk>/', views.UserDeleteView.as_view(), name='user_delete'),
    path('change-password/<int:pk>/', views.change_user_password, name='change_password'),
    path('toggle-superuser-visibility/', views.toggle_superuser_visibility, name='toggle_superuser_visibility'),
    path('groups/', views.UserGroupListView.as_view(), name='group_list'),
    path('groups/add/', views.UserGroupCreateView.as_view(), name='group_add'),
    path('groups/edit/<int:pk>/', views.UserGroupUpdateView.as_view(), name='group_edit'),
    path('groups/delete/<int:pk>/', views.UserGroupDeleteView.as_view(), name='group_delete'),
]
