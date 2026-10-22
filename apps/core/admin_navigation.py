"""Callbacks usados pelo UNFOLD["SIDEBAR"] (links dinâmicos, badges e permissões)."""

from django.urls import reverse

from .features import enabled


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


def _feature_perm(feature, codename):
    def check(request):
        return enabled(feature) and request.user.has_perm(codename)

    return check


can_view_broker = _feature_perm("brokers", "people.view_broker")
can_view_partner = _feature_perm("partners", "people.view_partner")
can_view_owner = _feature_perm("owners", "people.view_owner")
can_view_search = _feature_perm("searches", "leads.view_propertysearch")


def can_view_user(request):
    from apps.people.roles import ADMIN, role_of

    return role_of(request.user) == ADMIN and request.user.has_perm("auth.view_user")


def masks_script(request):
    from django.templatetags.static import static

    return static("core/admin/masks.js")


def _is_property_list(request):
    return request.path.startswith(reverse("admin:properties_property_changelist"))


def all_properties_active(request):
    """ "Todos os imóveis" fica ativo na lista e na edição, mas não em /add/."""
    return _is_property_list(request) and not request.path.endswith("/add/")


def add_property_active(request):
    return request.path == reverse("admin:properties_property_add")


def site_settings_link(request):
    """Link direto ao único registro de configurações (cria se ainda não existir)."""
    from .models import SiteSettings

    return reverse("admin:core_sitesettings_change", args=[SiteSettings.load().pk])


def new_leads_badge(request):
    from apps.leads.models import Lead

    count = Lead.objects.filter(status=Lead.Status.NEW).count()
    return count or None


def new_searches_badge(request):
    from apps.leads.models import PropertySearch

    count = PropertySearch.objects.filter(status=PropertySearch.Status.NEW).count()
    return count or None
