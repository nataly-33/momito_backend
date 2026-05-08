"""
ASGI config para TUMOMITO ERP — con soporte WebSocket (django-channels).
"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Inicializar Django antes de importar consumers (que usan modelos)
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from apps.products.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    }
)
