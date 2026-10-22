from django.db.models import Q

from .roles import BROKER, role_of


def is_scoped(user):
    """Corretor vê só o que é dele; Administrador/Gerente/Atendente veem tudo que podem."""
    return not user.is_superuser and role_of(user) == BROKER


def own_properties_q(user, prefix=""):
    """Imóveis em que o usuário é o corretor responsável ou o criador."""
    return Q(**{f"{prefix}broker__user": user}) | Q(**{f"{prefix}created_by": user})


class ScopedByRoleMixin:
    """Filtra o queryset do ModelAdmin para o Corretor. `scope_prefix` é o caminho até Property."""

    scope_prefix = ""

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if is_scoped(request.user):
            qs = qs.filter(own_properties_q(request.user, self.scope_prefix)).distinct()
        return qs
