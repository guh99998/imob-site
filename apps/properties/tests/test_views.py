import pytest
from django.urls import reverse

from apps.properties.models import Category, Property

from .factories import CategoryFactory, FeatureFactory, NeighborhoodFactory, PropertyFactory

pytestmark = pytest.mark.django_db


def slugs(response):
    return {p.slug for p in response.context["page"]}


def test_list_shows_only_published(client):
    pub = PropertyFactory()
    draft = PropertyFactory(status=Property.Status.DRAFT)
    r = client.get(reverse("properties:list"))
    assert r.status_code == 200
    assert pub.slug in slugs(r) and draft.slug not in slugs(r)


def test_detail_draft_is_404(client):
    draft = PropertyFactory(status=Property.Status.DRAFT)
    assert client.get(draft.get_absolute_url()).status_code == 404


def test_detail_renders_with_whatsapp(client):
    from apps.core.models import SiteSettings

    s = SiteSettings.load()
    s.whatsapp = "+55 (11) 99999-8888"
    s.save()
    prop = PropertyFactory()
    prop.features.add(FeatureFactory(name="Piscina"))
    r = client.get(prop.get_absolute_url())
    html = r.content.decode()
    assert r.status_code == 200
    assert "Piscina" in html
    assert (
        "https://wa.me/5511999998888?text=Ol%C3%A1%2C%20tenho%20interesse%20no%20im%C3%B3vel%20"
        + prop.code
        in html
    )
    assert 'property="og:title"' in html


def test_filter_purpose_and_category(client):
    sale = PropertyFactory(purpose="SALE")
    house = Category.objects.get(slug="casa")  # criada pela data migration
    rent = PropertyFactory(purpose="RENT", sale_price=None, rent_price=2000, category=house)
    both = PropertyFactory(purpose="BOTH", rent_price=3000)
    r = client.get(reverse("properties:list"), {"purpose": "RENT"})
    assert slugs(r) == {rent.slug, both.slug}
    r = client.get(reverse("properties:list"), {"purpose": "SALE"})
    assert slugs(r) == {sale.slug, both.slug}
    r = client.get(reverse("properties:list"), {"category": house.slug})
    assert slugs(r) == {rent.slug}


def test_filter_price_uses_purpose(client):
    cheap = PropertyFactory(purpose="RENT", sale_price=None, rent_price=1000)
    PropertyFactory(purpose="RENT", sale_price=None, rent_price=5000)
    r = client.get(reverse("properties:list"), {"purpose": "RENT", "max_price": 2000})
    assert slugs(r) == {cheap.slug}


def test_filter_bedrooms_parking_area_neighborhood(client):
    nb = NeighborhoodFactory()
    match = PropertyFactory(bedrooms=3, parking_spaces=2, area_total=120, neighborhood=nb)
    PropertyFactory(bedrooms=1, parking_spaces=0, area_total=40)
    r = client.get(
        reverse("properties:list"),
        {"bedrooms": 3, "parking_spaces": 1, "min_area": 100, "neighborhood": nb.pk},
    )
    assert slugs(r) == {match.slug}


def test_ordering_by_price(client):
    a = PropertyFactory(sale_price=100)
    b = PropertyFactory(sale_price=300)
    c = PropertyFactory(sale_price=200)
    r = client.get(reverse("properties:list"), {"order": "-price"})
    assert [p.pk for p in r.context["page"]] == [b.pk, c.pk, a.pk]


def test_pagination(client):
    PropertyFactory.create_batch(13)
    r = client.get(reverse("properties:list"))
    assert len(r.context["page"]) == 12
    assert len(client.get(reverse("properties:list"), {"page": 2}).context["page"]) == 1


def test_htmx_returns_partial(client):
    PropertyFactory()
    r = client.get(reverse("properties:list"), HTTP_HX_REQUEST="true")
    assert "<html" not in r.content.decode()
    assert "properties/partials/results.html" in [t.name for t in r.templates]


def test_home_shows_featured(client):
    feat = PropertyFactory(is_featured=True, title="Destaque Premium")
    PropertyFactory(title="Comum", is_featured=False)
    r = client.get("/")
    assert r.status_code == 200
    assert list(r.context["featured"]) == [feat]


def test_sitemap_and_robots(client):
    prop = PropertyFactory()
    PropertyFactory(status=Property.Status.DRAFT, slug="rascunho-secreto")
    sm = client.get("/sitemap.xml").content.decode()
    assert prop.slug in sm and "rascunho-secreto" not in sm
    robots = client.get("/robots.txt")
    assert "Sitemap:" in robots.content.decode()


def test_home_lists_categories_with_counts(client):
    cat = CategoryFactory(name="Chácara")
    PropertyFactory(category=cat)
    PropertyFactory(category=cat, status=Property.Status.DRAFT)
    r = client.get("/")
    found = {c.name: c.total for c in r.context["categories"]}
    assert found == {"Chácara": 1}
    assert "Chácara" in r.content.decode()


def test_detail_shows_similar_same_category_first(client):
    cat = CategoryFactory()
    main = PropertyFactory(category=cat)
    same = PropertyFactory(category=cat)
    same_city = PropertyFactory(neighborhood=main.neighborhood)
    PropertyFactory()  # sem relação
    r = client.get(main.get_absolute_url())
    assert list(r.context["similar"]) == [same, same_city]


def test_active_filter_chips_have_removal_urls(client):
    r = client.get(reverse("properties:list"), {"purpose": "RENT", "bedrooms": 2})
    chips = {c["label"]: c["url"] for c in r.context["chips"]}
    assert chips["Finalidade: Aluguel"] == "?bedrooms=2"
