from datetime import timedelta

from django.utils import timezone
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from apps.core.features import enabled

from .models import ApiKey

TOUCH_EVERY = timedelta(minutes=1)


class ApiUser:
    """Usuário "fantasma" da integração: o DRF exige um `request.user` autenticado."""

    is_authenticated = True
    is_anonymous = False

    def __init__(self, key):
        self.key = key
        self.pk = None

    def __str__(self):
        return f"api:{self.key.name}"


class ApiKeyAuthentication(BaseAuthentication):
    keyword = b"api-key"

    def authenticate(self, request):
        if not enabled("api"):
            return None  # o módulo desligado responde 404 pela permissão
        parts = get_authorization_header(request).split()
        if not parts or parts[0].lower() != self.keyword:
            return None
        if len(parts) != 2:
            raise AuthenticationFailed("Cabeçalho inválido. Use: Authorization: Api-Key <chave>.")
        key = ApiKey.lookup(parts[1].decode(errors="ignore"))
        if key is None:
            raise AuthenticationFailed("Chave de API inválida ou desativada.")
        now = timezone.now()
        if key.last_used_at is None or now - key.last_used_at > TOUCH_EVERY:
            ApiKey.objects.filter(pk=key.pk).update(last_used_at=now)
        return ApiUser(key), key

    def authenticate_header(self, request):
        return "Api-Key"


class ApiKeyScheme(OpenApiAuthenticationExtension):
    target_class = "apps.api.authentication.ApiKeyAuthentication"
    name = "ApiKeyAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Envie `Api-Key <sua chave>` (a chave é criada no painel).",
        }
