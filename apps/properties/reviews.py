"""Revisão periódica dos anúncios: prazo para conferir se o imóvel publicado ainda está correto."""

from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from .models import PUBLIC_STATUSES, Property

SOON_DAYS = 7


def interval_days():
    from apps.core.models import SiteSettings

    return SiteSettings.load().review_interval_days


def next_due(today=None):
    days = interval_days()
    if not days:
        return None
    return (today or timezone.localdate()) + timedelta(days=days)


def schedule(prop):
    """Ao publicar: define o prazo, sem sobrescrever uma data futura já escolhida."""
    today = timezone.localdate()
    if prop.review_due is None or prop.review_due <= today:
        prop.review_due = next_due(today)


def mark_reviewed(prop, user):
    """Registra a revisão e empurra o prazo (não salva; quem chama salva)."""
    prop.last_reviewed_at = timezone.now()
    prop.last_reviewed_by = user
    prop.review_due = next_due()


def pending(queryset=None, within_days=0):
    """Publicados/reservados com revisão vencida (ou vencendo em `within_days`)."""
    qs = Property.objects.all() if queryset is None else queryset
    limit = timezone.localdate() + timedelta(days=within_days)
    return qs.filter(Q(status__in=PUBLIC_STATUSES) & Q(review_due__lte=limit))
