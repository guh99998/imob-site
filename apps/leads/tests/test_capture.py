from decimal import Decimal
from urllib.parse import urlencode

import pytest
from django.core import mail
from django.urls import reverse

from apps.core.models import SiteSettings
from apps.leads.models import Lead, PropertySearch
from apps.properties.models import Category
from apps.properties.tests.factories import CityFactory, NeighborhoodFactory, PropertyFactory

pytestmark = pytest.mark.django_db

SEARCH = {
    "name": "João",
    "whatsapp": "(11) 90000-1111",
    "email": "joao@example.com",
    "purpose": "SALE",
    "max_price": "R$ 900.000,00",
    "notes": "Perto de escola",
    "lgpd_consent": "on",
}
CONTACT = {"name": "Maria", "email": "m@example.com", "phone": "11999", "message": "Olá"}


@pytest.fixture
def site_email():
    site = SiteSettings.load()
    site.email = "corretor@example.com"
    site.save()


def test_search_form_creates_record_and_emails(client, site_email):
    house = Category.objects.get(slug="casa")
    city = CityFactory()
    r = client.post(reverse("leads:search"), {**SEARCH, "category": house.pk, "city": city.pk})
    assert r.status_code == 200 and "Recebemos seu pedido" in r.content.decode()
    s = PropertySearch.objects.get()
    assert s.max_price == Decimal("900000.00") and s.min_price is None
    assert list(s.categories.all()) == [house] and s.city == city and s.lgpd_consent
    assert len(mail.outbox) == 1 and "procurando" in mail.outbox[0].subject


def test_search_htmx_returns_partial(client):
    r = client.post(reverse("leads:search"), SEARCH, HTTP_HX_REQUEST="true")
    html = r.content.decode()
    assert "<html" not in html and "Recebemos seu pedido" in html


def test_search_requires_consent_and_valid_phone(client):
    data = {k: v for k, v in SEARCH.items() if k != "lgpd_consent"}
    r = client.post(reverse("leads:search"), data)
    assert not PropertySearch.objects.exists() and "aceite" in r.content.decode()
    r = client.post(reverse("leads:search"), {**SEARCH, "whatsapp": "123"})
    assert not PropertySearch.objects.exists() and "DDD" in r.content.decode()
    r = client.post(reverse("leads:search"), {**SEARCH, "max_price": "abc"})
    assert not PropertySearch.objects.exists()


def test_search_honeypot_and_rate_limit(client):
    r = client.post(reverse("leads:search"), {**SEARCH, "website": "http://spam"})
    assert not PropertySearch.objects.exists() and r.status_code == 200
    for _ in range(5):
        client.post(reverse("leads:search"), SEARCH)
    r = client.post(reverse("leads:search"), SEARCH)
    assert r.status_code == 429 and PropertySearch.objects.count() == 4


def test_search_page_renders_without_js(client):
    r = client.get(reverse("leads:search"))
    html = r.content.decode()
    assert r.status_code == 200 and "<form" in html and 'method="post"' in html
    assert "lgpd_consent" in html
    # versão enxuta: sem checkboxes de categoria, bairros, quartos e vagas
    for removed in ("min_bedrooms", "min_parking", "neighborhoods", 'type="checkbox" name="categ'):
        assert removed not in html


def test_search_feature_flag_off(client, settings):
    settings.SITE_FEATURES = ["brokers"]
    assert client.get(reverse("leads:search")).status_code == 404
    assert "quero-um-imovel" not in client.get("/").content.decode()


def test_search_link_on_home_and_footer(client):
    assert "/quero-um-imovel/" in client.get("/").content.decode()


@pytest.mark.parametrize(
    "name,kind", [("core:contact", Lead.Kind.CONTACT), ("core:advertise", Lead.Kind.LISTING)]
)
def test_contact_and_advertise_create_leads_with_kind(client, name, kind, site_email):
    page = client.get(reverse(name))
    assert page.status_code == 200 and "<form" in page.content.decode()
    r = client.post(reverse(name), CONTACT)
    assert r.status_code == 200 and "Mensagem enviada" in r.content.decode()
    lead = Lead.objects.get()
    assert lead.kind == kind and lead.property is None
    assert len(mail.outbox) == 1


def test_contact_htmx_partial_and_rate_limit(client):
    r = client.post(reverse("core:contact"), CONTACT, HTTP_HX_REQUEST="true")
    assert "<html" not in r.content.decode()
    for _ in range(4):
        client.post(reverse("core:contact"), CONTACT)
    assert client.post(reverse("core:contact"), CONTACT).status_code == 429


def test_property_lead_keeps_default_kind(client):
    prop = PropertyFactory()
    client.post(reverse("leads:create", args=[prop.slug]), CONTACT)
    assert Lead.objects.get().kind == Lead.Kind.PROPERTY


def test_matching_properties_link_filters_admin_list(admin_client):
    house = Category.objects.get(slug="casa")
    nb = NeighborhoodFactory()
    match = PropertyFactory(
        category=house, neighborhood=nb, sale_price=500000, bedrooms=3, parking_spaces=2
    )
    PropertyFactory(category=house, neighborhood=nb, sale_price=2000000, bedrooms=3)
    PropertyFactory(category=house, neighborhood=nb, sale_price=500000, bedrooms=1)
    PropertyFactory(category=Category.objects.get(slug="terreno"), sale_price=500000, bedrooms=3)
    search = PropertySearch.objects.create(
        name="X",
        whatsapp="11900000000",
        city=nb.city,
        min_price=300000,
        max_price=900000,
        min_bedrooms=2,
        min_parking=1,
    )
    search.categories.add(house)
    assert search.matching_count() == 1
    listing = admin_client.get(reverse("admin:leads_propertysearch_changelist")).content.decode()
    assert "Ver 1 imóvel compatível" in listing
    url = reverse("admin:properties_property_changelist") + "?" + urlencode(search.matching_query())
    r = admin_client.get(url)
    assert r.status_code == 200
    assert [p.pk for p in r.context["cl"].result_list] == [match.pk]


def test_admin_search_mark_contacted_and_dashboard(admin_client):
    s = PropertySearch.objects.create(name="X", whatsapp="11900000000")
    assert admin_client.get(reverse("admin:leads_propertysearch_changelist")).status_code == 200
    assert "Procuras novas" in admin_client.get(reverse("admin:index")).content.decode()
    admin_client.get(reverse("admin:leads_propertysearch_mark_contacted_row", args=[s.pk]))
    s.refresh_from_db()
    assert s.status == PropertySearch.Status.CONTACTED
