from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.properties.models import Category, Property, SearchQuery

from .factories import NeighborhoodFactory, PropertyFactory

pytestmark = pytest.mark.django_db

BROWSER = {"HTTP_USER_AGENT": "Mozilla/5.0 (X11; Linux x86_64) Firefox/130.0"}
LIST = "properties:list"


def search(client, query="", **extra):
    return client.get(reverse(LIST) + query, **{**BROWSER, **extra})


def test_same_search_with_other_param_order_and_price_format_is_one_row(client):
    PropertyFactory()
    search(client, "?purpose=SALE&max_price=500000")
    search(client, "?max_price=R$ 500.000,00&purpose=SALE")
    row = SearchQuery.objects.get()
    assert row.count == 2
    assert row.key == "max_price=500000&purpose=SALE"
    assert row.label == "Imóveis à venda · até R$ 500.000"


def test_label_with_category_and_neighborhood(client):
    cat = Category.objects.get(slug="casa")
    hood = NeighborhoodFactory(name="Centro")
    PropertyFactory(category=cat, neighborhood=hood)
    search(client, f"?purpose=RENT&category=casa&neighborhood={hood.pk}&bedrooms=3")
    assert SearchQuery.objects.get().label == "Casa para alugar em Centro · 3+ quartos"


def test_results_count_is_stored(client):
    PropertyFactory.create_batch(2)
    search(client, "?bedrooms=2")
    search(client, "?bedrooms=2")
    assert SearchQuery.objects.get().results == 2


@pytest.mark.parametrize(
    "query,extra",
    [
        ("", {}),  # sem filtro
        ("?order=price", {}),  # só ordenação
        ("?purpose=SALE&page=2", {}),  # página 2
        ("?code=XX999&purpose=SALE", {}),  # busca por código
        ("?purpose=SALE", {"HTTP_USER_AGENT": "Googlebot/2.1 (+http://www.google.com/bot.html)"}),
        ("?purpose=SALE", {"HTTP_USER_AGENT": ""}),
        ("?bedrooms=abc", {}),  # formulário inválido
    ],
)
def test_not_recorded(client, query, extra):
    PropertyFactory()
    search(client, query, **extra)
    assert SearchQuery.objects.count() == 0


def test_landing_and_htmx_are_recorded(client):
    cat = Category.objects.get(slug="casa")
    PropertyFactory(category=cat)
    client.get(reverse("core:landing", args=["comprar", "casa"]), **BROWSER)
    search(client, "?purpose=SALE&category=casa", HTTP_HX_REQUEST="true")
    row = SearchQuery.objects.get()
    assert row.key == "category=casa&purpose=SALE" and row.count == 2


def _popular(count, results=1, days_ago=0, **kw):
    return SearchQuery.objects.create(
        key=kw.pop("key", f"bedrooms={count}{days_ago}"),
        label=kw.pop("label", "Busca"),
        count=count,
        results=results,
        last_searched_at=timezone.now() - timedelta(days=days_ago),
        **kw,
    )


def test_home_shows_only_popular_recent_with_results(client):
    _popular(5, key="bedrooms=2", label="Dois quartos")
    _popular(2, key="bedrooms=3", label="Poucas vezes")
    _popular(9, key="bedrooms=4", label="Sem resultado", results=0)
    _popular(9, key="bedrooms=5", label="Antiga", days_ago=45)
    html = client.get(reverse("core:home")).content.decode()
    assert "Mais procurados" in html and "Dois quartos" in html
    assert 'href="/imoveis/?bedrooms=2"' in html
    for hidden in ("Poucas vezes", "Sem resultado", "Antiga"):
        assert hidden not in html


def test_home_hides_section_without_data(client):
    assert "Mais procurados" not in client.get(reverse("core:home")).content.decode()


def test_home_limits_to_six(client):
    for i in range(8):
        _popular(5 + i, key=f"bedrooms={i + 1}", label=f"Busca {i}")
    assert client.get(reverse("core:home")).content.decode().count("rounded-full px-4 py-2") == 6


def test_sold_property_still_counts_but_published_only_in_results(client):
    PropertyFactory(status=Property.Status.SOLD)
    search(client, "?bedrooms=2")
    assert SearchQuery.objects.get().results == 0
