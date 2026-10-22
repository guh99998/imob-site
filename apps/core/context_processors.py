from django.core.cache import cache
from django.db.models import Count, Q
from django.urls import reverse

from apps.properties.models import PUBLIC_STATUSES, Category, City

from .models import SiteSettings

CACHE_SECONDS = 120


def _footer_links():
    """Categorias e cidades que têm imóveis públicos (cache curto)."""
    data = cache.get("footer-links")
    if data is None:
        public = Q(properties__status__in=PUBLIC_STATUSES)
        categories = list(
            Category.objects.annotate(n=Count("properties", filter=public))
            .filter(n__gt=0)
            .only("name", "slug")
        )
        cities = list(
            City.objects.annotate(
                n=Count(
                    "neighborhoods__properties",
                    filter=Q(neighborhoods__properties__status__in=PUBLIC_STATUSES),
                )
            )
            .filter(n__gt=0)
            .order_by("-n", "name")[:6]
        )
        data = {"footer_categories": categories, "footer_cities": cities}
        cache.set("footer-links", data, CACHE_SECONDS)
    return data


def site_settings(request):
    return {
        "site": SiteSettings.load(),
        "nav_items": [
            {"label": "Comprar", "url": reverse("properties:list") + "?purpose=SALE"},
            {"label": "Alugar", "url": reverse("properties:list") + "?purpose=RENT"},
            {"label": "Anuncie seu imóvel", "url": reverse("core:advertise")},
            {"label": "Contato", "url": reverse("core:contact")},
        ],
        **_footer_links(),
    }
