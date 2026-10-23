from decimal import Decimal

import pytest
from django.contrib import admin
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.management import call_command
from django.urls import reverse

from apps.properties import duplicates
from apps.properties.admin import PropertyAdmin
from apps.properties.models import DuplicateDismissal, Property

from .factories import CategoryFactory, NeighborhoodFactory, PropertyFactory

pytestmark = pytest.mark.django_db

ADDR = {"zip_code": "13000-000", "number": "120", "complement": "Apto 12"}


def addr(**kw):
    return PropertyFactory(**{**ADDR, **kw})


def test_strong_match_ignores_cep_hyphen_case_and_apto_style():
    a = addr()
    b = addr(zip_code="13000000", complement="apto. 12", number=" 120 ")
    assert duplicates.find_duplicates(a) == [(b, duplicates.STRONG)]
    assert duplicates.find_duplicates(b) == [(a, duplicates.STRONG)]


@pytest.mark.parametrize("complement", ["Apartamento 12", "AP12", "apto12", "ap. 12"])
def test_apartment_spellings_are_equal(complement):
    a = addr()
    b = addr(complement=complement)
    assert [m for m, _ in duplicates.find_duplicates(a)] == [b]


@pytest.mark.parametrize(
    "other",
    [
        {"complement": "Apto 13"},
        {"number": "121"},
        {"zip_code": "13000-001"},
        {"zip_code": ""},
    ],
)
def test_different_unit_is_not_strong(other):
    a = addr()
    PropertyFactory(**{**ADDR, **other})
    assert [m for m, lvl in duplicates.find_duplicates(a) if lvl == duplicates.STRONG] == []


def test_needs_zip_and_number():
    a = PropertyFactory(zip_code="", number="")
    PropertyFactory(zip_code="", number="")
    assert duplicates.find_duplicates(a) == []


def test_sold_and_rented_are_ignored():
    a = addr()
    addr(status=Property.Status.SOLD)
    addr(status=Property.Status.RENTED)
    assert duplicates.find_duplicates(a) == []


def test_draft_counts():
    a = addr()
    d = addr(status=Property.Status.DRAFT)
    assert [m for m, _ in duplicates.find_duplicates(a)] == [d]


def _base():
    return PropertyFactory(area_total=Decimal("100"), sale_price=Decimal("500000"), bedrooms=3)


def test_probable_match_within_tolerance():
    a = _base()
    kw = {"neighborhood": a.neighborhood, "category": a.category, "bedrooms": 3}
    near = PropertyFactory(area_total=Decimal("104"), sale_price=Decimal("540000"), **kw)
    assert duplicates.find_duplicates(a) == [(near, duplicates.PROBABLE)]


@pytest.mark.parametrize(
    "changes",
    [
        {"area_total": Decimal("110")},  # área fora de 5%
        {"sale_price": Decimal("600000")},  # preço fora de 10%
        {"bedrooms": 2},
        {"category": "other"},
        {"neighborhood": "other"},
    ],
)
def test_probable_outside_tolerance(changes):
    a = _base()
    kw = {
        "neighborhood": a.neighborhood,
        "category": a.category,
        "bedrooms": 3,
        "area_total": Decimal("100"),
        "sale_price": Decimal("500000"),
    }
    for key, value in changes.items():
        if value == "other":
            value = CategoryFactory() if key == "category" else NeighborhoodFactory()
        kw[key] = value
    PropertyFactory(**kw)
    assert duplicates.find_duplicates(a) == []


def test_probable_needs_area_and_price():
    a = PropertyFactory(area_total=None, sale_price=Decimal("500000"))
    PropertyFactory(
        neighborhood=a.neighborhood, category=a.category, bedrooms=a.bedrooms, area_total=None
    )
    assert duplicates.find_duplicates(a) == []


def test_strong_wins_over_probable():
    a = addr(area_total=Decimal("100"), sale_price=Decimal("500000"))
    b = addr(
        neighborhood=a.neighborhood,
        category=a.category,
        bedrooms=a.bedrooms,
        area_total=Decimal("100"),
        sale_price=Decimal("500000"),
    )
    assert duplicates.find_duplicates(a) == [(b, duplicates.STRONG)]


