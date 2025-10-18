"""
URL configuration for finspilot project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import set_language
from django.views.generic import RedirectView
from core.views import logout_alias, language_switch_view

def redirect_to_default_language(request):
    """توجيه المستخدم إلى اللغة الافتراضية"""
    from django.shortcuts import redirect
    # استخدام اللغة الافتراضية من الإعدادات مباشرة
    language = settings.LANGUAGE_CODE
    return redirect(f'/{language}/')

urlpatterns = [
    path('', redirect_to_default_language, name='root_redirect'),
    path('admin/', admin.site.urls),
    path('api/', include('core.api_urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    # Alias غير مترجم للتعامل مع /logout/ مباشرةً (مثلاً من sendBeacon)
    path('logout/', logout_alias, name='logout'),
    # تبديل اللغة (خارج i18n_patterns لتجنب تضارب اللغات)
    path('language-switch/', language_switch_view, name='language_switch'),
    # إعادة توجيه favicon.ico إلى الأيقونة الصحيحة
    path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'FinsPiloticn.png', permanent=True)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += i18n_patterns(
    path('', include('core.urls')),
    # استخدام auth URLs المخصصة للتسجيل والخروج وإدارة الحسابات المالية
    path('auth/', include('accounts.urls', namespace='auth')),
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
    path('search/', include('search.urls')),  # البحث الشامل
    # التطبيقات الجديدة
    path('revenues-expenses/', include('revenues_expenses.urls')),
    path('assets-liabilities/', include('assets_liabilities.urls')),
    path('backup/', include('backup.urls')),
    path('hr/', include('hr.urls')),  # الموارد البشرية
    path('documents/', include('documents.urls')),
    path('provisions/', include('provisions.urls')),  # المخصصات المحاسبية
    # path('financial-reports/', include('financial_reports.urls')),  # معطل مؤقتاً
)
