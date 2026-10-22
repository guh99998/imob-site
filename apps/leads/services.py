"""Anti-spam e notificação compartilhados pelos formulários públicos."""

import logging

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail

from apps.core.models import SiteSettings

logger = logging.getLogger(__name__)

RATE_LIMIT = 5  # envios
RATE_WINDOW = 3600  # por hora, por IP


def rate_limited(request):
    key = f"lead-rate:{request.META.get('REMOTE_ADDR', '')}"
    count = cache.get(key, 0)
    if count >= RATE_LIMIT:
        return True
    cache.set(key, count + 1, RATE_WINDOW)
    return False


def notify(subject, message):
    """E-mail para o endereço configurado em SiteSettings (se houver)."""
    to = SiteSettings.load().email
    if not to:
        return
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to],
        fail_silently=True,
    )


def notify_lead(lead):
    ref = f" sobre {lead.property}" if lead.property else ""
    titles = {"LISTING": "Quer anunciar um imóvel", "CONTACT": "Novo contato"}
    subject = f"{titles.get(lead.kind, 'Novo contato')}{ref}"
    notify(
        subject,
        f"Nome: {lead.name}\nEmail: {lead.email}\nTelefone: {lead.phone}\n\n{lead.message}",
    )


def notify_search(search):
    cats = ", ".join(c.name for c in search.categories.all()) or "qualquer categoria"
    notify(
        "Novo cliente procurando imóvel",
        f"Nome: {search.name}\nWhatsApp: {search.whatsapp}\nEmail: {search.email}\n"
        f"Finalidade: {search.get_purpose_display()}\nCategorias: {cats}\n"
        f"Cidade: {search.city or '-'}\nBairros: {search.neighborhoods or '-'}\n"
        f"Preço: {search.min_price or '-'} a {search.max_price or '-'}\n"
        f"Quartos (mín.): {search.min_bedrooms}  Vagas (mín.): {search.min_parking}\n\n"
        f"{search.notes}",
    )
