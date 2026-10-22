from django.urls import path, re_path
from django.views.generic import TemplateView

from apps.properties import views as property_views

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("anuncie/", views.advertise, name="advertise"),
    path("contato/", views.contact, name="contact"),
    path("politica-de-privacidade/", views.privacy, name="privacy"),
    re_path(
        r"^(?P<kind>comprar|alugar)/(?P<category>[-\w]+)/$",
        property_views.landing,
        name="landing",
    ),
    re_path(
        r"^(?P<kind>comprar|alugar)/(?P<category>[-\w]+)/(?P<city>[-\w]+)/$",
        property_views.landing,
        name="landing_city",
    ),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots",
    ),
]
