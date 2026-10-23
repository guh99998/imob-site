from rest_framework.exceptions import NotAuthenticated, NotFound, PermissionDenied
from rest_framework.permissions import BasePermission

from apps.core.features import enabled

from .models import ApiKey


class ApiEnabled(BasePermission):
    """Módulo desligado: a API não existe (404), nem a documentação."""

    def has_permission(self, request, view):
        if not enabled("api"):
            raise NotFound()
        return True


class HasApiKey(BasePermission):
    def has_permission(self, request, view):
        if not isinstance(request.auth, ApiKey):
            raise NotAuthenticated("Informe a chave: Authorization: Api-Key <chave>.")
        return True


class FullAccess(BasePermission):
    """Rotas de clientes exigem uma chave com permissão total."""

    def has_permission(self, request, view):
        if request.auth.permission != ApiKey.Permission.FULL:
            raise PermissionDenied("Esta chave só pode enviar contatos.")
        return True
