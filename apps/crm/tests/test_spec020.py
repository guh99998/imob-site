from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.crm import services
from apps.crm.models import Client, FollowUp, Interaction, normalize_phone
from apps.leads.models import Lead, PropertySearch
from apps.people import roles
from apps.people.models import Broker
from apps.properties.tests.factories import PropertyFactory

pytestmark = pytest.mark.django_db
User = get_user_model()
PHONE = "(11) 91234-5678"


# ---------- normalização e casamento ----------


@pytest.mark.parametrize(
    "raw,key",
    [
        ("(11) 91234-5678", "11912345678"),
        ("+55 11 91234-5678", "11912345678"),
        ("5511912345678", "11912345678"),
        ("(11) 3123-4567", "1131234567"),
        ("12345", ""),
        ("", ""),
        (None, ""),
    ],
)
def test_normalize_phone(raw, key):
    assert normalize_phone(raw) == key


def test_match_by_phone_in_any_format_then_by_email():
    first, created = services.get_or_create_client(name="Ana", phone=PHONE, email="Ana@X.com")
    assert created
    same_phone, created = services.get_or_create_client(name="Outro", phone="+55 11 912345678")
    assert not created and same_phone == first
    same_email, created = services.get_or_create_client(name="Ana", email="ana@x.COM")
    assert not created and same_email == first
    assert Client.objects.count() == 1


def test_match_only_fills_missing_data():
    client, _ = services.get_or_create_client(name="Ana", email="ana@x.com")
    services.get_or_create_client(name="Ana", phone=PHONE, email="ana@x.com")
    client.refresh_from_db()
    assert client.whatsapp == PHONE and client.phone_key == "11912345678"
    assert client.name == "Ana"
    services.get_or_create_client(name="Ana", phone="(21) 98888-7777", email="ana@x.com")
    client.refresh_from_db()
    assert client.whatsapp == PHONE  # não sobrescreve


def test_invalid_phone_is_not_stored_and_does_not_match():
    a, _ = services.get_or_create_client(name="A", phone="123")
    b, _ = services.get_or_create_client(name="B", phone="123")
    assert a != b and a.whatsapp == ""


def test_module_off_returns_none():
    with override_settings(SITE_FEATURES=["searches"]):
        assert services.get_or_create_client(name="Ana", phone=PHONE) == (None, False)
    assert Client.objects.count() == 0


def test_anonymized_client_does_not_match():
    client, _ = services.get_or_create_client(name="Ana", phone=PHONE, email="ana@x.com")
    services.anonymize(client)
    again, created = services.get_or_create_client(name="Ana", phone=PHONE, email="ana@x.com")
    assert created and again != client


def test_model_clean_rejects_duplicate_and_bad_phone():
    Client.objects.create(name="Ana", whatsapp=PHONE)
    with pytest.raises(ValidationError) as exc:
        Client(name="Bia", whatsapp="11 91234 5678").clean()
    assert "já é do cliente Ana" in str(exc.value)
    with pytest.raises(ValidationError):
        Client(name="Bia", whatsapp="12").clean()
    Client(name="Bia", whatsapp="").clean()  # vazio é permitido


def test_followup_done_sets_timestamp():
    client = Client.objects.create(name="Ana")
    f = FollowUp.objects.create(client=client, done=True)
    assert f.done_at
    f.done = False
    f.save()
    assert f.done_at is None


# ---------- captação pelas views públicas ----------


def _lead_post(client, prop, **data):
    payload = {
        "name": "Maria",
        "email": "maria@example.com",
        "phone": PHONE,
        "message": "Quero visitar",
        **data,
    }
    return client.post(reverse("leads:create", args=[prop.slug]), payload)


def test_property_message_creates_client_and_timeline(client):
    broker = Broker.objects.create(name="Marina")
    prop = PropertyFactory(broker=broker)
    assert _lead_post(client, prop).status_code == 200
    lead = Lead.objects.get()
    crm = Client.objects.get()
    assert lead.client == crm
    assert (crm.source, crm.broker, crm.stage) == ("SITE", broker, "NEW")
    note = Interaction.objects.get()
    assert note.client == crm and note.property == prop and "Quero visitar" in note.text


def test_second_message_reuses_client(client):
    prop = PropertyFactory()
    _lead_post(client, prop)
    _lead_post(client, prop, email="outro@example.com", phone="+55 11 912345678")
    assert Client.objects.count() == 1 and Lead.objects.count() == 2
    assert Interaction.objects.count() == 2


