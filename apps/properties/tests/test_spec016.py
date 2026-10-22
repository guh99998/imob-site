import pytest
from django.test import override_settings
from django.urls import reverse

from apps.core.models import SiteSettings

from .factories import PropertyFactory

pytestmark = pytest.mark.django_db


def test_whatsapp_text_default(rf):
    prop = PropertyFactory(sale_price=350000)
    text = prop.whatsapp_text(rf.get("/"))
    assert prop.code in text and prop.title in text and "R$ 350.000,00" in text
    assert f"{prop.get_absolute_url()}?utm_source=whatsapp" in text


def test_whatsapp_text_custom_template_and_unknown_placeholder():
    s = SiteSettings.load()
    s.whatsapp_message = "{codigo} / {bairro} / {inexistente}"
    s.save()
    prop = PropertyFactory()
    assert prop.whatsapp_text() == f"{prop.code} / {prop.neighborhood.name} / {{inexistente}}"


def test_detail_has_copy_link_and_encoded_whatsapp(client):
    s = SiteSettings.load()
    s.whatsapp = "5511999998888"
    s.save()
    prop = PropertyFactory()
    html = client.get(prop.get_absolute_url()).content.decode()
    assert "data-share" in html
    assert f'data-share href="http://testserver{prop.get_absolute_url()}"' in html
    assert "utm_source%3Dwhatsapp" in html


def test_developer_credit_in_footer(client):
    html = client.get(reverse("core:home")).content.decode()
    assert "Desenvolvido por Gustavo Lopes" in html
    assert "instagram.com/devlopes_guh" in html and "github.com/guh99998" in html


@override_settings(DEVELOPER_CREDIT=None)
def test_developer_credit_can_be_disabled(client):
    assert "Desenvolvido por" not in client.get(reverse("core:home")).content.decode()


def test_admin_change_page_shows_client_message(admin_client):
    prop = PropertyFactory()
    r = admin_client.get(reverse("admin:properties_property_change", args=[prop.pk]))
    assert r.status_code == 200
    assert "Mensagem para o cliente" in r.content.decode()
