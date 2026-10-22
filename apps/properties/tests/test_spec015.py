import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.core.models import SiteSettings
from apps.people.models import Broker
from apps.properties.models import Property

from .factories import CategoryFactory, NeighborhoodFactory, PropertyFactory

pytestmark = pytest.mark.django_db


def image(name):
    buf = io.BytesIO()
    Image.new("RGB", (800, 600), "blue").save(buf, format="JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


def test_code_search_redirects_to_property(client):
    prop = PropertyFactory()
    r = client.get(reverse("properties:list"), {"code": prop.code.lower()})
    assert r.status_code == 302 and r.url == prop.get_absolute_url()


def test_code_search_not_found_and_sold_hidden(client):
    sold = PropertyFactory(status=Property.Status.SOLD)
    r = client.get(reverse("properties:list"), {"code": sold.code})
    assert r.status_code == 200
    assert "Não encontramos" in r.content.decode()


def test_price_filter_accepts_formatted_values(client):
    cheap = PropertyFactory(purpose="SALE", sale_price=400000)
    PropertyFactory(purpose="SALE", sale_price=900000)
    r = client.get(
        reverse("properties:list"),
        {"purpose": "SALE", "min_price": "R$ 300.000,00", "max_price": "R$ 500.000"},
    )
    assert {p.pk for p in r.context["page"]} == {cheap.pk}


def test_home_has_listing_form_neighborhood_and_code_search(client):
    html = client.get("/").content.decode()
    assert 'id="contact-box"' in html and 'action="/anuncie/"' in html
    assert 'name="neighborhood"' in html and 'name="min_price"' in html
    assert 'name="code"' in html


def test_header_links_to_property_search(client):
    html = client.get("/imoveis/").content.decode()
    assert "Procuro um imóvel" in html.split("</header>")[0]


def test_max_featured_defaults_to_three():
    assert SiteSettings.load().max_featured == 3


def test_bulk_photo_upload(admin_client):
    prop = PropertyFactory()
    url = reverse("admin:properties_property_change", args=[prop.pk])
    form = admin_client.get(url).context["adminform"].form
    data = {k: v for k, v in form.initial.items() if v is not None and k != "features"}
    data.update(
        {
            "category": prop.category_id,
            "neighborhood": prop.neighborhood_id,
            "sale_price": str(prop.sale_price),
            "photos-TOTAL_FORMS": 0,
            "photos-INITIAL_FORMS": 0,
            "photos-MIN_NUM_FORMS": 0,
            "photos-MAX_NUM_FORMS": 1000,
            "bulk_photos": [image("a.jpg"), image("b.jpg"), image("c.jpg")],
        }
    )
    r = admin_client.post(url, data)
    assert r.status_code == 302, r.context["adminform"].form.errors if r.context else r
    photos = list(prop.photos.order_by("order"))
    assert len(photos) == 3
    assert [p.order for p in photos] == [0, 1, 2]
    assert photos[0].is_cover and not photos[1].is_cover


def test_person_view_properties_shortcut(admin_client):
    broker = Broker.objects.create(name="Fulana")
    mine = PropertyFactory(broker=broker)
    PropertyFactory()
    changelist = admin_client.get(reverse("admin:people_broker_changelist")).content.decode()
    assert f"broker__id__exact={broker.pk}" in changelist
    r = admin_client.get(reverse("admin:people_broker_view_properties_action", args=[broker.pk]))
    assert r.status_code == 302
    r = admin_client.get(r.url)
    assert [p.pk for p in r.context["cl"].result_list] == [mine.pk]


def test_admin_add_still_works_with_bulk_field(admin_client):
    data = {
        "title": "Sem fotos",
        "category": CategoryFactory().pk,
        "status": "DRAFT",
        "purpose": "SALE",
        "sale_price": "100000",
        "neighborhood": NeighborhoodFactory().pk,
        "bedrooms": 1,
        "suites": 0,
        "bathrooms": 1,
        "parking_spaces": 0,
        "source": "OWN",
        "photos-TOTAL_FORMS": 0,
        "photos-INITIAL_FORMS": 0,
        "photos-MIN_NUM_FORMS": 0,
        "photos-MAX_NUM_FORMS": 1000,
    }
    assert admin_client.post(reverse("admin:properties_property_add"), data).status_code == 302