def test_listing_and_contact_pages_set_source(client):
    data = {"name": "Joana", "email": "j@example.com", "phone": "", "message": "Tenho um imóvel"}
    client.post(reverse("core:advertise"), data)
    assert Client.objects.get().source == "LISTING"
    client.post(reverse("core:contact"), {**data, "name": "Rui", "email": "rui@example.com"})
    assert Client.objects.get(name="Rui").source == "SITE"


def test_search_creates_client_with_interest(client):
    r = client.post(
        reverse("leads:search"),
        {
            "name": "Lucas",
            "whatsapp": PHONE,
            "purpose": "RENT",
            "max_price": "R$ 3.500,00",
            "notes": "Perto do metrô",
            "lgpd_consent": "on",
        },
    )
    assert r.status_code == 200
    crm = Client.objects.get()
    assert (crm.source, crm.purpose, crm.max_price) == ("SEARCH", "RENT", 3500)
    assert crm.lgpd_consent and crm.lgpd_consent_at
    assert PropertySearch.objects.get().client == crm
    assert "Perto do metrô" in Interaction.objects.get().text


def test_crm_failure_never_loses_the_lead(client, monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("falhou")

    monkeypatch.setattr(services, "get_or_create_client", boom)
    prop = PropertyFactory()
    assert _lead_post(client, prop).status_code == 200
    assert Lead.objects.count() == 1 and Client.objects.count() == 0


# ---------- LGPD ----------


def test_anonymize_clears_personal_data_everywhere(client):
    prop = PropertyFactory()
    _lead_post(client, prop)
    crm = Client.objects.get()
    crm.notes, crm.tags = "VIP", "vip"
    crm.save()
    services.anonymize(crm)
    crm.refresh_from_db()
    assert crm.name == services.ANON_NAME and crm.anonymized_at
    assert not (crm.whatsapp or crm.email or crm.tags or crm.notes or crm.phone_key)
    lead = Lead.objects.get()
    assert lead.name == services.ANON_NAME and not (lead.phone or lead.message)
    assert lead.email == services.ANON_EMAIL
    assert Interaction.objects.get().text == ""


# ---------- painel ----------


def _make_user(role, name):
    user = User.objects.create_user(name, password="pw")
    roles.apply_role(user, role)
    return user


def test_admin_pages_render(admin_client):
    crm, _ = services.get_or_create_client(name="Ana", phone=PHONE, email="ana@x.com")
    FollowUp.objects.create(client=crm, due_date=timezone.localdate() - timedelta(days=1))
    for name, args in [
        ("admin:crm_client_changelist", []),
        ("admin:crm_client_change", [crm.pk]),
        ("admin:crm_client_add", []),
        ("admin:crm_followup_changelist", []),
    ]:
        r = admin_client.get(reverse(name, args=args))
        assert r.status_code == 200, name
    html = admin_client.get(reverse("admin:crm_client_changelist")).content.decode()
    assert "atrasado" in html and "Ana" in html
    change = admin_client.get(reverse("admin:crm_client_change", args=[crm.pk])).content.decode()
    assert reverse("admin:crm_client_matching_detail", args=[crm.pk]) in change


def test_admin_stage_action_and_assign_to_me(admin_client, admin_user):
    crm, _ = services.get_or_create_client(name="Ana", phone=PHONE)
    url = reverse("admin:crm_client_changelist")
    admin_client.post(url, {"action": "move_to_visit", "_selected_action": [crm.pk]})
    crm.refresh_from_db()
    assert crm.stage == Client.Stage.VISIT
    r = admin_client.post(
        url, {"action": "assign_to_me", "_selected_action": [crm.pk]}, follow=True
    )
    assert "não está ligado a um corretor" in r.content.decode()
    broker = Broker.objects.create(name="Admin", user=admin_user)
    admin_client.post(url, {"action": "assign_to_me", "_selected_action": [crm.pk]})
    crm.refresh_from_db()
    assert crm.broker == broker


def test_admin_matching_redirects_with_interest(admin_client):
    crm = Client.objects.create(name="Ana", purpose="RENT", max_price=3000)
    r = admin_client.get(reverse("admin:crm_client_matching_detail", args=[crm.pk]))
    assert r.status_code == 302
    assert "purpose__in=RENT%2CBOTH" in r["Location"] and "rent_price__lte=3000" in r["Location"]


def test_admin_anonymize_action(admin_client):
    crm, _ = services.get_or_create_client(name="Ana", phone=PHONE)
    admin_client.post(
        reverse("admin:crm_client_changelist"),
        {"action": "anonymize_clients", "_selected_action": [crm.pk]},
    )
    crm.refresh_from_db()
    assert crm.anonymized_at and crm.name == services.ANON_NAME


def test_admin_followup_mark_done(admin_client):
    crm = Client.objects.create(name="Ana")
    f = FollowUp.objects.create(client=crm)
    admin_client.post(
        reverse("admin:crm_followup_changelist"),
        {"action": "mark_done", "_selected_action": [f.pk]},
    )
    f.refresh_from_db()
    assert f.done and f.done_at


def test_inline_sets_author_and_broker(admin_client, admin_user):
    broker = Broker.objects.create(name="Marina")
    crm = Client.objects.create(name="Ana", broker=broker)
    data = {
        "name": "Ana",
        "whatsapp": "",
        "email": "",
        "source": "OTHER",
        "broker": broker.pk,
        "stage": "NEW",
        "tags": "",
        "notes": "",
        "interactions-TOTAL_FORMS": "1",
        "interactions-INITIAL_FORMS": "0",
        "interactions-MIN_NUM_FORMS": "0",
        "interactions-MAX_NUM_FORMS": "1000",
        "interactions-0-kind": "CALL",
        "interactions-0-happened_at_0": "2026-10-20",
        "interactions-0-happened_at_1": "10:00:00",
        "interactions-0-text": "Liguei",
        "followups-TOTAL_FORMS": "1",
        "followups-INITIAL_FORMS": "0",
        "followups-MIN_NUM_FORMS": "0",
        "followups-MAX_NUM_FORMS": "1000",
        "followups-0-due_date": "2026-10-30",
        "followups-0-note": "Retornar",
    }
    r = admin_client.post(reverse("admin:crm_client_change", args=[crm.pk]), data)
    assert r.status_code == 302, r.content.decode()[:500]
    assert Interaction.objects.get().author == admin_user
    assert FollowUp.objects.get().broker == broker
    crm.refresh_from_db()
    assert crm.updated_by == admin_user


def test_broker_sees_only_own_clients(client):
    user = _make_user(roles.BROKER, "corretor")
    mine = Broker.objects.create(name="Eu", user=user)
    other = Broker.objects.create(name="Outro")
    a = Client.objects.create(name="Do corretor", broker=mine)
    Client.objects.create(name="De outro", broker=other)
    FollowUp.objects.create(client=a)
    FollowUp.objects.create(client=Client.objects.get(name="De outro"))
    client.force_login(user)
    html = client.get(reverse("admin:crm_client_changelist")).content.decode()
    assert "Do corretor" in html and "De outro" not in html
    html = client.get(reverse("admin:crm_followup_changelist")).content.decode()
    assert "Do corretor" in html and "De outro" not in html


def test_broker_cannot_delete_or_anonymize():
    user = _make_user(roles.BROKER, "corretor")
    assert user.has_perm("crm.add_client") and user.has_perm("crm.change_followup")
    assert not user.has_perm("crm.delete_client")
    assert _make_user(roles.CLERK, "atendente").has_perm("crm.change_client")
    assert _make_user(roles.MANAGER, "gerente").has_perm("crm.delete_client")


def test_dashboard_and_sidebar_show_followups(admin_client):
    crm = Client.objects.create(name="Cliente Atrasado")
    FollowUp.objects.create(
        client=crm, due_date=timezone.localdate() - timedelta(days=2), note="Ligar já"
    )
    FollowUp.objects.create(client=crm, due_date=timezone.localdate(), note="Hoje também")
    html = admin_client.get(reverse("admin:index")).content.decode()
    assert "Retornos de hoje e atrasados" in html
    assert "Cliente Atrasado" in html and "Atrasado" in html
    assert "Retornos atrasados" in html and "Retornos hoje" in html


def test_dashboard_hides_crm_when_off(admin_client):
    with override_settings(SITE_FEATURES=["searches"]):
        html = admin_client.get(reverse("admin:index")).content.decode()
    assert "Retornos de hoje e atrasados" not in html


def test_seed_demo_creates_clients(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    call_command("seed_demo")
    assert Client.objects.count() == 3
    assert FollowUp.objects.filter(due_date__lt=timezone.localdate()).count() == 1
    call_command("seed_demo")
    assert Client.objects.count() == 3
