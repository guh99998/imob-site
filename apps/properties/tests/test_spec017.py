import pytest
from django.urls import reverse

from apps.properties import favorites
from apps.properties.models import Property

from .factories import PropertyFactory

pytestmark = pytest.mark.django_db


def _fav_url(prop):
    return reverse("properties:favorite", args=[prop.slug])


def test_toggle_without_js_sets_cookie_and_redirects(client):
    prop = PropertyFactory()
    r = client.post(_fav_url(prop), {"next": "/imoveis/?purpose=SALE"})
    assert r.status_code == 302 and r["Location"] == "/imoveis/?purpose=SALE"
    assert client.cookies[favorites.COOKIE].value == prop.code
    prop.refresh_from_db()
    assert prop.favorites_count == 1

    r = client.post(_fav_url(prop))
    assert r["Location"] == prop.get_absolute_url()
    assert client.cookies[favorites.COOKIE].value == ""
    prop.refresh_from_db()
    assert prop.favorites_count == 1  # só sobe


def test_external_next_is_ignored(client):
    prop = PropertyFactory()
    r = client.post(_fav_url(prop), {"next": "https://example.com/"})
    assert r["Location"] == prop.get_absolute_url()


def test_get_not_allowed_and_unpublished_404(client):
    prop = PropertyFactory()
    assert client.get(_fav_url(prop)).status_code == 405
    sold = PropertyFactory(status=Property.Status.SOLD)
    assert client.post(_fav_url(sold)).status_code == 404


def test_htmx_returns_button_and_oob_counter(client):
    prop = PropertyFactory()
    r = client.post(_fav_url(prop), {"variant": "full"}, headers={"HX-Request": "true"})
    html = r.content.decode()
    assert r.status_code == 200
    assert "Salvo nos favoritos" in html and 'aria-pressed="true"' in html
    assert 'id="favs-count" hx-swap-oob="true"' in html and "(1)" in html


def test_cookie_with_garbage_does_not_break(client):
    prop = PropertyFactory()
    client.cookies[favorites.COOKIE] = f"<script>,,{prop.code.lower()},{'X' * 50},{prop.code}"
    assert client.get(reverse("core:home")).status_code == 200
    r = client.get(reverse("core:favorites"))
    assert r.status_code == 200
    assert list(r.context["properties"]) == [prop]
    assert r.context["favorites_total"] == 1


def test_list_hides_sold_and_rewrites_cookie(client):
    a, b = PropertyFactory(), PropertyFactory()
    client.cookies[favorites.COOKIE] = f"{a.code},{b.code}"
    Property.objects.filter(pk=a.pk).update(status=Property.Status.SOLD)
    r = client.get(reverse("core:favorites"))
    assert list(r.context["properties"]) == [b]
    assert r.cookies[favorites.COOKIE].value == b.code
    assert "noindex" in r.content.decode()


def test_list_most_recent_first(client):
    a, b = PropertyFactory(), PropertyFactory()
    client.cookies[favorites.COOKIE] = f"{a.code},{b.code}"
    assert list(client.get(reverse("core:favorites")).context["properties"]) == [b, a]


def test_empty_list_message(client):
    assert "ainda não salvou" in client.get(reverse("core:favorites")).content.decode()


def test_card_and_header_reflect_cookie(client):
    prop = PropertyFactory()
    client.cookies[favorites.COOKIE] = prop.code
    html = client.get(reverse("properties:list")).content.decode()
    assert f'aria-label="Remover {prop.code} dos favoritos"' in html
    assert "(1)" in html


def test_cookie_is_capped(client):
    props = PropertyFactory.create_batch(3)
    client.cookies[favorites.COOKIE] = ",".join(f"ZZ{i:03d}" for i in range(favorites.MAX_ITEMS))
    client.post(_fav_url(props[0]))
    codes = client.cookies[favorites.COOKIE].value.split(",")
    assert len(codes) == favorites.MAX_ITEMS and codes[-1] == props[0].code


def test_admin_list_shows_favorites_column(admin_client):
    PropertyFactory(favorites_count=7)
    r = admin_client.get(reverse("admin:properties_property_changelist") + "?o=-7")
    assert r.status_code == 200
    assert "favoritos" in r.content.decode().lower()
