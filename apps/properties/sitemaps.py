from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Property


class PropertySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Property.objects.published()

    def lastmod(self, obj):
        return obj.updated_at


class StaticSitemap(Sitemap):
    priority = 0.5

    def items(self):
        return ["core:home", "properties:list"]

    def location(self, item):
        return reverse(item)
