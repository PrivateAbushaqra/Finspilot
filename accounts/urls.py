from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(
        next_page=settings.LOGOUT_REDIRECT_URL
    ), name='logout'),
    path('password-change/', auth_views.PasswordChangeView.as_view(
        template_name='accounts/password_change.html',
        success_url='/accounts/password-change/done/'
    ), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='accounts/password_change_done.html'
    ), name='password_change_done'),
    
    # حركات الحسابات
    path('transactions/', views.AccountTransactionListView.as_view(), name='transaction_list'),
    path('customer/<int:customer_id>/statement/', views.customer_account_statement, name='customer_statement'),
    path('create-transactions/', views.create_account_transactions_for_existing_invoices, name='create_transactions'),
]
