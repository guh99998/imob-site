"""Captação automática: tudo que entra pelo site cai no CRM com a mesma regra de casamento."""

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.features import enabled

from .models import Client, Interaction, normalize_phone

logger = logging.getLogger(__name__)

ANON_NAME = "Cliente anonimizado"
ANON_EMAIL = "anonimizado@example.invalid"


def get_or_create_client(*, name, phone="", email="", source=Client.Source.SITE, **extra):
    """Casa por WhatsApp e, se não achar, por email. Devolve (cliente, criado).

    Cliente achado só é completado (nada que já existe é sobrescrito). `(None, False)` quando o
    módulo CRM está desligado.
    """
    if not enabled("crm"):
        return None, False
    key = normalize_phone(phone)
    email = (email or "").strip().lower()
    client = None
    if key:
        client = Client.objects.filter(phone_key=key).first()
    if client is None and email:
        client = Client.objects.filter(email__iexact=email).first()
    if client is not None:
        _fill_missing(client, phone if key else "", email, extra)
        return client, False
    data = {k: v for k, v in extra.items() if v not in (None, "")}
    client = Client(
        name=(name or "").strip()[:150] or "Sem nome",
        whatsapp=phone.strip() if key else "",
        email=email,
        source=source,
        **data,
    )
    try:
        with transaction.atomic():
            client.save()
    except IntegrityError:  # outro envio criou o mesmo WhatsApp no meio tempo
        existing = Client.objects.filter(phone_key=key).first()
        if existing is None:
            raise
        return existing, False
    return client, True


def _fill_missing(client, phone, email, extra):
    changed = []
    if phone and not client.whatsapp:
        client.whatsapp = phone.strip()
        changed.append("whatsapp")
    if email and not client.email:
        client.email = email
        changed.append("email")
    for field, value in extra.items():
        if value not in (None, "") and not getattr(client, field):
            setattr(client, field, value)
            changed.append(field)
    if changed:
        client.save(update_fields=[*changed, "phone_key", "updated_at"])


def register_lead(lead, source=None):
    """Liga uma mensagem (site ou API) a um cliente. `source` troca a origem padrão."""
    try:
        listing = lead.kind == lead.Kind.LISTING
        client, _created = get_or_create_client(
            name=lead.name,
            phone=lead.phone,
            email=lead.email,
            source=source or (Client.Source.LISTING if listing else Client.Source.SITE),
            broker=lead.property.broker if lead.property_id else None,
        )
        if client is None:
            return None
        lead.client = client
        lead.save(update_fields=["client"])
        Interaction.objects.create(
            client=client,
            kind=Interaction.Kind.NOTE,
            property=lead.property,
            text=f"{lead.get_kind_display()}: {lead.message}",
        )
        return client
    except Exception:
        logger.exception("Falha ao ligar a mensagem %s ao CRM", lead.pk)
        return None


def register_search(search):
    """Liga uma procura ("Procuro um imóvel") a um cliente, com o interesse informado."""
    try:
        client, _created = get_or_create_client(
            name=search.name,
            phone=search.whatsapp,
            email=search.email,
            source=Client.Source.SEARCH,
            purpose=search.purpose,
            max_price=search.max_price,
            min_price=search.min_price,
            lgpd_consent=search.lgpd_consent,
        )
        if client is None:
            return None
        search.client = client
        search.save(update_fields=["client"])
        cats = ", ".join(c.name for c in search.categories.all()) or "qualquer tipo"
        where = search.city.name if search.city_id else "qualquer cidade"
        text = f"Procura: {search.get_purpose_display()} · {cats} · {where}"
        if search.max_price:
            text += f" · até R$ {search.max_price:,.2f}"
        if search.notes:
            text += f"\n{search.notes}"
        Interaction.objects.create(client=client, kind=Interaction.Kind.NOTE, text=text)
        return client
    except Exception:
        logger.exception("Falha ao ligar a procura %s ao CRM", search.pk)
        return None


@transaction.atomic
def move_stage(client, stage, user=None):
    """Muda a etapa do funil e deixa o registro na linha do tempo. Devolve False se não mudou."""
    stage = Client.Stage(stage)
    if client.stage == stage:
        return False
    old = Client.Stage(client.stage)
    client.stage = stage
    client.updated_by = user
    client.save(update_fields=["stage", "updated_by", "updated_at"])
    Interaction.objects.create(
        client=client,
        kind=Interaction.Kind.NOTE,
        text=f"Etapa: {old.label} → {stage.label}",
        author=user,
    )
    return True


def anonymize(client):
    """LGPD: apaga os dados pessoais do cliente e dos contatos/procuras ligados a ele."""
    client.name = ANON_NAME
    client.whatsapp = client.email = client.tags = client.notes = ""
    client.anonymized_at = timezone.now()
    client.save()
    client.interactions.update(text="")
    client.leads.update(name=ANON_NAME, email=ANON_EMAIL, phone="", message="")
    client.searches.update(name=ANON_NAME, whatsapp="", email="", notes="")
    return client
