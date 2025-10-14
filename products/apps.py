from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'
    verbose_name = 'المنتجات والفئات'
    
    def ready(self):
        """استيراد الإشارات عند بدء التطبيق"""
        import products.signals
