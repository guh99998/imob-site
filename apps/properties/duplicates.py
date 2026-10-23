"""Detecção de imóveis duplicados (aviso no painel e varredura do estoque)."""

import re
import unicodedata
from decimal import Decimal

from django.db.models import Q

from .models import DuplicateDismissal, Property

AREA_TOLERANCE = Decimal("0.05")
PRICE_TOLERANCE = Decimal("0.10")
STRONG, PROBABLE = "strong", "probable"
LEVEL_LABELS = {STRONG: "mesmo endereço", PROBABLE: "características parecidas"}
_APT = re.compile(r"(?<![a-z])(apartamento|apto|ap)(?![a-z])")


def _plain(text):
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def normalize_complement(text):
    """ "Apto. 12", "apto12" e "Apartamento 12" viram "ap12"."""
    return re.sub(r"[^a-z0-9]", "", _APT.sub("ap", _plain(text)))


def normalize_number(text):
    value = re.sub(r"[^a-z0-9]", "", _plain(text))
    return value.lstrip("0") or value


def zip_variants(zip_code):
    digits = re.sub(r"\D", "", zip_code or "")
    if not digits:
        return []
    return [digits, f"{digits[:5]}-{digits[5:]}"] if len(digits) == 8 else [digits]


def _candidates(prop):
    """Imóveis ainda no estoque (vendido/alugado não contam) menos ele mesmo."""
    return Property.objects.exclude(pk=prop.pk).exclude(
        status__in=[Property.Status.SOLD, Property.Status.RENTED]
    )


def _dismissed_ids(prop):
    pairs = DuplicateDismissal.objects.filter(Q(property_a=prop) | Q(property_b=prop))
    ids = set()
    for a, b in pairs.values_list("property_a_id", "property_b_id"):
        ids.add(b if a == prop.pk else a)
    return ids


def _strong(prop):
    variants = zip_variants(prop.zip_code)
    number = normalize_number(prop.number)
    if not variants or not number:
        return []
    complement = normalize_complement(prop.complement)
    return [
        other
        for other in _candidates(prop).filter(zip_code__in=variants)
        if normalize_number(other.number) == number
        and normalize_complement(other.complement) == complement
    ]


def _probable(prop):
    if not prop.area_total:
        return []
    prices = Q()
    if prop.sale_price:
        prices |= Q(
            sale_price__gte=prop.sale_price * (1 - PRICE_TOLERANCE),
            sale_price__lte=prop.sale_price * (1 + PRICE_TOLERANCE),
        )
    if prop.rent_price:
        prices |= Q(
            rent_price__gte=prop.rent_price * (1 - PRICE_TOLERANCE),
            rent_price__lte=prop.rent_price * (1 + PRICE_TOLERANCE),
        )
    if not prices:
        return []
    return list(
        _candidates(prop)
        .filter(
            neighborhood_id=prop.neighborhood_id,
            category_id=prop.category_id,
            bedrooms=prop.bedrooms,
            area_total__gte=prop.area_total * (1 - AREA_TOLERANCE),
            area_total__lte=prop.area_total * (1 + AREA_TOLERANCE),
        )
        .filter(prices)
    )


def find_duplicates(prop):
    """[(imóvel, nível)] com os fortes primeiro. Pares dispensados não aparecem."""
    dismissed = _dismissed_ids(prop)
    found, seen = [], set()
    for level, others in ((STRONG, _strong(prop)), (PROBABLE, _probable(prop))):
        for other in others:
            if other.pk not in seen and other.pk not in dismissed:
                seen.add(other.pk)
                found.append((other, level))
    return found


def _set_hint(prop, value):
    Property.objects.filter(pk=prop.pk).update(duplicate_hint=value)
    prop.duplicate_hint = value


def refresh_hints(prop):
    """Recalcula o aviso do imóvel e marca os parecidos. Devolve os duplicados possíveis."""
    matches = find_duplicates(prop)
    _set_hint(prop, bool(matches))
    Property.objects.filter(pk__in=[m.pk for m, _level in matches]).update(duplicate_hint=True)
    return matches


def dismiss(user, properties):
    """Marca como "não duplicado" os pares atuais dos imóveis. Devolve quantos pares."""
    total, touched = 0, {}
    for prop in properties:
        for other, _level in find_duplicates(prop):
            a, b = sorted((prop.pk, other.pk))
            _pair, created = DuplicateDismissal.objects.get_or_create(
                property_a_id=a, property_b_id=b, defaults={"created_by": user}
            )
            total += created
            touched[prop.pk], touched[other.pk] = prop, other
    for prop in touched.values():
        _set_hint(prop, bool(find_duplicates(prop)))
    return total


def scan_all():
    """Recalcula o estoque inteiro. Devolve os pares [(a, b, nível)] sem repetir."""
    pairs, flagged = {}, set()
    for prop in Property.objects.exclude(
        status__in=[Property.Status.SOLD, Property.Status.RENTED]
    ).select_related("neighborhood", "category"):
        for other, level in find_duplicates(prop):
            key = tuple(sorted((prop.pk, other.pk)))
            if key not in pairs or level == STRONG:
                pairs[key] = (prop, other, level) if prop.pk < other.pk else (other, prop, level)
            flagged.update(key)
    Property.objects.update(duplicate_hint=False)
    Property.objects.filter(pk__in=flagged).update(duplicate_hint=True)
    return sorted(pairs.values(), key=lambda p: (p[2] != STRONG, p[0].pk))
