"""Histórico campo a campo do imóvel (painel, ações em lote e, depois, API/importação)."""

from decimal import Decimal

from django.db import models
from django.utils.translation import gettext as _

from .models import Property, PropertyChange

SKIP = {"id"}
MONEY = {"sale_price", "rent_price", "condo_fee", "iptu"}
EMPTY = "—"


def format_brl(value):
    return "R$ " + f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _tracked_fields():
    return [f for f in Property._meta.concrete_fields if f.editable and f.name not in SKIP]


def _format(field, prop):
    value = getattr(prop, field.name)
    if value in (None, ""):
        return EMPTY
    if field.name in MONEY and isinstance(value, (Decimal, int, float)):
        return format_brl(Decimal(str(value)))
    if isinstance(value, bool):
        return _("Sim") if value else _("Não")
    if field.choices:
        return str(getattr(prop, f"get_{field.name}_display")())
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, models.Model):
        return str(value)
    text = str(value)
    return text if len(text) <= 80 else text[:77] + "…"


def snapshot(prop):
    """{campo: (rótulo, valor legível)} do imóvel salvo; inclui comodidades e nº de fotos."""
    data = {f.name: (str(f.verbose_name), _format(f, prop)) for f in _tracked_fields()}
    if prop.pk:
        features = ", ".join(sorted(prop.features.values_list("name", flat=True)))
        data["features"] = (_("Comodidades"), features or EMPTY)
        data["photos"] = (_("Fotos"), str(prop.photos.count()))
    return data


def diff(before, after):
    return [
        {
            "field": name,
            "label": label,
            "old": before[name][1] if name in before else EMPTY,
            "new": new,
        }
        for name, (label, new) in after.items()
        if (before.get(name) or (None, EMPTY))[1] != new
    ]


def record_changes(prop, before, after, user=None, source="Painel"):
    """Grava uma linha de histórico se algo mudou. Devolve a linha (ou None)."""
    changes = diff(before, after)
    if not changes:
        return None
    return PropertyChange.objects.create(
        property=prop,
        user=user if getattr(user, "pk", None) else None,
        source=source,
        changes=changes,
    )


def record_created(prop, user=None, source="Painel"):
    return PropertyChange.objects.create(
        property=prop,
        user=user if getattr(user, "pk", None) else None,
        source=source,
        changes=[{"field": "created", "label": _("Imóvel"), "old": EMPTY, "new": _("cadastrado")}],
    )


def append_changes(row, prop, before, after, user=None, source="Painel"):
    """Junta mudanças tardias (comodidades/fotos) à linha já gravada, ou cria uma nova."""
    changes = diff(before, after)
    if not changes:
        return row
    if row is None:
        return PropertyChange.objects.create(
            property=prop,
            user=user if getattr(user, "pk", None) else None,
            source=source,
            changes=changes,
        )
    row.changes = [*row.changes, *changes]
    row.save(update_fields=["changes"])
    return row
