from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.core.features import enabled
from apps.crm.services import register_lead, register_search
from apps.properties.models import Property

from .forms import LeadForm, PropertySearchForm
from .services import notify_lead, notify_search, rate_limited

RATE_MESSAGE = "Muitas mensagens enviadas. Tente novamente mais tarde."


@require_POST
def create_lead(request, slug):
    prop = get_object_or_404(Property.objects.published(), slug=slug)
    form = LeadForm(request.POST)
    if rate_limited(request):
        form.add_error(None, RATE_MESSAGE)
        status = 429
    elif form.is_valid():
        lead = form.save(commit=False)
        lead.property = prop
        lead.save()
        register_lead(lead)
        notify_lead(lead)
        return render(request, "leads/partials/success.html", {"property": prop})
    else:
        status = 200
    return render(
        request, "leads/partials/form.html", {"form": form, "property": prop}, status=status
    )


def lead_page(request, kind, template, action):
    """Página com formulário de contato/anúncio. Funciona com HTMX e sem JS."""
    form = LeadForm(request.POST or None)
    sent, status = False, 200
    if request.method == "POST":
        if rate_limited(request):
            form.add_error(None, RATE_MESSAGE)
            status = 429
        elif form.is_valid():
            lead = form.save(commit=False)
            lead.kind = kind
            lead.save()
            register_lead(lead)
            notify_lead(lead)
            sent = True
            form = LeadForm()
    ctx = {"form": form, "sent": sent, "action": action}
    if request.htmx:
        return render(request, "leads/partials/contact_box.html", ctx, status=status)
    return render(request, template, ctx, status=status)


def property_search(request):
    if not enabled("searches"):
        raise Http404
    form = PropertySearchForm(request.POST or None)
    sent, status = False, 200
    if request.method == "POST":
        if rate_limited(request):
            form.add_error(None, RATE_MESSAGE)
            status = 429
        elif form.is_valid():
            search = form.save()
            register_search(search)
            notify_search(search)
            sent = True
            form = PropertySearchForm()
    ctx = {"form": form, "sent": sent}
    if request.htmx:
        return render(request, "leads/partials/search_box.html", ctx, status=status)
    ctx["available_count"] = Property.objects.published().count()
    return render(request, "leads/property_search.html", ctx, status=status)
