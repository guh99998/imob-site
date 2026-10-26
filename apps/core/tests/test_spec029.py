import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse
from django.utils import translation

from apps.core import admin_navigation as nav
from apps.leads.models import PropertySearch
from apps.properties.models import Category, SearchQuery
from apps.properties.tests.factories import CategoryFactory, FeatureFactory, PropertyFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    user = get_user_model().objects.create_superuser("admin", "a@a.com", "pw")
    client.force_login(user)
    return client


def _active(check, path):
    return check(RequestFactory().get(path))


def test_sidebar_clients_and_kanban_are_exclusive():
    clients = reverse("admin:crm_client_changelist")
    kanban = reverse("admin:crm_client_kanban")
    assert _active(nav.clients_active, clients)
    assert not _active(nav.clients_active, kanban)
    assert _active(nav.kanban_active, kanban)
    assert not _active(nav.kanban_active, clients)


def test_sidebar_followups_and_settings_are_active():
    assert _active(nav.followups_active, reverse("admin:crm_followup_changelist"))
    assert not _active(nav.followups_active, reverse("admin:index"))
    assert _active(nav.site_settings_active, reverse("admin:core_sitesettings_changelist"))


def test_unfold_texts_are_translated_to_pt_br():
    with translation.override("pt-br"):
        assert translation.gettext("Select value") == "Selecione um valor"
        assert translation.gettext("No results found") == "Nenhum resultado encontrado"
        assert translation.gettext("Reset filters") == "Limpar filtros"


def test_categories_are_alphabetical():
    CategoryFactory(name="Zebra")
    CategoryFactory(name="Alfa")
    names = list(Category.objects.values_list("name", flat=True))
    assert names == sorted(names)
    assert not hasattr(Category, "order")


def test_demo_banner_follows_demo_mode(client, settings):
    settings.DEMO_MODE = False
    assert "Site de demonstração" not in client.get(reverse("core:home")).content.decode()
    settings.DEMO_MODE = True
    assert "Site de demonstração" in client.get(reverse("core:home")).content.decode()


def test_share_link_script_is_rendered_with_fallback(client):
    prop = PropertyFactory()
    html = client.get(prop.get_absolute_url()).content.decode()
    assert "data-share-feedback" in html
    assert "execCommand" in html


def test_property_add_form_is_guided(admin_client):
    FeatureFactory(name="Piscina")
    html = admin_client.get(reverse("admin:properties_property_add")).content.decode()
    assert "Selecione a categoria" in html
    assert "Ex.: Casa 3 quartos com piscina no Jardim América" in html
    assert 'placeholder="00000-000"' in html
    assert "data-bulk-photos" in html
    assert "Mensagem para o cliente" not in html


def test_features_are_checkboxes(admin_client):
    FeatureFactory(name="Piscina")
    html = admin_client.get(reverse("admin:properties_property_add")).content.decode()
    assert 'type="checkbox"' in html and "Piscina" in html


def test_search_query_not_in_admin():
    assert SearchQuery not in admin.site._registry


def test_property_search_list_shows_summary_and_whatsapp(admin_client):
    search = PropertySearch.objects.create(
        name="Maria", whatsapp="(11) 91234-5678", purpose="SALE", max_price=500000
    )
    html = admin_client.get(reverse("admin:leads_propertysearch_changelist")).content.decode()
    assert "Maria" in html
    assert "https://wa.me/5511912345678" in html
    assert "até R$ 500.000,00" in html
    assert "Ver 0 imóveis compatíveis" in html
    assert search.matching_count() == 0
