from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.leads.models import Lead
from apps.properties.models import Property


def dashboard_callback(request, context):
    """Contexto da página inicial do admin (templates/admin/index.html)."""
    today = timezone.localdate()
    S = Property.Status
    month_closed = Property.objects.filter(
        status__in=[S.SOLD, S.RENTED],
        updated_at__year=today.year,
        updated_at__month=today.month,
    ).count()
    new_leads = Lead.objects.filter(status=Lead.Status.NEW).count()

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
                    "value": Property.objects.filter(status=S.PUBLISHED).count(),
                },
                {
                    "label": _("Rascunhos"),
                    "value": Property.objects.filter(status=S.DRAFT).count(),
                },
                {"label": _("Vendidos/alugados no mês"), "value": month_closed},
                {"label": _("Mensagens novas"), "value": new_leads},
            ],
            "recent_properties": Property.objects.select_related("category")
            .prefetch_related("photos")
            .order_by("-updated_at")[:5],
            "recent_leads": Lead.objects.select_related("property")[:5],
        }
    )
    return context
