from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle

from .models import ApiKey


class ApiKeyThrottle(SimpleRateThrottle):
    """Limite por chave (não por IP: portais chamam de poucos servidores)."""

    scope = "apikey"

    def get_rate(self):
        return getattr(settings, "API_THROTTLE_RATE", "120/min")

    def get_cache_key(self, request, view):
        if not isinstance(request.auth, ApiKey):
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.auth.pk}
