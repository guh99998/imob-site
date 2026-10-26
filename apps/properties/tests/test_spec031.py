from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.core.admin_dashboard import dashboard_callback
from apps.core.admin_navigation import pending_reviews_badge
from apps.core.models import SiteSettings
from apps.properties import history, reviews
from apps.properties.models import Property, PropertyChange

from .factories import FeatureFactory, PropertyFactory
from .test_spec030 import _post_data

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    user = get_user_model().objects.create_superuser("admin", "a@a.com", "pw")
    client.force_login(user)
    return client


def _change_data(prop, **over):
    data = _post_data(prop, **over)
    data.update(
        title=prop.title,
        status=prop.status,
        street=prop.street or "Rua A",
        purpose=prop.purpose,
        sale_price="500000,00",
    )
    data.update(over)
    return data


def _change_url(prop):
    return reverse("admin:properties_property_change", args=[prop.pk])


def _with_due(days, **kw):
    prop = PropertyFactory(**kw)
    Property.objects.filter(pk=prop.pk).update(
        review_due=timezone.localdate() + timedelta(days=days)
    )
    return prop


# --- histórico ------------------------------------------------------------------------------


def test_snapshot_diff_formats_values():
    prop = PropertyFactory(sale_price=300000)
    before = history.snapshot(prop)
    prop.sale_price = 320000
    prop.status = Property.Status.RESERVED
    prop.is_featured = True
    changes = {c["field"]: c for c in history.diff(before, history.snapshot(prop))}
    assert changes["sale_price"]["old"] == "R$ 300.000,00"
    assert changes["sale_price"]["new"] == "R$ 320.000,00"
    assert changes["status"]["old"] == "Publicado" and changes["status"]["new"] == "Reservado"
    assert changes["is_featured"]["new"] == "Sim"
    assert "title" not in changes


def test_record_changes_skips_when_nothing_changed():
    prop = PropertyFactory()
    snap = history.snapshot(prop)
    assert history.record_changes(prop, snap, history.snapshot(prop)) is None
    assert not PropertyChange.objects.exists()


def test_admin_edit_records_fields_features_and_photos(admin_client):
    prop = PropertyFactory(title="Antigo")
    feature = FeatureFactory(name="Piscina")
    r = admin_client.post(
        _change_url(prop),
        _change_data(prop, title="Novo título", features=[feature.pk], sale_price="520000,00"),
    )
    assert r.status_code == 302
    row = PropertyChange.objects.get(property=prop)
    assert row.source == "Painel" and row.user.username == "admin"
    fields = {c["field"]: c for c in row.changes}
    assert fields["title"]["old"] == "Antigo" and fields["title"]["new"] == "Novo título"
    assert fields["sale_price"]["new"] == "R$ 520.000,00"
    assert fields["features"]["new"] == "Piscina"
    assert PropertyChange.objects.filter(property=prop).count() == 1


def test_admin_add_records_creation(admin_client):
    base = PropertyFactory(zip_code="11111-111", number="1")
    data = _post_data(base, zip_code="22222-222", number="9")
    r = admin_client.post(reverse("admin:properties_property_add"), data)
    assert r.status_code == 302
    created = Property.objects.exclude(pk=base.pk).get()
    [row] = PropertyChange.objects.filter(property=created)
    assert row.changes[0]["new"] == "cadastrado"


def test_change_page_lists_history(admin_client):
    prop = PropertyFactory()
    PropertyChange.objects.create(
        property=prop,
        source="API: chave",
        changes=[{"field": "title", "label": "título", "old": "A", "new": "B"}],
    )
    html = admin_client.get(_change_url(prop)).content.decode()
    assert "Histórico de alterações" in html and "API: chave" in html and "A → B" in html


def test_bulk_action_records_history_and_schedules_review(admin_client):
    prop = PropertyFactory(status=Property.Status.DRAFT)
    assert prop.review_due is None
    r = admin_client.post(
        reverse("admin:properties_property_changelist"),
        {"action": "publish", "_selected_action": [prop.pk]},
        follow=True,
    )
    assert "publicado(s)" in r.content.decode()
    prop.refresh_from_db()
    assert prop.status == Property.Status.PUBLISHED
    assert prop.review_due == timezone.localdate() + timedelta(days=60)
    row = PropertyChange.objects.get(property=prop)
    assert row.source == "Ação em lote"
    assert any(c["field"] == "status" for c in row.changes)


