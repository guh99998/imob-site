from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import PUBLIC_STATUSES, Property


class PropertySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Property.objects.published()

    def lastmod(self, obj):
        return obj.updated_at


class LandingSitemap(Sitemap):
    """Landings por categoria e por categoria+cidade que têm imóveis públicos."""

    changefreq = "weekly"
    priority = 0.6

    def items(self):
        pairs = (
            Property.objects.filter(status__in=PUBLIC_STATUSES)
            .values_list("purpose", "category__slug", "neighborhood__city__slug")
            .distinct()
        )
        urls = set()
        for purpose, cat, city in pairs:
            kinds = {"SALE": ["comprar"], "RENT": ["alugar"], "BOTH": ["comprar", "alugar"]}[
                purpose
            ]
            for kind in kinds:
                urls.add(reverse("core:landing", args=[kind, cat]))
                urls.add(reverse("core:landing_city", args=[kind, cat, city]))
        return sorted(urls)

    def location(self, item):
        return item


class StaticSitemap(Sitemap):
    priority = 0.5

    def items(self):
        return ["core:home", "properties:list", "core:advertise", "core:contact", "core:privacy"]

    def location(self, item):
        return reverse(item)
