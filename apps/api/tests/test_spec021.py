import json

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from apps.api.models import ApiKey
from apps.crm.models import Client, Interaction
from apps.leads.models import Lead
from apps.people import roles
from apps.properties.tests.factories import PropertyFactory

pytestmark = pytest.mark.django_db
PHONE = "(11) 91234-5678"


@pytest.fixture(autouse=True)
def api_on(settings):
    settings.SITE_FEATURES = ["brokers", "partners", "owners", "searches", "crm", "api"]
    cache.clear()


@pytest.fixture
def full_key():
    return ApiKey.create_with_key(name="Zapier", permission="FULL", source="PORTAL")


@pytest.fixture
def leads_key():
    return ApiKey.create_with_key(name="Landing", permission="LEADS")


def call(client, method, name, raw=None, *args, data=None, **extra):
    if raw:
        extra["HTTP_AUTHORIZATION"] = f"Api-Key {raw}"
    url = reverse(name, args=args)
    if method == "get":
        return client.get(url, data or {}, **extra)
    body = json.dumps(data) if data is not None else None
    return getattr(client, method)(url, body, content_type="application/json", **extra)


# ---------- chaves e autenticação ----------


def test_key_is_hashed_and_shown_only_once():
    key, raw = ApiKey.create_with_key(name="X")
    assert raw.startswith("imob_") and raw not in (key.key_hash, key.prefix)
    assert len(key.key_hash) == 64 and key.prefix == raw[:12]
    assert ApiKey.lookup(raw) == key
    assert ApiKey.lookup(raw[:-1] + ("a" if raw[-1] != "a" else "b")) is None
    assert ApiKey.lookup("lixo") is None


@pytest.mark.parametrize(
    "header",
    [None, "Api-Key", "Api-Key errada", "Api-Key a b", "Bearer abc"],
)
def test_missing_or_bad_credentials_are_401(client, header):
    extra = {"HTTP_AUTHORIZATION": header} if header else {}
    r = client.get(reverse("api:properties"), **extra)
    assert r.status_code == 401
    assert r["WWW-Authenticate"] == "Api-Key"


def test_inactive_key_is_401_and_last_use_is_tracked(client, full_key):
    key, raw = full_key
    assert call(client, "get", "api:properties", raw).status_code == 200
    key.refresh_from_db()
    assert key.last_used_at
    key.is_active = False
    key.save()
    assert call(client, "get", "api:properties", raw).status_code == 401


def test_module_off_is_404_everywhere(client, full_key, settings):
    _key, raw = full_key
    settings.SITE_FEATURES = ["crm"]
    for name in ("api:properties", "api:clients", "api:schema", "api:docs"):
        assert call(client, "get", name, raw).status_code == 404, name
    assert call(client, "get", "api:properties", "chave-ruim").status_code == 404


def test_leads_key_cannot_use_client_routes(client, leads_key):
    _key, raw = leads_key
    crm = Client.objects.create(name="Ana")
    assert call(client, "get", "api:clients", raw).status_code == 403
    assert call(client, "get", "api:client", raw, crm.pk).status_code == 403
    assert call(client, "get", "api:interactions", raw, crm.pk).status_code == 403
    assert call(client, "get", "api:properties", raw).status_code == 200


