import json
import urllib.error
from io import BytesIO

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.api.models import ApiKey
from apps.core.features import ALL
from apps.properties import services
from apps.properties.models import Category, City, Feature, Property, PropertyChange, PropertyPhoto
from apps.properties.tests.factories import PropertyFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def api_on(settings, tmp_path):
    settings.SITE_FEATURES = ["brokers", "partners", "owners", "searches", "crm", "api"]
    settings.MEDIA_ROOT = tmp_path
    cache.clear()


@pytest.fixture
def full_key():
    return ApiKey.create_with_key(name="Zapier", permission="FULL")[1]


@pytest.fixture
def leads_key():
    return ApiKey.create_with_key(name="Landing", permission="LEADS")[1]


@pytest.fixture
def house():
    category = Category.objects.get(name="Casa")
    return category


def _send(client, method, url, raw=None, data=None, **extra):
    if raw:
        extra["HTTP_AUTHORIZATION"] = f"Api-Key {raw}"
    if method == "get":
        return client.get(url, data or {}, **extra)
    body = json.dumps(data) if data is not None else None
    return getattr(client, method)(url, body, content_type="application/json", **extra)


def _png(size=(40, 30), fmt="PNG"):
    buf = BytesIO()
    Image.new("RGB", size, "red").save(buf, format=fmt)
    return buf.getvalue()


def _upload(name="foto.png", content=None):
    return SimpleUploadedFile(name, content or _png(), content_type="image/png")


PAYLOAD = {
    "title": "Casa nova na API",
    "category": "Casa",
    "city": "Campinas",
    "state": "SP",
    "neighborhood": "Cambuí",
    "purpose": "SALE",
    "sale_price": "450000.00",
    "bedrooms": 3,
    "features": ["Piscina", "Churrasqueira"],
}
LIST = "api:properties"


def _detail(code):
    return reverse("api:property", args=[code])


# ---------- criação ----------


def test_api_module_is_on_by_default():
    assert "api" in ALL


def test_create_requires_full_key(client, leads_key):
    url = reverse(LIST)
    assert _send(client, "post", url, data=PAYLOAD).status_code == 401
    assert _send(client, "post", url, leads_key, PAYLOAD).status_code == 403
    assert not Property.objects.exists()


def test_create_property_resolves_names_and_defaults_to_draft(client, full_key, house):
    r = _send(client, "post", reverse(LIST), full_key, PAYLOAD)
    assert r.status_code == 201, r.content
    body = r.json()
    assert body["created"] is True and body["status"] == "DRAFT"
    assert body["code"].startswith(house.code_prefix)
    assert body["possible_duplicates"] == []
    prop = Property.objects.get(code=body["code"])
    assert prop.neighborhood.name == "Cambuí" and prop.neighborhood.city.name == "Campinas"
    assert sorted(f.name for f in prop.features.all()) == ["Churrasqueira", "Piscina"]
    row = PropertyChange.objects.get(property=prop)
    assert row.source == "API: Zapier" and row.user is None


def test_create_reuses_existing_city_neighborhood_and_features(client, full_key):
    _send(client, "post", reverse(LIST), full_key, PAYLOAD)
    _send(client, "post", reverse(LIST), full_key, {**PAYLOAD, "title": "Outra", "state": "sp"})
    assert City.objects.filter(name="Campinas").count() == 1
    assert Feature.objects.filter(name="Piscina").count() == 1
    assert Property.objects.count() == 2


def test_category_by_code_prefix(client, full_key, house):
    r = _send(client, "post", reverse(LIST), full_key, {**PAYLOAD, "category": house.code_prefix})
    assert r.status_code == 201 and r.json()["category"] == house.name


def _without(*keys, **changes):
    return {**{k: v for k, v in PAYLOAD.items() if k not in keys}, **changes}


@pytest.mark.parametrize(
    ("data", "field"),
    [
        (_without(category="Inexistente"), "category"),
        (_without("city"), "non_field_errors"),
        (_without("neighborhood"), "non_field_errors"),
        (_without("sale_price"), "sale_price"),
        (_without("state", city="Cidade Inédita"), "state"),
        (_without(purpose="XYZ"), "purpose"),
    ],
)
def test_create_validation_errors(client, full_key, data, field):
    r = _send(client, "post", reverse(LIST), full_key, data)
    assert r.status_code == 400 and field in r.json(), r.json()
    assert not Property.objects.exists()