# --- revisão --------------------------------------------------------------------------------


def test_publish_schedules_review_but_draft_does_not():
    draft = PropertyFactory(status=Property.Status.DRAFT)
    live = PropertyFactory(status=Property.Status.PUBLISHED)
    assert draft.review_due is None
    assert live.review_due == timezone.localdate() + timedelta(days=60)


def test_interval_zero_turns_reviews_off():
    SiteSettings.objects.update_or_create(pk=1, defaults={"review_interval_days": 0})
    assert PropertyFactory().review_due is None


def test_interval_comes_from_settings():
    SiteSettings.objects.update_or_create(pk=1, defaults={"review_interval_days": 15})
    assert PropertyFactory().review_due == timezone.localdate() + timedelta(days=15)


def test_future_manual_date_survives_publishing():
    future = timezone.localdate() + timedelta(days=200)
    prop = PropertyFactory(status=Property.Status.DRAFT, review_due=future)
    prop.status = Property.Status.PUBLISHED
    prop.save()
    assert prop.review_due == future


def test_mark_reviewed_row_and_bulk(admin_client):
    today = timezone.localdate()
    a = _with_due(-3)
    b = _with_due(-1)
    admin_client.get(reverse("admin:properties_property_mark_reviewed_row", args=[a.pk]))
    a.refresh_from_db()
    assert a.review_due == today + timedelta(days=60)
    assert a.last_reviewed_by.username == "admin" and a.last_reviewed_at
    admin_client.post(
        reverse("admin:properties_property_changelist"),
        {"action": "mark_reviewed", "_selected_action": [b.pk]},
    )
    b.refresh_from_db()
    assert b.review_due == today + timedelta(days=60)
    assert PropertyChange.objects.filter(property=b, source="Ação em lote").exists()


def test_pending_only_counts_public_and_due():
    late = _with_due(-1)
    _with_due(30)
    draft = _with_due(-5, status=Property.Status.DRAFT)
    sold = _with_due(-5, status=Property.Status.SOLD)
    assert list(reviews.pending()) == [late]
    assert draft not in reviews.pending() and sold not in reviews.pending()


def test_review_filter_and_column(admin_client):
    late = _with_due(-2, title="Vencido")
    soon = _with_due(3, title="Logo")
    fine = _with_due(40, title="Tranquilo")
    url = reverse("admin:properties_property_changelist")

    def listed(value):
        r = admin_client.get(url, {"review": value})
        return {p.pk for p in r.context["cl"].result_list}

    assert listed("overdue") == {late.pk}
    assert listed("soon") == {soon.pk}
    assert listed("ok") == {fine.pk}
    assert "Vencida" in admin_client.get(url).content.decode()


def test_sidebar_badge_and_dashboard(rf, admin_user):
    _with_due(-1)
    _with_due(-9)
    _with_due(20)
    request = rf.get("/admin/")
    request.user = admin_user
    assert pending_reviews_badge(request) == 2
    context = dashboard_callback(request, {})
    assert {"label": "Revisões pendentes", "value": 2} in [
        {"label": str(n["label"]), "value": n["value"]} for n in context["numbers"]
    ]


def test_scoped_user_badge_counts_only_own(rf, admin_user, monkeypatch):
    mine = _with_due(-1, created_by=admin_user)
    _with_due(-1)
    monkeypatch.setattr("apps.people.scoping.is_scoped", lambda user: True)
    request = rf.get("/admin/")
    request.user = admin_user
    assert pending_reviews_badge(request) == 1
    assert mine.pk


def test_settings_form_has_review_interval(admin_client):
    url = reverse("admin:core_sitesettings_change", args=[SiteSettings.load().pk])
    assert "review_interval_days" in admin_client.get(url).content.decode()
