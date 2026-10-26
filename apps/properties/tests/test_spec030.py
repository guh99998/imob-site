import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.properties import duplicates
from apps.properties.admin import PropertyAdminForm
from apps.properties.models import DuplicateDismissal, Property

from .factories import PropertyFactory

pytestmark = pytest.mark.django_db

ADDR = {"zip_code": "13000-000", "number": "120", "complement": "Apto 12"}


@pytest.fixture
def admin_client(client):
    user = get_user_model().objects.create_superuser("admin", "a@a.com", "pw")
    client.force_login(user)
    return client


def _post_data(existing, **extra):
    """Dados de um cadastro novo com o mesmo endereço de `existing`."""
    data = {
        "title": "Casa nova",
        "category": existing.category_id,
        "purpose": "SALE",
        "status": "DRAFT",
        "neighborhood": existing.neighborhood_id,
        "street": "Rua A",
        "number": existing.number,
        "complement": existing.complement,
        "zip_code": existing.zip_code,
        "sale_price": "300000,00",
        "bedrooms": 2,
        "bathrooms": 1,
        "parking_spaces": 0,
        "suites": 0,
        "photos-TOTAL_FORMS": 0,
        "photos-INITIAL_FORMS": 0,
        "photos-MIN_NUM_FORMS": 0,
        "photos-MAX_NUM_FORMS": 1000,
    }
    data.update(extra)
    return data


def test_find_duplicates_accepts_unsaved_instance():
    existing = PropertyFactory(**ADDR)
    candidate = duplicates.unsaved_from({**ADDR, "category": existing.category})
    assert [(m.pk, lvl) for m, lvl in duplicates.find_duplicates(candidate)] == [
        (existing.pk, duplicates.STRONG)
    ]


def test_check_endpoint_returns_panel_with_cards(admin_client):
    existing = PropertyFactory(**ADDR, title="Casa do Jardim")
    r = admin_client.post(
        reverse("admin:properties_property_check_duplicates"),
        {"zip_code": "13000000", "number": "120", "complement": "apto 12"},
    )
    html = r.content.decode()
    assert r.status_code == 200
    assert "possivelmente duplicado" in html
    assert existing.code in html and "Casa do Jardim" in html
    assert reverse("admin:properties_property_change", args=[existing.pk]) in html
    assert "Não é duplicado" in html


def test_check_endpoint_empty_when_no_duplicate(admin_client):
    PropertyFactory(**ADDR)
    r = admin_client.post(
        reverse("admin:properties_property_check_duplicates"),
        {"zip_code": "99999-999", "number": "1"},
    )
    assert r.status_code == 204


def test_check_endpoint_is_post_only(admin_client):
    assert (
        admin_client.get(reverse("admin:properties_property_check_duplicates")).status_code == 405
    )


def test_check_endpoint_hides_other_properties_from_scoped_user(admin_client, monkeypatch):
    existing = PropertyFactory(**ADDR, title="Segredo do vizinho")
    monkeypatch.setattr("apps.properties.admin.is_scoped", lambda user: True)
    r = admin_client.post(
        reverse("admin:properties_property_check_duplicates"),
        {"zip_code": "13000-000", "number": "120", "complement": "Apto 12"},
    )
    html = r.content.decode()
    assert r.status_code == 200
    assert existing.code not in html and "Segredo" not in html and "parecido" in html


def test_form_blocks_until_confirmed():
    existing = PropertyFactory(**ADDR)
    form = PropertyAdminForm(_post_data(existing))
    assert not form.is_valid()
    assert existing.code in str(form.non_field_errors())

    confirmed = PropertyAdminForm(_post_data(existing, not_duplicate="on"))
    confirmed.is_valid()
    assert existing.code not in str(confirmed.non_field_errors())


def test_form_confirmation_by_ids_must_cover_every_match():
    first = PropertyFactory(**ADDR)
    form = PropertyAdminForm(_post_data(first, not_duplicate=str(first.pk + 999)))
    form.is_valid()
    assert first.code in str(form.non_field_errors())


def test_form_without_duplicate_has_no_error():
    existing = PropertyFactory(**ADDR)
    data = _post_data(existing, zip_code="99999-999", number="7")
    form = PropertyAdminForm(data)
    form.is_valid()
    assert not form.non_field_errors()


