"""Funcionalidades ligáveis por site: o mesmo painel serve a clientes com módulos diferentes."""

from django.conf import settings

ALL = ("brokers", "partners", "owners", "searches", "crm", "api")


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

    def _feature_off(self):
        return bool(self.feature) and not enabled(self.feature)

    def has_module_permission(self, request):
        return not self._feature_off() and super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return not self._feature_off() and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return not self._feature_off() and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return not self._feature_off() and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not self._feature_off() and super().has_delete_permission(request, obj)
