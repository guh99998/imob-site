import re

import pytest
from django.core.exceptions import ValidationError

from apps.properties.models import Property

from .factories import PropertyFactory

pytestmark = pytest.mark.django_db


def test_sidebar_links_are_real_urls(admin_client):
    html = admin_client.get("/admin/").content.decode()
    hrefs = re.findall(r'href="([^"]*)"', html)
    assert not [h for h in hrefs if "apps." in h]
    assert "/admin/crm/followup/?done__exact=0" in hrefs


def test_featured_action_uses_env_limit(settings):
    settings.MAX_FEATURED = 1
    PropertyFactory(is_featured=True)
    with pytest.raises(ValidationError):
        extra = PropertyFactory()
        extra.is_featured = True
        extra.clean()


def test_site_settings_no_longer_has_max_featured():
    from apps.core.models import SiteSettings

    assert not hasattr(SiteSettings.load(), "max_featured")


def test_card_shows_code_badge(client):
    p = PropertyFactory()
    assert f"Cód. {p.code}" in client.get("/imoveis/").content.decode()


def test_price_for():
    p = PropertyFactory(purpose=Property.Purpose.BOTH, sale_price=500000, rent_price=2500)
    assert p.price_for("SALE") == 500000
    assert p.price_for("RENT") == 2500
    assert p.price_for("") is None


def test_both_property_price_by_section(client):
    PropertyFactory(purpose=Property.Purpose.BOTH, sale_price=500000, rent_price=2500)
    sale = client.get("/imoveis/?purpose=SALE").content.decode()
    assert "500,000" in sale or "500.000" in sale
    assert "/mês" not in sale
    rent = client.get("/imoveis/?purpose=RENT").content.decode()
    assert "2,500" in rent or "2.500" in rent
    assert "/mês" in rent
    both = client.get("/imoveis/").content.decode()
    assert "Venda" in both and "Aluguel" in both and "/mês" in both


def test_home_featured_big_plus_stacked(client):
    PropertyFactory.create_batch(3, is_featured=True)
    html = client.get("/").content.decode()
    assert "lg:col-span-7" in html
    assert html.count("lg:col-span-5") >= 2
