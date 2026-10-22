import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.core.models import SiteSettings
from apps.properties.models import Property
from apps.properties.tests.factories import CategoryFactory, NeighborhoodFactory, PropertyFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    user = get_user_model().objects.create_superuser("admin", "a@a.com", "pw")
    client.force_login(user)
    return client


@pytest.mark.parametrize(
    "name",
    [
        "properties_property_changelist",
        "properties_property_add",
        "properties_category_changelist",
        "properties_category_add",
        "properties_feature_changelist",
        "properties_city_changelist",
        "properties_city_add",
        "properties_neighborhood_changelist",
        "leads_lead_changelist",
        "auth_user_changelist",
        "index",
    ],
)
def test_admin_pages_load(admin_client, name):
    assert admin_client.get(reverse(f"admin:{name}")).status_code == 200


def test_property_change_page_and_actions(admin_client):
    props = PropertyFactory.create_batch(2, status=Property.Status.DRAFT)
    assert (
        admin_client.get(
            reverse("admin:properties_property_change", args=[props[0].pk])
        ).status_code
        == 200
    )
    ids = [p.pk for p in props]
    admin_client.post(
        reverse("admin:properties_property_changelist"),
        {"action": "publish", "_selected_action": ids},
    )
    assert (
        Property.objects.filter(status="PUBLISHED", pk__in=ids, published_at__isnull=False).count()
        == 2
    )
    admin_client.post(
        reverse("admin:properties_property_changelist"),
        {"action": "mark_sold", "_selected_action": ids},
    )
    assert Property.objects.filter(status="SOLD").count() == 2


def test_admin_create_validates_price(admin_client):
    nb = NeighborhoodFactory()
    r = admin_client.post(
        reverse("admin:properties_property_add"),
        {
            "title": "T",
            "status": "DRAFT",
            "purpose": "SALE",
            "category": CategoryFactory().pk,
            "neighborhood": nb.pk,
            "bedrooms": 1,
            "suites": 0,
            "bathrooms": 1,
            "parking_spaces": 0,
            "photos-TOTAL_FORMS": 0,
            "photos-INITIAL_FORMS": 0,
            "photos-MIN_NUM_FORMS": 0,
            "photos-MAX_NUM_FORMS": 1000,
        },
    )
    assert r.status_code == 200
    assert "Informe o preço de venda" in r.content.decode()


def test_site_settings_singleton():
    a = SiteSettings.load()
    b = SiteSettings(name="Outra")
    b.save()
    assert a.pk == b.pk == 1 and SiteSettings.objects.count() == 1


def test_site_settings_changelist_redirects_to_single_record(admin_client):
    r = admin_client.get(reverse("admin:core_sitesettings_changelist"))
    assert r.status_code == 302
    assert r.url == reverse("admin:core_sitesettings_change", args=[1])
    assert admin_client.get(r.url).status_code == 200


def test_dashboard_shows_numbers_and_shortcuts(admin_client):
    PropertyFactory(title="Casa do Lago", status=Property.Status.PUBLISHED)
    PropertyFactory(status=Property.Status.DRAFT)
    r = admin_client.get(reverse("admin:index"))
    html = r.content.decode()
    assert r.status_code == 200
    assert "Cadastrar imóvel" in html and "Abrir o site" in html
    assert "Casa do Lago" in html
    assert [n["value"] for n in r.context["numbers"]][:2] == [1, 1]


def test_sidebar_has_sections_and_no_groups(admin_client):
    html = admin_client.get(reverse("admin:index")).content.decode()
    for label in ("Todos os imóveis", "Categorias", "Mensagens recebidas", "Equipe"):
        assert label in html
    assert Group not in admin.site._registry


def test_admin_create_generates_code_and_slug(admin_client):
    nb = NeighborhoodFactory()
    data = {
        "title": "Casa Nova",
        "category": CategoryFactory().pk,
        "status": "DRAFT",
        "purpose": "SALE",
        "sale_price": "300000",
        "neighborhood": nb.pk,
        "bedrooms": 1,
        "suites": 0,
        "bathrooms": 1,
        "parking_spaces": 0,
        "photos-TOTAL_FORMS": 0,
        "photos-INITIAL_FORMS": 0,
        "photos-MIN_NUM_FORMS": 0,
        "photos-MAX_NUM_FORMS": 1000,
    }
    r = admin_client.post(reverse("admin:properties_property_add"), data)
    assert r.status_code == 302
    prop = Property.objects.get(title="Casa Nova")
    assert prop.code.startswith("DLM-") and prop.slug.endswith("casa-nova")


def test_lead_mark_contacted_action(admin_client):
    from apps.leads.models import Lead

    lead = Lead.objects.create(name="A", email="a@a.com", message="oi")
    admin_client.post(
        reverse("admin:leads_lead_changelist"),
        {"action": "mark_contacted", "_selected_action": [lead.pk]},
    )
    lead.refresh_from_db()
    assert lead.status == Lead.Status.CONTACTED
