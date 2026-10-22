from django.contrib.admin.models import LogEntry
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.leads.models import Lead
from apps.properties.models import Property


def _recent_activity(request):
    """Últimas ações no painel (só para quem pode ver a equipe/histórico completo)."""
    from apps.people.roles import has_full_access

    if not has_full_access(request.user):
        return []
    return list(LogEntry.objects.select_related("user", "content_type")[:8])


def dashboard_callback(request, context):
    """Contexto da página inicial do admin (templates/admin/index.html)."""
    from apps.people.scoping import is_scoped, own_properties_q

    today = timezone.localdate()
    S = Property.Status
    properties = Property.objects.all()
    leads = Lead.objects.all()
    if is_scoped(request.user):
        properties = properties.filter(own_properties_q(request.user)).distinct()
        leads = leads.filter(own_properties_q(request.user, "property__")).distinct()
    month_closed = properties.filter(
        status__in=[S.SOLD, S.RENTED],
        updated_at__year=today.year,
        updated_at__month=today.month,
    ).count()
    new_leads = leads.filter(status=Lead.Status.NEW).count()

    context.update(
        {
            "shortcuts": [
                {
                    "label": _("Cadastrar imóvel"),
                    "icon": "add_home",
                    "url": reverse("admin:properties_property_add"),
                    "primary": True,
                },
                {
                    "label": _("Ver mensagens novas"),
                    "icon": "mail",
                    "url": reverse("admin:leads_lead_changelist")
                    + f"?status__exact={Lead.Status.NEW}",
                    "badge": new_leads or None,
                },
                {"label": _("Abrir o site"), "icon": "open_in_new", "url": "/"},
            ],
            "numbers": [
                {
                    "label": _("Publicados"),
                    "value": properties.filter(status=S.PUBLISHED).count(),
                },
                {
                    "label": _("Rascunhos"),
                    "value": properties.filter(status=S.DRAFT).count(),
                },
                {"label": _("Vendidos/alugados no mês"), "value": month_closed},
                {"label": _("Mensagens novas"), "value": new_leads},
            ],
            "recent_properties": properties.select_related("category")
            .prefetch_related("photos")
            .order_by("-updated_at")[:5],
            "recent_leads": leads.select_related("property")[:5],
            "activity": _recent_activity(request),
        }
    )
    return context
