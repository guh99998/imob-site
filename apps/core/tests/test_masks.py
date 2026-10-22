from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.core import features, validators
from apps.core.widgets import BRDecimalField, parse_br_decimal


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1.234,56", Decimal("1234.56")),
        ("R$ 1.234,56", Decimal("1234.56")),
        ("980.000,00", Decimal("980000.00")),
        ("320,5 m²", Decimal("320.5")),
        ("1234.56", Decimal("1234.56")),
        ("1.234", Decimal("1234")),
        ("1.234.567", Decimal("1234567")),
        ("", None),
    ],
)
def test_parse_br_decimal(raw, expected):
    assert parse_br_decimal(raw) == expected


def test_br_decimal_field_cleans_masked_value():
    field = BRDecimalField(max_digits=12, decimal_places=2)
    assert field.clean("R$ 1.234,56") == Decimal("1234.56")
    with pytest.raises(ValidationError):
        field.clean("abc")


def test_cpf_cnpj_validators():
    assert validators.is_valid_cpf("529.982.247-25")
    assert not validators.is_valid_cpf("111.111.111-11")
    assert not validators.is_valid_cpf("529.982.247-24")
    assert validators.is_valid_cnpj("11.222.333/0001-81")
    assert not validators.is_valid_cnpj("11.222.333/0001-80")
    with pytest.raises(ValidationError):
        validators.validate_cpf_or_cnpj("123")
    validators.validate_cpf_or_cnpj("")


def test_features_enabled(settings):
    settings.SITE_FEATURES = ["owners"]
    assert features.enabled("owners") and not features.enabled("partners")


def test_property_form_accepts_masked_price(admin_client, settings):
    from apps.properties.tests.factories import CategoryFactory, NeighborhoodFactory

    nb = NeighborhoodFactory()
    data = {
        "title": "Casa mascarada",
        "category": CategoryFactory().pk,
        "status": "DRAFT",
        "purpose": "SALE",
        "sale_price": "R$ 1.234.567,89",
        "neighborhood": nb.pk,
        "bedrooms": 1,
        "suites": 0,
        "bathrooms": 1,
        "parking_spaces": 0,
        "area_total": "320,50 m²",
        "photos-TOTAL_FORMS": 0,
        "photos-INITIAL_FORMS": 0,
        "photos-MIN_NUM_FORMS": 0,
        "photos-MAX_NUM_FORMS": 1000,
    }
    r = admin_client.post(reverse("admin:properties_property_add"), data)
    assert r.status_code == 302, getattr(r, "context_data", None)
    from apps.properties.models import Property

    prop = Property.objects.get(title="Casa mascarada")
    assert prop.sale_price == Decimal("1234567.89") and prop.area_total == Decimal("320.50")


def test_theme_is_light_and_sidebar_single_active(admin_client):
    from apps.properties.tests.factories import PropertyFactory

    prop = PropertyFactory()
    for url, active_title in [
        (reverse("admin:properties_property_changelist"), "Todos os imóveis"),
        (reverse("admin:properties_property_change", args=[prop.pk]), "Todos os imóveis"),
        (reverse("admin:properties_property_add"), "Cadastrar imóvel"),
    ]:
        r = admin_client.get(url)
        items = [
            i
            for g in r.context["sidebar_navigation"]
            for i in g["items"]
            if i.get("active") and i["title"] in ("Todos os imóveis", "Cadastrar imóvel")
        ]
        assert [str(i["title"]) for i in items] == [active_title], url
    html = admin_client.get(reverse("admin:index")).content.decode()
    assert "prefers-color-scheme: dark" not in html
    assert "core/admin/masks.js" in html
