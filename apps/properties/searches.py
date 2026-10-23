"""Registro das buscas do site para o "Mais procurados" (sem dado pessoal)."""

import re
from datetime import timedelta
from urllib.parse import urlencode

from django.db import IntegrityError
from django.db.models import F
from django.utils import timezone

from apps.core.widgets import parse_br_decimal

from .models import Property, SearchQuery

POPULAR_DAYS = 30
POPULAR_MIN_COUNT = 3
POPULAR_LIMIT = 6
_BOT = re.compile(r"bot|crawl|spider|slurp|curl|wget|python-requests|headless|monitor", re.I)
_NUMBERS = ("bedrooms", "parking_spaces", "min_area", "max_area")


def is_bot(request):
    agent = request.META.get("HTTP_USER_AGENT", "")
    return not agent or bool(_BOT.search(agent))


def normalize(cleaned):
    """{filtro: texto} só com os filtros conhecidos e valores limpos (ordenação não conta)."""
    params = {}
    if cleaned.get("purpose"):
        params["purpose"] = cleaned["purpose"]
    if cleaned.get("category"):
        params["category"] = cleaned["category"].slug
    if cleaned.get("city"):
        params["city"] = str(cleaned["city"].pk)
    if cleaned.get("neighborhood"):
        params["neighborhood"] = str(cleaned["neighborhood"].pk)
    for name in ("min_price", "max_price"):
        try:
            price = parse_br_decimal(cleaned.get(name))
        except Exception:
            price = None
        if price is not None and price > 0:
            params[name] = str(int(price))
    for name in _NUMBERS:
        value = cleaned.get(name)
        if value is not None and value > 0:
            params[name] = str(int(value))
    return dict(sorted(params.items()))


def _brl(value):
    return "R$ " + f"{int(value):,}".replace(",", ".")


def label_for(cleaned, params):
    category = cleaned.get("category")
    subject = category.name if category else "Imóveis"
    purpose = {
        Property.Purpose.SALE: "à venda",
        Property.Purpose.RENT: "para alugar",
    }.get(params.get("purpose"), "")
    where = ""
    if cleaned.get("neighborhood"):
        where = f"em {cleaned['neighborhood'].name}"
    elif cleaned.get("city"):
        where = f"em {cleaned['city'].name}"
    head = " ".join(p for p in (subject, purpose, where) if p)
    extras = []
    if "bedrooms" in params:
        extras.append(f"{params['bedrooms']}+ quartos")
    if "parking_spaces" in params:
        extras.append(f"{params['parking_spaces']}+ vagas")
    if "min_area" in params:
        extras.append(f"{params['min_area']}+ m²")
    if "max_area" in params:
        extras.append(f"até {params['max_area']} m²")
    if "min_price" in params:
        extras.append(f"a partir de {_brl(params['min_price'])}")
    if "max_price" in params:
        extras.append(f"até {_brl(params['max_price'])}")
    return " · ".join([head, *extras])[:200]


def record(request, filterset, results):
    """Soma uma busca. Ignora robôs, páginas 2+, formulário inválido e busca sem filtro."""
    if request.GET.get("page") not in (None, "", "1") or is_bot(request):
        return
    if not filterset.is_bound or not filterset.form.is_valid():
        return
    cleaned = filterset.form.cleaned_data
    params = normalize(cleaned)
    if not params:
        return
    key = urlencode(params)
    fields = {
        "count": F("count") + 1,
        "results": results,
        "last_searched_at": timezone.now(),
        "label": label_for(cleaned, params),
    }
    if SearchQuery.objects.filter(key=key).update(**fields):
        return
    try:
        SearchQuery.objects.create(
            key=key,
            label=fields["label"],
            count=1,
            results=results,
            last_searched_at=fields["last_searched_at"],
        )
    except IntegrityError:  # outra requisição criou no meio tempo
        SearchQuery.objects.filter(key=key).update(**fields)


def popular():
    since = timezone.now() - timedelta(days=POPULAR_DAYS)
    return list(
        SearchQuery.objects.filter(
            last_searched_at__gte=since, count__gte=POPULAR_MIN_COUNT, results__gt=0
        )[:POPULAR_LIMIT]
    )