def test_external_ref_makes_post_idempotent(client, full_key):
    data = {**PAYLOAD, "external_ref": "ERP-1"}
    first = _send(client, "post", reverse(LIST), full_key, data)
    second = _send(client, "post", reverse(LIST), full_key, {**data, "title": "Título novo"})
    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json()["created"] is False and second.json()["code"] == first.json()["code"]
    prop = Property.objects.get()
    assert prop.title == "Título novo" and prop.external_ref == "ERP-1"
    assert PropertyChange.objects.filter(property=prop).count() == 2


def test_duplicates_are_reported_but_do_not_block(client, full_key):
    existing = PropertyFactory(zip_code="13000-000", number="120", complement="")
    data = {**PAYLOAD, "zip_code": "13000000", "number": "120"}
    r = _send(client, "post", reverse(LIST), full_key, data)
    assert r.status_code == 201
    [dup] = r.json()["possible_duplicates"]
    assert dup["code"] == existing.code and dup["match"] == "strong"


# ---------- atualização ----------


def test_patch_updates_fields_features_and_history(client, full_key):
    prop = PropertyFactory(status=Property.Status.DRAFT, sale_price=300000)
    r = _send(
        client,
        "patch",
        _detail(prop.code),
        full_key,
        {"sale_price": "320000.00", "status": "PUBLISHED", "features": ["Piscina"]},
    )
    assert r.status_code == 200, r.content
    prop.refresh_from_db()
    assert str(prop.sale_price) == "320000.00" and prop.status == "PUBLISHED"
    assert prop.review_due > timezone.localdate()
    [row] = PropertyChange.objects.filter(property=prop)
    assert row.source == "API: Zapier"
    assert {c["field"] for c in row.changes} >= {"sale_price", "status", "features"}


def test_patch_rejects_invalid_values_and_unknown_code(client, full_key, leads_key):
    prop = PropertyFactory()
    assert (
        _send(client, "patch", _detail(prop.code), full_key, {"category": "Nada"}).status_code
        == 400
    )
    assert _send(client, "patch", _detail("ZZ999"), full_key, {"title": "x"}).status_code == 404
    assert _send(client, "patch", _detail(prop.code), leads_key, {"title": "x"}).status_code == 403


def test_patch_city_requires_neighborhood(client, full_key):
    prop = PropertyFactory()
    r = _send(client, "patch", _detail(prop.code), full_key, {"city": "Santos", "state": "SP"})
    assert r.status_code == 400 and "neighborhood" in r.json()


# ---------- fotos ----------


def _photos_url(code):
    return reverse("api:property-photos", args=[code])


def test_upload_photo_first_is_cover(client, full_key):
    prop = PropertyFactory()
    url = _photos_url(prop.code)
    auth = {"HTTP_AUTHORIZATION": f"Api-Key {full_key}"}
    one = client.post(url, {"file": _upload(), "caption": "Sala"}, **auth)
    two = client.post(url, {"file": _upload("b.png")}, **auth)
    assert one.status_code == two.status_code == 201, one.content
    assert one.json()["is_cover"] is True and two.json()["is_cover"] is False
    photos = list(prop.photos.all())
    assert [p.caption for p in photos] == ["Sala", ""] and [p.order for p in photos] == [0, 1]
    assert PropertyChange.objects.filter(property=prop, source="API: Zapier").count() == 2


def test_upload_rejects_non_image_and_oversize(client, full_key, monkeypatch):
    prop = PropertyFactory()
    auth = {"HTTP_AUTHORIZATION": f"Api-Key {full_key}"}
    bad = SimpleUploadedFile("x.png", b"not an image", content_type="image/png")
    assert client.post(_photos_url(prop.code), {"file": bad}, **auth).status_code == 400
    monkeypatch.setattr(services, "MAX_PHOTO_BYTES", 100)
    big = _upload(content=_png((300, 300)))
    r = client.post(_photos_url(prop.code), {"file": big}, **auth)
    assert r.status_code == 400 and "10 MB" in json.dumps(r.json())
    assert not prop.photos.exists()