def test_throttle_per_key(client, full_key, leads_key, settings):
    settings.API_THROTTLE_RATE = "2/min"
    _a, raw = full_key
    _b, other = leads_key
    codes = [call(client, "get", "api:properties", raw).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    assert call(client, "get", "api:properties", other).status_code == 200  # outra chave


# ---------- POST /leads/ ----------


def _lead(client, raw, **data):
    payload = {"name": "Maria", "email": "maria@example.com", "phone": PHONE, "message": "Oi"}
    payload.update(data)
    return call(client, "post", "api:leads", raw, data=payload)


def test_lead_creates_lead_client_and_timeline(client, leads_key, mailoutbox):
    key, raw = leads_key
    prop = PropertyFactory()
    r = _lead(client, raw, property=prop.code.lower(), message="Quero visitar")
    assert r.status_code == 201
    lead = Lead.objects.get()
    crm = Client.objects.get()
    assert r.json() == {"id": lead.pk, "client": crm.pk}
    assert (lead.kind, lead.property) == ("PROPERTY", prop)
    assert (crm.source, crm.whatsapp) == ("API", PHONE)
    assert Interaction.objects.get().property == prop


def test_lead_uses_key_source_and_listing_kind(client, full_key):
    _key, raw = full_key
    _lead(client, raw)
    assert Client.objects.get().source == "PORTAL"
    _lead(client, raw, name="Joana", email="j@example.com", phone="", kind="LISTING")
    assert Client.objects.get(name="Joana").source == "LISTING"


def test_lead_dedupes_client_by_phone_or_email(client, leads_key):
    _key, raw = leads_key
    _lead(client, raw)
    _lead(client, raw, email="outro@example.com", phone="+55 11 912345678")
    _lead(client, raw, email="MARIA@example.com", phone="")
    assert Client.objects.count() == 1 and Lead.objects.count() == 3


def test_lead_with_only_phone_or_only_email(client, leads_key):
    _key, raw = leads_key
    assert _lead(client, raw, email="").status_code == 201
    assert _lead(client, raw, name="B", phone="", email="b@example.com").status_code == 201


@pytest.mark.parametrize(
    "changes",
    [
        {"email": "", "phone": ""},
        {"email": "", "phone": "123"},
        {"email": "nao-e-email"},
        {"name": ""},
        {"message": ""},
        {"kind": "OUTRO"},
        {"property": "XX999"},
    ],
)
def test_lead_validation(client, leads_key, changes):
    _key, raw = leads_key
    assert _lead(client, raw, **changes).status_code == 400
    assert Lead.objects.count() == 0


def test_lead_for_unpublished_property_is_rejected(client, leads_key):
    _key, raw = leads_key
    draft = PropertyFactory(status="DRAFT")
    assert _lead(client, raw, property=draft.code).status_code == 400


def test_lead_accepts_form_encoding(client, leads_key):
    _key, raw = leads_key
    r = client.post(
        reverse("api:leads"),
        "name=Form&email=f%40example.com&message=Oi",
        content_type="application/x-www-form-urlencoded",
        HTTP_AUTHORIZATION=f"Api-Key {raw}",
    )
    assert r.status_code == 201


def test_lead_works_with_crm_off(client, leads_key, settings):
    settings.SITE_FEATURES = ["api"]
    _key, raw = leads_key
    r = _lead(client, raw)
    assert r.status_code == 201 and r.json()["client"] is None
    assert Lead.objects.count() == 1 and Client.objects.count() == 0


# ---------- clientes ----------


def test_client_list_filters_and_hides_anonymized(client, full_key):
    _key, raw = full_key
    Client.objects.create(name="Ana Souza", whatsapp=PHONE, stage="NEW", source="SITE")
    Client.objects.create(name="Bruno", email="bruno@x.com", stage="VISIT", source="API")
    Client.objects.create(name="Fantasma", anonymized_at=timezone.now())
    data = call(client, "get", "api:clients", raw).json()
    assert data["count"] == 2 and {c["name"] for c in data["results"]} == {"Ana Souza", "Bruno"}

    def names(**params):
        return {
            c["name"]
            for c in call(client, "get", "api:clients", raw, data=params).json()["results"]
        }

    assert names(stage="VISIT") == {"Bruno"}
    assert names(source="SITE") == {"Ana Souza"}
    assert names(q="91234") == {"Ana Souza"}
    assert names(q="bruno@") == {"Bruno"}
    assert names(stage="INVALIDA") == {"Ana Souza", "Bruno"}


def test_client_pagination(client, full_key):
    _key, raw = full_key
    for i in range(3):
        Client.objects.create(name=f"C{i}")
    data = call(client, "get", "api:clients", raw, data={"page_size": 2}).json()
    assert len(data["results"]) == 2 and data["next"]


def test_client_detail_patch(client, full_key):
    _key, raw = full_key
    crm = Client.objects.create(name="Ana", whatsapp=PHONE, source="SITE")
    r = call(
        client,
        "patch",
        "api:client",
        raw,
        crm.pk,
        data={"stage": "PROPOSAL", "tags": "vip", "source": "PORTAL", "name": "Ana Maria"},
    )
    assert r.status_code == 200
    crm.refresh_from_db()
    assert (crm.stage, crm.tags, crm.name) == ("PROPOSAL", "vip", "Ana Maria")
    assert crm.source == "SITE"  # origem não muda pela API
    assert call(client, "put", "api:client", raw, crm.pk, data={"name": "x"}).status_code == 405
    assert call(client, "delete", "api:client", raw, crm.pk).status_code == 405


def test_client_patch_validation(client, full_key):
    _key, raw = full_key
    Client.objects.create(name="Outra", whatsapp=PHONE)
    crm = Client.objects.create(name="Ana")
    clash = call(client, "patch", "api:client", raw, crm.pk, data={"whatsapp": "11 91234 5678"})
    assert clash.status_code == 400 and "Outra" not in clash.content.decode()
    assert (
        call(client, "patch", "api:client", raw, crm.pk, data={"whatsapp": "12"}).status_code == 400
    )
    assert call(client, "patch", "api:client", raw, crm.pk, data={"stage": "X"}).status_code == 400
    ok = call(client, "patch", "api:client", raw, crm.pk, data={"whatsapp": "(21) 98888-7777"})
    assert ok.status_code == 200
    crm.refresh_from_db()
    assert crm.phone_key == "21988887777"


def test_anonymized_client_is_404(client, full_key):
    _key, raw = full_key
    crm = Client.objects.create(name="X", anonymized_at=timezone.now())
    assert call(client, "get", "api:client", raw, crm.pk).status_code == 404
    assert call(client, "get", "api:interactions", raw, crm.pk).status_code == 404


def test_interactions_create_and_list(client, full_key):
    _key, raw = full_key
    crm = Client.objects.create(name="Ana")
    prop = PropertyFactory()
    r = call(
        client,
        "post",
        "api:interactions",
        raw,
        crm.pk,
        data={"kind": "VISIT", "text": "Visitou", "property": prop.code},
    )
    assert r.status_code == 201 and r.json()["property"] == prop.code
    rows = call(client, "get", "api:interactions", raw, crm.pk).json()["results"]
    assert [(i["kind"], i["text"], i["property"]) for i in rows] == [
        ("VISIT", "Visitou", prop.code)
    ]
    assert Interaction.objects.get().client == crm
    bad = call(
        client, "post", "api:interactions", raw, crm.pk, data={"kind": "NOTE", "property": "ZZ"}
    )
    assert bad.status_code == 400


# ---------- imóveis ----------


def test_properties_only_published_with_filters(client, full_key):
    _key, raw = full_key
    house = PropertyFactory(bedrooms=3, show_address=False, street="Rua Secreta", number="99")
    PropertyFactory(bedrooms=1)
    PropertyFactory(status="DRAFT")
    PropertyFactory(status="SOLD")
    data = call(client, "get", "api:properties", raw).json()
    assert data["count"] == 2
    only = call(client, "get", "api:properties", raw, data={"bedrooms": 3}).json()
    assert [p["code"] for p in only["results"]] == [house.code]
    item = only["results"][0]
    assert "Rua Secreta" not in json.dumps(item) and item["url"].endswith(house.get_absolute_url())
    assert item["photos"] == [] and item["features"] == []


def test_property_detail_by_code(client, full_key):
    _key, raw = full_key
    prop = PropertyFactory()
    r = call(client, "get", "api:property", raw, prop.code.lower())
    assert r.status_code == 200 and r.json()["code"] == prop.code
    draft = PropertyFactory(status="DRAFT")
    assert call(client, "get", "api:property", raw, draft.code).status_code == 404


# ---------- documentação ----------


def test_docs_and_schema_are_public_and_describe_the_key(client):
    assert client.get(reverse("api:docs")).status_code == 200
    r = client.get(reverse("api:schema"))
    assert r.status_code == 200
    schema = r.content.decode()
    assert "/api/v1/leads/" in schema and "ApiKeyAuth" in schema and "Api-Key" in schema


# ---------- painel ----------


def test_admin_creates_key_and_shows_it_once(admin_client, admin_user):
    r = admin_client.post(
        reverse("admin:api_apikey_add"),
        {"name": "Portal Y", "permission": "FULL", "source": "PORTAL", "is_active": "on"},
        follow=True,
    )
    assert r.status_code == 200
    key = ApiKey.objects.get()
    assert key.created_by == admin_user and key.is_active
    page = r.content.decode()
    raw = page.split("select-all")[1].split(">")[1].split("<")[0]
    assert raw.startswith(key.prefix) and ApiKey.lookup(raw) == key
    again = admin_client.get(reverse("admin:api_apikey_change", args=[key.pk])).content.decode()
    assert raw not in again and key.key_hash not in again
    listing = admin_client.get(reverse("admin:api_apikey_changelist")).content.decode()
    assert raw not in listing and "Portal Y" in listing


def test_admin_can_deactivate_key(admin_client):
    key, raw = ApiKey.create_with_key(name="X")
    admin_client.post(
        reverse("admin:api_apikey_change", args=[key.pk]),
        {"name": "X", "permission": "LEADS", "source": "API"},
    )
    key.refresh_from_db()
    assert not key.is_active and ApiKey.lookup(raw) is None


def test_only_administrator_manages_keys():
    from django.contrib.auth import get_user_model

    User = get_user_model()
    for role, expected in [(roles.ADMIN, True), (roles.MANAGER, False), (roles.BROKER, False)]:
        user = User.objects.create_user(role.lower(), password="pw")
        roles.apply_role(user, role)
        assert user.has_perm("api.view_apikey") is expected, role


def test_admin_hidden_when_module_off(admin_client, settings):
    settings.SITE_FEATURES = ["crm"]
    assert admin_client.get(reverse("admin:api_apikey_changelist")).status_code == 403
