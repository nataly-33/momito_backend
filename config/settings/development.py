from .base import *

DEBUG = True

AUTH_PASSWORD_VALIDATORS = []

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Archivos subidos van directamente a tm_frontend/public/ — Vite los sirve en dev.
# MEDIA_URL='/' → Django retorna /images/productos/file.jpg (ruta relativa al root).
# Funciona igual en dev (localhost:3000) y en producción (cualquier dominio).
MEDIA_ROOT = BASE_DIR.parent / 'tm_frontend' / 'public'
MEDIA_URL = '/'

# Para debug
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}