def test_upload_rejects_unsupported_format(client, full_key):
    prop = PropertyFactory()
    tiff = SimpleUploadedFile("x.tif", _png(fmt="TIFF"), content_type="image/tiff")
    r = client.post(
        _photos_url(prop.code), {"file": tiff}, HTTP_AUTHORIZATION=f"Api-Key {full_key}"
    )
    assert r.status_code == 400 and "Formato" in json.dumps(r.json(), ensure_ascii=False)


def test_photo_requires_exactly_one_source(client, full_key):
    prop = PropertyFactory()
    r = _send(client, "post", _photos_url(prop.code), full_key, {})
    assert r.status_code == 400


def test_photo_by_url(client, full_key, monkeypatch):
    prop = PropertyFactory()
    monkeypatch.setattr(services, "fetch_image_bytes", lambda url: _png())
    r = _send(
        client, "post", _photos_url(prop.code), full_key, {"url": "https://cdn.exemplo.com/a.png"}
    )
    assert r.status_code == 201 and prop.photos.count() == 1


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/a.png",
        "http://10.0.0.5/a.png",
        "http://192.168.1.1/a.png",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/a.png",
        "http://localhost/a.png",
        "ftp://exemplo.com/a.png",
        "file:///etc/passwd",
    ],
)
def test_url_to_internal_or_non_http_hosts_is_refused(client, full_key, url):
    prop = PropertyFactory()
    r = _send(client, "post", _photos_url(prop.code), full_key, {"url": url})
    assert r.status_code == 400
    assert not prop.photos.exists()


def test_redirect_to_private_address_is_refused(monkeypatch):
    def getaddrinfo(host, port):
        ip = "93.184.216.34" if host == "cdn.exemplo.com" else "127.0.0.1"
        return [(2, 1, 6, "", (ip, port))]

    class Opener:
        def open(self, request, timeout):
            raise urllib.error.HTTPError(
                request.full_url, 302, "Found", {"Location": "http://interno.local/x"}, None
            )

    monkeypatch.setattr(services.socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(services.urllib.request, "build_opener", lambda *a: Opener())
    with pytest.raises(ValidationError):
        services.fetch_image_bytes("https://cdn.exemplo.com/a.png")


def test_too_many_redirects_are_refused(monkeypatch):
    class Opener:
        def open(self, request, timeout):
            raise urllib.error.HTTPError(
                request.full_url, 301, "Moved", {"Location": "https://cdn.exemplo.com/b"}, None
            )

    monkeypatch.setattr(
        services.socket, "getaddrinfo", lambda h, p: [(2, 1, 6, "", ("93.184.216.34", p))]
    )
    monkeypatch.setattr(services.urllib.request, "build_opener", lambda *a: Opener())
    with pytest.raises(ValidationError, match="Redirecionamentos"):
        services.fetch_image_bytes("https://cdn.exemplo.com/a")


def test_delete_photo_moves_cover_and_checks_ownership(client, full_key):
    prop, other = PropertyFactory(), PropertyFactory()
    first = services.add_photo(prop, upload=_upload())
    second = services.add_photo(prop, upload=_upload("b.png"))
    foreign = services.add_photo(other, upload=_upload("c.png"))
    url = reverse("api:property-photo", args=[prop.code, first.pk])
    assert _send(client, "delete", url, full_key).status_code == 204
    second.refresh_from_db()
    assert second.is_cover and prop.photos.count() == 1
    missing = reverse("api:property-photo", args=[prop.code, foreign.pk])
    assert _send(client, "delete", missing, full_key).status_code == 404
    assert PropertyPhoto.objects.filter(pk=foreign.pk).exists()


def test_photo_delete_requires_full_key(client, leads_key):
    prop = PropertyFactory()
    photo = services.add_photo(prop, upload=_upload())
    url = reverse("api:property-photo", args=[prop.code, photo.pk])
    assert _send(client, "delete", url, leads_key).status_code == 403


def test_schema_documents_write_endpoints(client):
    paths = client.get(reverse("api:schema") + "?format=json").content.decode()
    assert "/api/v1/properties/{code}/photos/" in paths
    assert "/api/v1/properties/{code}/photos/{photo_id}/" in paths
