import pytest
from django.core import mail
from django.core.cache import cache
from django.urls import reverse

from apps.core.models import SiteSettings
from apps.leads.models import Lead
from apps.properties.tests.factories import PropertyFactory

pytestmark = pytest.mark.django_db

DATA = {"name": "Maria", "email": "maria@example.com", "phone": "11999", "message": "Quero visitar"}


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()


def url(prop):
    return reverse("leads:create", args=[prop.slug])


def test_create_lead_sends_email(client):
    s = SiteSettings.load()
    s.email = "corretor@example.com"
    s.save()
    prop = PropertyFactory()
    r = client.post(url(prop), DATA, HTTP_HX_REQUEST="true")
    assert r.status_code == 200
    lead = Lead.objects.get()
    assert lead.property == prop and lead.status == Lead.Status.NEW
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ["corretor@example.com"]


def test_invalid_lead_shows_errors(client):
    prop = PropertyFactory()
    r = client.post(url(prop), {**DATA, "email": "invalido"})
    assert not Lead.objects.exists()
    assert "Insira um endereço de email válido" in r.content.decode()


def test_honeypot_blocks_bots(client):
    prop = PropertyFactory()
    client.post(url(prop), {**DATA, "website": "http://spam"})
    assert not Lead.objects.exists()


def test_rate_limit(client):
    prop = PropertyFactory()
    for _ in range(5):
        client.post(url(prop), DATA)
    r = client.post(url(prop), DATA)
    assert r.status_code == 429
    assert Lead.objects.count() == 5


def test_get_not_allowed(client):
    assert client.get(url(PropertyFactory())).status_code == 405


def test_draft_property_rejected(client):
    prop = PropertyFactory(status="DRAFT")
    assert client.post(url(prop), DATA).status_code == 404
