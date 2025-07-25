"""
URL configuration for finspilot project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import set_language

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.api_urls')),
    path('i18n/', include('django.conf.urls.i18n')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += i18n_patterns(
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('products/', include('products.urls')),
    path('customers/', include('customers.urls')),
    path('purchases/', include('purchases.urls')),
    path('sales/', include('sales.urls')),
    path('inventory/', include('inventory.urls')),
    path('banks/', include('banks.urls')),
    path('cashboxes/', include('cashboxes.urls')),
    path('receipts/', include('receipts.urls')),
    path('payments/', include('payments.urls')),
    path('journal/', include('journal.urls')),
    path('reports/', include('reports.urls')),
    path('users/', include('users.urls')),
    path('settings/', include('settings.urls')),
    # التطبيقات الجديدة
    path('revenues-expenses/', include('revenues_expenses.urls')),
    path('assets-liabilities/', include('assets_liabilities.urls')),
    # path('financial-reports/', include('financial_reports.urls')),  # معطل مؤقتاً
)
