from .base import *

DEBUG = False

# ── Seguridad ─────────────────────────────────────────────
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 3600
X_FRAME_OPTIONS = "DENY"

# ── Archivos estáticos — WhiteNoise (CSS/JS del proyecto) ─
# WhiteNoise sirve los archivos estáticos directamente desde Django
# sin necesidad de S3, lo que simplifica el deploy en Render.
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Insertar WhiteNoise después de SecurityMiddleware
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

# ── Archivos de media — AWS S3 (fotos de productos) ───────
# S3 es obligatorio en producción porque Render tiene filesystem efímero.
USE_S3 = config("USE_S3", default=False, cast=bool)

if USE_S3:
    AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="us-east-1")
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com"

    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
    AWS_DEFAULT_ACL = "public-read"
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_FILE_OVERWRITE = False

    # Solo media va a S3; static lo maneja WhiteNoise
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
    AWS_LOCATION = "media"
else:
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"