def test_add_view_creates_dismissal_and_no_hint(admin_client):
    existing = PropertyFactory(**ADDR)
    r = admin_client.post(
        reverse("admin:properties_property_add"),
        _post_data(existing, not_duplicate=str(existing.pk)),
    )
    assert r.status_code == 302, getattr(r, "context_data", None) and r.context_data["errors"]
    created = Property.objects.exclude(pk=existing.pk).get()
    assert DuplicateDismissal.objects.filter(
        property_a_id=min(created.pk, existing.pk), property_b_id=max(created.pk, existing.pk)
    ).exists()
    created.refresh_from_db()
    existing.refresh_from_db()
    assert not created.duplicate_hint and not existing.duplicate_hint


def test_add_view_without_confirmation_shows_panel_and_saves_nothing(admin_client):
    existing = PropertyFactory(**ADDR)
    r = admin_client.post(reverse("admin:properties_property_add"), _post_data(existing))
    assert r.status_code == 200
    html = r.content.decode()
    assert existing.code in html and "Confirmo que este imóvel não é duplicado" in html
    assert Property.objects.count() == 1


def test_scoped_user_is_not_blocked(admin_client, monkeypatch):
    existing = PropertyFactory(**ADDR)
    monkeypatch.setattr("apps.properties.admin.is_scoped", lambda user: True)
    r = admin_client.post(reverse("admin:properties_property_add"), _post_data(existing))
    assert r.status_code == 302
    assert Property.objects.count() == 2
    assert not DuplicateDismissal.objects.exists()


def test_slot_and_script_present_on_add_page(admin_client):
    html = admin_client.get(reverse("admin:properties_property_add")).content.decode()
    assert 'id="duplicates-panel"' in html
    assert "properties/admin/duplicates.js" in html


def test_add_page_has_no_stray_not_duplicate_field(admin_client):
    html = admin_client.get(reverse("admin:properties_property_add")).content.decode().lower()
    assert "not duplicate" not in html and "not_duplicate" not in html


def test_panel_shows_placeholder_for_property_without_photo(admin_client):
    PropertyFactory(**ADDR)
    r = admin_client.post(
        reverse("admin:properties_property_check_duplicates"),
        {"zip_code": "13000-000", "number": "120", "complement": "Apto 12"},
    )
    html = r.content.decode()
    assert "Sem foto" in html and "<img" not in html
    assert "w-20" not in html  # estilo próprio (panels.css), não classes que o Unfold não tem


def test_panel_shows_cover_thumbnail_when_there_is_a_photo(admin_client, settings, tmp_path):
    import io

    from django.core.files.base import ContentFile
    from PIL import Image

    from apps.properties.models import PropertyPhoto

    settings.MEDIA_ROOT = tmp_path
    existing = PropertyFactory(**ADDR)
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), "red").save(buf, format="PNG")
    PropertyPhoto.objects.create(
        property=existing, image=ContentFile(buf.getvalue(), name="a.png"), is_cover=True
    )
    r = admin_client.post(
        reverse("admin:properties_property_check_duplicates"),
        {"zip_code": "13000-000", "number": "120", "complement": "Apto 12"},
    )
    html = r.content.decode()
    assert "<img" in html and "Sem foto" not in html


def test_fallback_panel_carries_the_confirmation_checkbox(admin_client):
    existing = PropertyFactory(**ADDR)
    r = admin_client.post(reverse("admin:properties_property_add"), _post_data(existing))
    html = r.content.decode()
    assert 'type="checkbox" name="not_duplicate"' in html
    confirmed = admin_client.post(
        reverse("admin:properties_property_add"), _post_data(existing, not_duplicate="on")
    )
    assert confirmed.status_code == 302


def test_duplicate_filter_is_readable_and_keeps_old_param(admin_client):
    dup = PropertyFactory(duplicate_hint=True)
    ok = PropertyFactory()
    url = reverse("admin:properties_property_changelist")
    html = admin_client.get(url).content.decode()
    assert "Possível duplicado" in html and "Sem suspeita de duplicado" in html

    def listed(value):
        r = admin_client.get(url, {"duplicate_hint__exact": value})
        return {p.pk for p in r.context["cl"].result_list}

    assert listed("1") == {dup.pk} and listed("0") == {ok.pk}


def test_add_form_suggests_review_date(admin_client):
    from datetime import timedelta

    from django.utils import timezone

    html = admin_client.get(reverse("admin:properties_property_add")).content.decode()
    due = timezone.localdate() + timedelta(days=60)
    assert f"{due:%d/%m/%Y}" in html or f"{due:%Y-%m-%d}" in html
