from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.crm.models import Client, Interaction
from apps.people import roles
from apps.people.models import Broker
from apps.properties.tests.factories import PropertyFactory

from .test_spec020 import _make_user

pytestmark = pytest.mark.django_db


def _change(client_obj):
    return reverse("admin:crm_client_change", args=[client_obj.pk])


def _add_url(client_obj):
    return reverse("admin:crm_client_add_interaction", args=[client_obj.pk])


def test_timeline_newest_first_with_author_and_property(admin_client, admin_user):
    crm = Client.objects.create(name="Ana")
    prop = PropertyFactory()
    now = timezone.now()
    Interaction.objects.create(
        client=crm, text="primeira", happened_at=now - timedelta(days=2), author=admin_user
    )
    Interaction.objects.create(client=crm, text="segunda", happened_at=now, property=prop)
    html = admin_client.get(_change(crm)).content.decode()
    assert html.index("segunda") < html.index("primeira")
    assert prop.code in html
    assert "Registrar interação" in html


def test_add_interaction_sets_author_and_redirects(admin_client, admin_user):
    crm = Client.objects.create(name="Ana")
    r = admin_client.post(
        _add_url(crm),
        {"kind": "CALL", "happened_at": "2026-10-20T10:00", "text": "Liguei"},
    )
    assert r.status_code == 302 and r.url == _change(crm)
    i = Interaction.objects.get()
    assert i.author == admin_user and i.client == crm and i.kind == "CALL"


def test_invalid_interaction_is_not_saved(admin_client):
    crm = Client.objects.create(name="Ana")
    admin_client.post(_add_url(crm), {"kind": "CALL", "happened_at": "2026-10-20T10:00"})
    assert not Interaction.objects.exists()


def test_get_does_not_create(admin_client):
    crm = Client.objects.create(name="Ana")
    assert admin_client.get(_add_url(crm)).status_code == 302
    assert not Interaction.objects.exists()


def test_text_is_escaped(admin_client):
    crm = Client.objects.create(name="Ana")
    Interaction.objects.create(client=crm, text="<script>alert(1)</script>")
    html = admin_client.get(_change(crm)).content.decode()
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_broker_cannot_add_to_other_clients(client):
    user = _make_user(roles.BROKER, "corretor")
    Broker.objects.create(name="Eu", user=user)
    other = Client.objects.create(name="De outro", broker=Broker.objects.create(name="Outro"))
    client.force_login(user)
    r = client.post(
        _add_url(other), {"kind": "NOTE", "happened_at": "2026-10-20T10:00", "text": "x"}
    )
    assert r.status_code == 404
    assert not Interaction.objects.exists()


def test_broker_adds_to_own_client(client):
    user = _make_user(roles.BROKER, "corretor")
    mine = Client.objects.create(name="Meu", broker=Broker.objects.create(name="Eu", user=user))
    client.force_login(user)
    client.post(_add_url(mine), {"kind": "NOTE", "happened_at": "2026-10-20T10:00", "text": "x"})
    assert Interaction.objects.get().author == user


def test_anonymized_client_has_no_form_and_rejects_post(admin_client):
    crm = Client.objects.create(name="Anon", anonymized_at=timezone.now())
    assert "Registrar interação" not in admin_client.get(_change(crm)).content.decode()
    r = admin_client.post(
        _add_url(crm), {"kind": "NOTE", "happened_at": "2026-10-20T10:00", "text": "x"}
    )
    assert r.status_code == 403
    assert not Interaction.objects.exists()


def test_edit_and_delete_links_follow_permissions(admin_client, client):
    crm = Client.objects.create(name="Ana", broker=None)
    i = Interaction.objects.create(client=crm, text="algo")
    html = admin_client.get(_change(crm)).content.decode()
    assert reverse("admin:crm_interaction_change", args=[i.pk]) in html
    assert reverse("admin:crm_interaction_delete", args=[i.pk]) in html


def test_delete_returns_to_client(admin_client):
    crm = Client.objects.create(name="Ana")
    i = Interaction.objects.create(client=crm, text="algo")
    r = admin_client.post(reverse("admin:crm_interaction_delete", args=[i.pk]), {"post": "yes"})
    assert r.status_code == 302 and r.url == _change(crm)
    assert not Interaction.objects.exists()