def test_refresh_hints_flags_both():
    a, b = addr(), addr()
    assert not Property.objects.get(pk=b.pk).duplicate_hint
    duplicates.refresh_hints(b)
    assert Property.objects.get(pk=a.pk).duplicate_hint
    assert Property.objects.get(pk=b.pk).duplicate_hint


def test_dismiss_removes_pair_for_good(admin_user):
    a, b = addr(), addr()
    duplicates.refresh_hints(b)
    assert duplicates.dismiss(admin_user, Property.objects.filter(pk=a.pk)) == 1
    assert duplicates.find_duplicates(a) == [] and duplicates.find_duplicates(b) == []
    assert not Property.objects.get(pk=a.pk).duplicate_hint
    assert not Property.objects.get(pk=b.pk).duplicate_hint
    pair = DuplicateDismissal.objects.get()
    assert pair.property_a_id < pair.property_b_id
    # repetir não duplica o registro
    assert duplicates.dismiss(admin_user, Property.objects.filter(pk=b.pk)) == 0


def _request(rf, user):
    request = rf.post("/")
    request.user = user
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


def test_admin_warning_has_link(rf, admin_user):
    a = addr()
    b = addr()
    request = _request(rf, admin_user)
    PropertyAdmin(Property, admin.site).warn_duplicates(request, b)
    [msg] = list(get_messages(request))
    assert "Possível duplicado de" in str(msg)
    assert reverse("admin:properties_property_change", args=[a.pk]) in str(msg)
    assert "mesmo endereço" in str(msg)


def test_admin_no_warning_without_duplicates(rf, admin_user):
    request = _request(rf, admin_user)
    PropertyAdmin(Property, admin.site).warn_duplicates(request, addr())
    assert list(get_messages(request)) == []


def test_scoped_user_does_not_see_other_properties(rf, admin_user, monkeypatch):
    a = addr(title="Segredo do vizinho")
    b = addr()
    monkeypatch.setattr("apps.properties.admin.is_scoped", lambda user: True)
    request = _request(rf, admin_user)
    PropertyAdmin(Property, admin.site).warn_duplicates(request, b)
    [msg] = list(get_messages(request))
    assert a.code not in str(msg) and "Segredo" not in str(msg) and "parecido" in str(msg)


def test_changelist_badge_filter_and_action(admin_client):
    a, b = addr(), addr()
    duplicates.refresh_hints(b)
    url = reverse("admin:properties_property_changelist")
    html = admin_client.get(url).content.decode()
    assert "Possível" in html
    assert admin_client.get(url + "?duplicate_hint__exact=1").status_code == 200
    r = admin_client.post(
        url,
        {"action": "dismiss_duplicates", "_selected_action": [a.pk]},
        follow=True,
    )
    assert "marcado(s) como não duplicado" in r.content.decode()
    assert DuplicateDismissal.objects.count() == 1
    assert not Property.objects.get(pk=b.pk).duplicate_hint


def test_scan_command(capsys):
    a, b = addr(), addr()
    PropertyFactory()  # sem relação
    Property.objects.update(duplicate_hint=False)
    call_command("find_duplicates")
    out = capsys.readouterr().out
    assert f"{a.code} x {b.code}" in out and "1 par(es)" in out
    assert Property.objects.filter(duplicate_hint=True).count() == 2
    call_command("find_duplicates", "--quiet")
    assert "x" not in capsys.readouterr().out.replace("par(es)", "")


def test_save_model_triggers_warning(rf, admin_user):
    a = addr()
    b = addr()
    request = _request(rf, admin_user)
    PropertyAdmin(Property, admin.site).save_model(request, b, form=None, change=True)
    [msg] = list(get_messages(request))
    assert a.code in str(msg)
    assert Property.objects.get(pk=a.pk).duplicate_hint
