"""Callbacks usados pelo UNFOLD["SIDEBAR"] (links dinâmicos, badges e permissões)."""

from django.urls import reverse


def _perm(codename):
    def check(request):
        return request.user.has_perm(codename)

    return check


can_view_property = _perm("properties.view_property")
can_add_property = _perm("properties.add_property")
can_view_category = _perm("properties.view_category")
can_view_feature = _perm("properties.view_feature")
can_view_city = _perm("properties.view_city")
can_view_neighborhood = _perm("properties.view_neighborhood")
can_view_lead = _perm("leads.view_lead")
can_view_settings = _perm("core.view_sitesettings")
can_view_user = _perm("auth.view_user")


def site_settings_link(request):
    """Link direto ao único registro de configurações (cria se ainda não existir)."""
    from .models import SiteSettings

    return reverse("admin:core_sitesettings_change", args=[SiteSettings.load().pk])


def new_leads_badge(request):
    from apps.leads.models import Lead

    count = Lead.objects.filter(status=Lead.Status.NEW).count()
    return count or None
