from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView, 
    SpectacularSwaggerView, 
    SpectacularRedocView
)

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),
    
    # Documentación API
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Apps URLs
    path('api/auth/', include('apps.accounts.urls')),
    path('api/products/', include('apps.products.urls')),
    path('api/customers/', include('apps.customers.urls')),
    path('api/cart/', include('apps.cart.urls')),
    path('api/orders/', include('apps.orders.urls')),
    path('api/', include('apps.reports.urls')),
    path('api/', include('apps.ai.urls')),
    path('api/', include('apps.quotes.urls')),
]

# Servir archivos media en desarrollo.
# Cuando MEDIA_URL='/' los archivos los sirve Vite desde public/, no Django.
# Cuando MEDIA_URL='/media/' (producción u otro entorno) Django los sirve directamente.
if settings.DEBUG and settings.MEDIA_URL not in ('/', ''):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Personalización del Admin
admin.site.site_header = "TUMOMITO S.A. — Admin"
admin.site.site_title = "TUMOMITO ERP"
admin.site.index_title = "Panel de Administración"