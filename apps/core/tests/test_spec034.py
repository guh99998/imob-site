import pytest
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    client.force_login(get_user_model().objects.create_superuser("admin", "a@a.com", "pw"))
    return client


def test_mobile_assets_exist_and_are_loaded_on_every_admin_page(admin_client):
    assert finders.find("core/admin/mobile.css") and finders.find("core/admin/mobile.js")
    for name in ("admin:index", "admin:properties_property_changelist"):
        html = admin_client.get(reverse(name)).content.decode()
        assert "core/admin/mobile.css" in html and "core/admin/mobile.js" in html


def test_dashboard_grids_have_no_fixed_minimum_width(admin_client):
    html = admin_client.get(reverse("admin:index")).content.decode()
    assert "minmax(min(100%, 14rem), 1fr)" in html
    assert "minmax(min(100%, 20rem), 1fr)" in html
    assert "minmax(20rem, 1fr)" not in html and "minmax(14rem, 1fr)" not in html


def test_lists_become_cards_only_on_small_screens():
    css = open(finders.find("core/admin/mobile.css"), encoding="utf-8").read()
    assert "@media (max-width: 767px)" in css and "table.result-list" in css
    assert css.count("@media") == 1  # nada de regra mobile vazando para o desktop


def test_kanban_has_a_single_list_view_link(admin_client):
    from apps.crm.models import Client

    Client.objects.create(name="Cliente")
    html = admin_client.get(reverse("admin:crm_client_kanban")).content.decode()
    assert html.count("Ver em lista") == 1 and "contain: paint" in html


def test_user_page_shows_only_the_reset_password_button(admin_client):
    user = get_user_model().objects.create_user("maria", password="segredo-123")
    html = admin_client.get(reverse("admin:auth_user_change", args=[user.pk])).content.decode()
    assert "Redefinir senha" in html
    assert reverse("admin:auth_user_password_change", args=[user.pk]) in html
    assert (
        "pbkdf2" not in html and "iterações" not in html.lower() and "algoritmo" not in html.lower()
    )
    # salvar o usuário sem tocar na senha não a altera
    data = {"username": "maria", "role": "Atendente", "is_active": "on"}
    assert (
        admin_client.post(reverse("admin:auth_user_change", args=[user.pk]), data).status_code
        == 302
    )
    user.refresh_from_db()
    assert user.check_password("segredo-123")


def test_permissions_are_a_readable_checklist(admin_client):
    from django.contrib.auth.models import Permission

    from apps.core.admin import permission_label

    user = get_user_model().objects.create_user("joana", password="x")
    html = admin_client.get(reverse("admin:auth_user_change", args=[user.pk])).content.decode()
    assert 'name="user_permissions"' in html and 'type="checkbox"' in html
    assert "user_permissions_from" not in html  # sem a lista dupla antiga
    assert permission_label(Permission.objects.get(codename="view_client")) == "Cliente: Ver"
    assert permission_label(Permission.objects.get(codename="add_property")) == "Imóvel: Cadastrar"
    assert "Can view" not in html


def test_checklists_use_columns(admin_client):
    from django.contrib.staticfiles import finders

    css = open(finders.find("core/admin/checklists.css"), encoding="utf-8").read()
    assert (
        "#id_features" in css and "#id_user_permissions" in css and "grid-template-columns" in css
    )
    html = admin_client.get(reverse("admin:properties_property_add")).content.decode()
    assert "core/admin/checklists.css" in html
