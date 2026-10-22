import logging

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.core.models import SiteSettings
from apps.properties.models import Property

from .forms import LeadForm

logger = logging.getLogger(__name__)

RATE_LIMIT = 5  # envios
RATE_WINDOW = 3600  # por hora, por IP


def _rate_limited(request):
    key = f"lead-rate:{request.META.get('REMOTE_ADDR', '')}"
    count = cache.get(key, 0)
    if count >= RATE_LIMIT:
        return True
    cache.set(key, count + 1, RATE_WINDOW)
    return False


def _notify(lead):
    to = SiteSettings.load().email
    if not to:
        return
    ref = f" sobre {lead.property}" if lead.property else ""
    send_mail(
        subject=f"Novo contato{ref}",
        message=f"Nome: {lead.name}\nEmail: {lead.email}\nTelefone: {lead.phone}\n\n{lead.message}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to],
        fail_silently=True,
    )


@require_POST
def create_lead(request, slug):
    prop = get_object_or_404(Property.objects.published(), slug=slug)
    form = LeadForm(request.POST)
    if _rate_limited(request):
        form.add_error(None, "Muitas mensagens enviadas. Tente novamente mais tarde.")
        status = 429
    elif form.is_valid():
        lead = form.save(commit=False)
        lead.property = prop
        lead.save()
        _notify(lead)
        return render(request, "leads/partials/success.html", {"property": prop})
    else:
        status = 200
    return render(
        request, "leads/partials/form.html", {"form": form, "property": prop}, status=status
    )
