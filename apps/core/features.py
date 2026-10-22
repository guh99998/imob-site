"""Funcionalidades ligáveis por site: o mesmo painel serve a clientes com módulos diferentes."""

from django.conf import settings

ALL = ("brokers", "partners", "owners", "searches")


def enabled(name):
    return name in getattr(settings, "SITE_FEATURES", ALL)


def feature_check(name):
    """Callback de `permission` da sidebar: esconde o item se o módulo está desligado."""

    def check(request):
        return enabled(name)

    return check


class FeatureGatedAdminMixin:
    """ModelAdmin com `feature = "partners"`: some do painel quando o módulo está desligado."""

    feature = None

    def has_module_permission(self, request):
        if self.feature and not enabled(self.feature):
            return False
        return super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        if self.feature and not enabled(self.feature):
            return False
        return super().has_view_permission(request, obj)
