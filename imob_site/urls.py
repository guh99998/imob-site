from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from apps.properties.sitemaps import LandingSitemap, PropertySitemap, StaticSitemap

sitemaps = {"static": StaticSitemap, "landings": LandingSitemap, "properties": PropertySitemap}


urlpatterns = [
    path("admin/", admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("api/", include("apps.api.urls")),
    path("imoveis/", include("apps.properties.urls")),
    path("", include("apps.leads.urls")),
    path("", include("apps.core.urls")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
