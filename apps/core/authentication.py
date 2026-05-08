from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class SilentJWTAuthentication(JWTAuthentication):
    """JWT authentication que silencia tokens inválidos/expirados.

    Comportamiento:
    - Token válido   → autentica el usuario normalmente
    - Token expirado → retorna None (usuario anónimo), NO levanta 401
    - Sin token      → retorna None (usuario anónimo)

    Esto permite que los endpoints AllowAny (como el catálogo de productos)
    funcionen correctamente incluso cuando el browser envía un access_token
    vencido en el header Authorization.
    """

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except AuthenticationFailed:
            return None
