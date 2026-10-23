from datetime import timedelta

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


def searches_number():
    from apps.leads.models import PropertySearch

    from .features import enabled

    if not enabled("searches"):
        return []
    count = PropertySearch.objects.filter(status=PropertySearch.Status.NEW).count()
    return [{"label": _("Procuras novas"), "value": count}]


def crm_followups(request):
    """Retornos pendentes que o usuário pode ver (o Corretor só vê os dos seus clientes)."""
    from apps.crm.models import FollowUp
    from apps.people.scoping import is_scoped, own_properties_q

    qs = FollowUp.objects.filter(done=False)
    if is_scoped(request.user):
        qs = qs.filter(own_properties_q(request.user, "client__")).distinct()
    return qs


def crm_context(request):
    from .features import enabled

    if not (enabled("crm") and request.user.has_perm("crm.view_followup")):
        return {"numbers": [], "followups": None, "shortcuts": []}
    today = timezone.localdate()
    pending = crm_followups(request)
    due_today = pending.filter(due_date=today).count()
    overdue = pending.filter(due_date__lt=today).count()
    url = reverse("admin:crm_followup_changelist") + "?done__exact=0"
    return {
        "numbers": [
            {"label": _("Retornos hoje"), "value": due_today},
            {"label": _("Retornos atrasados"), "value": overdue},
        ],
        "followups": list(
            pending.filter(due_date__lte=today + timedelta(days=3))
            .select_related("client")
            .order_by("due_date")[:8]
        ),
        "shortcuts": [
            {
                "label": _("Funil de clientes"),
                "icon": "view_kanban",
                "url": reverse("admin:crm_client_kanban"),
            },
            {
                "label": _("Retornos de hoje"),
                "icon": "event_upcoming",
                "url": url,
                "badge": (due_today + overdue) or None,
            },
        ],
    }


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
    crm = crm_context(request)

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
                *crm["shortcuts"],
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
                *searches_number(),
                *crm["numbers"],
            ],
            "followups": crm["followups"],
            "recent_properties": properties.select_related("category")
            .prefetch_related("photos")
            .order_by("-updated_at")[:5],
            "recent_leads": leads.select_related("property")[:5],
            "activity": _recent_activity(request),
        }
    )
    return context
