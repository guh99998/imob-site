from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.crm import services
from apps.crm.models import Client, FollowUp, Interaction
from apps.people import roles
from apps.people.models import Broker

from .test_spec020 import _make_user

pytestmark = pytest.mark.django_db
KANBAN = "admin:crm_client_kanban"


def _stage_url(c):
    return reverse("admin:crm_client_stage", args=[c.pk])


def _age(client_obj, days):
    Client.objects.filter(pk=client_obj.pk).update(updated_at=timezone.now() - timedelta(days=days))


def test_columns_follow_stages(admin_client):
    Client.objects.create(name="Ana", stage="NEW")
    Client.objects.create(name="Beto", stage="VISIT")
    r = admin_client.get(reverse(KANBAN))
    assert r.status_code == 200
    cols = {c["stage"].value: [x["client"].name for x in c["cards"]] for c in r.context["columns"]}
    assert cols["NEW"] == ["Ana"] and cols["VISIT"] == ["Beto"]
    assert list(cols) == Client.Stage.values


def test_closed_columns_show_only_last_30_days(admin_client):
    recent = Client.objects.create(name="Recente", stage="WON")
    old = Client.objects.create(name="Antigo", stage="LOST")
    _age(old, 40)
    html = admin_client.get(reverse(KANBAN)).content.decode()
    assert recent.name in html and old.name not in html
    assert "stage__exact=LOST" in html


def test_anonymized_hidden_and_overdue_marked(admin_client):
    Client.objects.create(name="Anon", anonymized_at=timezone.now())
    late = Client.objects.create(name="Atrasada")
    FollowUp.objects.create(client=late, due_date=timezone.localdate() - timedelta(days=1))
    html = admin_client.get(reverse(KANBAN)).content.decode()
    assert "Anon<" not in html and "(atrasado)" in html


def test_broker_filter(admin_client):
    a = Broker.objects.create(name="A")
    Client.objects.create(name="DoA", broker=a)
    Client.objects.create(name="SemCorretor")
    html = admin_client.get(reverse(KANBAN), {"broker": a.pk}).content.decode()
    assert "DoA" in html and "SemCorretor" not in html


def test_broker_sees_only_own(client):
    user = _make_user(roles.BROKER, "corretor")
    mine = Broker.objects.create(name="Eu", user=user)
    Client.objects.create(name="Meu", broker=mine)
    Client.objects.create(name="Alheio", broker=Broker.objects.create(name="Outro"))
    client.force_login(user)
    html = client.get(reverse(KANBAN)).content.decode()
    assert "Meu" in html and "Alheio" not in html


def test_stage_post_moves_and_logs(admin_client, admin_user):
    c = Client.objects.create(name="Ana", stage="NEW")
    r = admin_client.post(
        _stage_url(c), {"stage": "VISIT"}, headers={"x-requested-with": "XMLHttpRequest"}
    )
    assert r.status_code == 200 and r.json()["moved"]
    c.refresh_from_db()
    assert c.stage == "VISIT" and c.updated_by == admin_user
    note = Interaction.objects.get()
    assert note.text == "Etapa: Novo → Visita agendada" and note.author == admin_user


def test_stage_post_without_js_redirects(admin_client):
    c = Client.objects.create(name="Ana")
    r = admin_client.post(_stage_url(c), {"stage": "PROPOSAL"})
    assert r.status_code == 302 and r.url == reverse(KANBAN)
    c.refresh_from_db()
    assert c.stage == "PROPOSAL"


def test_same_stage_and_invalid_stage_do_nothing(admin_client):
    c = Client.objects.create(name="Ana", stage="NEW")
    admin_client.post(_stage_url(c), {"stage": "NEW"})
    assert not Interaction.objects.exists()
    assert admin_client.post(_stage_url(c), {"stage": "XYZ"}).status_code == 400


def test_stage_post_permissions_and_scope(client):
    broker_user = _make_user(roles.BROKER, "corretor")
    Broker.objects.create(name="Eu", user=broker_user)
    other = Client.objects.create(name="Alheio", broker=Broker.objects.create(name="Outro"))
    client.force_login(broker_user)
    assert client.post(_stage_url(other), {"stage": "WON"}).status_code == 404
    viewer = _make_user(roles.CLERK, "atendente")
    from django.contrib.auth.models import Permission

    viewer.groups.clear()
    viewer.user_permissions.set(Permission.objects.filter(codename="view_client"))
    client.force_login(viewer)
    assert client.get(reverse(KANBAN)).status_code == 200
    assert client.post(_stage_url(other), {"stage": "WON"}).status_code == 403
    other.refresh_from_db()
    assert other.stage == "NEW"


def test_bulk_action_logs_stage_change(admin_client):
    c = Client.objects.create(name="Ana")
    admin_client.post(
        reverse("admin:crm_client_changelist"),
        {"action": "move_to_won", "_selected_action": [c.pk]},
    )
    assert Interaction.objects.get().text == "Etapa: Novo → Fechado"


def test_move_stage_service():
    c = Client.objects.create(name="Ana")
    assert services.move_stage(c, "LOST") and not services.move_stage(c, "LOST")


def test_sidebar_and_dashboard_link(admin_client):
    html = admin_client.get(reverse("admin:index")).content.decode()
    assert reverse(KANBAN) in html
