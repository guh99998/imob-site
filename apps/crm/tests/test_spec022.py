from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.template import Context, Template
from django.urls import reverse

from apps.core.models import SiteSettings
from apps.crm import documents
from apps.crm.base_templates import BASE_TEMPLATES
from apps.crm.extenso import cardinal, reais
from apps.crm.models import Client, DocumentTemplate, GeneratedDocument
from apps.people import roles
from apps.people.models import Broker
from apps.properties.tests.factories import PropertyFactory

pytestmark = pytest.mark.django_db
User = get_user_model()


def make_template(body, kind="RECEIPT", **kwargs):
    return DocumentTemplate.objects.create(name="Teste", kind=kind, body=body, **kwargs)


# ---------- valor por extenso ----------


@pytest.mark.parametrize(
    "value,text",
    [
        (0, "zero reais"),
        (1, "um real"),
        (2, "dois reais"),
        (15, "quinze reais"),
        (21, "vinte e um reais"),
        (100, "cem reais"),
        (101, "cento e um reais"),
        (250, "duzentos e cinquenta reais"),
        (1000, "mil reais"),
        (1001, "mil e um reais"),
        (1500, "mil e quinhentos reais"),
        (2345, "dois mil trezentos e quarenta e cinco reais"),
        (21000, "vinte e um mil reais"),
        (350000, "trezentos e cinquenta mil reais"),
        (1000000, "um milhão de reais"),
        (2500000, "dois milhões e quinhentos mil reais"),
        (1331000, "um milhão trezentos e trinta e um mil reais"),
        (3000000000, "três bilhões de reais"),
        (Decimal("12.45"), "doze reais e quarenta e cinco centavos"),
        ("0.01", "um centavo"),
        ("0.50", "cinquenta centavos"),
        (Decimal("1331000.00"), "um milhão trezentos e trinta e um mil reais"),
        (5.999, "seis reais"),  # arredonda para o centavo
    ],
)
def test_reais(value, text):
    assert reais(value) == text


@pytest.mark.parametrize("value", [None, "", "abc", -5])
def test_reais_invalid_is_empty(value):
    assert reais(value) == ""


def test_cardinal_hundreds_of_thousands():
    assert cardinal(200000) == "duzentos mil"
    assert cardinal(1200000) == "um milhão e duzentos mil"


def test_filter_in_template():
    tpl = Template("{% load crm_docs %}{{ v|valor_por_extenso }}")
    assert tpl.render(Context({"v": 1500})) == "mil e quinhentos reais"


# ---------- renderização isolada ----------


def test_context_has_only_plain_data():
    prop = PropertyFactory(sale_price=350000)
    client = Client.objects.create(name="Ana", whatsapp="(11) 91234-5678")
    ctx = documents.build_context(client=client, property=prop)

    def plain(value):
        if isinstance(value, dict):
            return all(plain(v) for v in value.values())
        return isinstance(value, str | Decimal | int)

    assert plain(ctx)
    assert ctx["imovel"]["valor"] == "R$ 350.000,00"
    assert ctx["imovel"]["valor_extenso"] == "trezentos e cinquenta mil reais"
    assert ctx["cliente"]["nome"] == "Ana" and ctx["imovel"]["codigo"] == prop.code


def test_context_without_client_or_property():
    ctx = documents.build_context()
    assert ctx["cliente"]["nome"] == "" and ctx["imovel"]["valor"] == "valor a combinar"
    assert ctx["data_extenso"].count(" de ") == 2


def test_render_fills_data_and_escapes_everything():
    client = Client.objects.create(name="<script>alert(1)</script> & Cia")
    tpl = make_template("# Recibo\n\nRecebi de {{ cliente.nome }}.\nLinha 2 <b>x</b>")
    html = documents.generate(tpl, client=client).html
    assert "<h2>Recibo</h2>" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; Cia" in html
    assert "<script" not in html and "<b>" not in html
    assert "Linha 2 &lt;b&gt;x&lt;/b&gt;" in html and "<br>" in html


def test_render_cannot_reach_internals():
    client = Client.objects.create(name="Ana")
    body = "B={{ settings.SECRET_KEY }}|C={{ request }}|E={{ user }}|F={{ imovel.codigo.upper }}"
    html = documents.generate(make_template(body), client=client).html
    assert "B=|C=|E=|F=" in html and "SECRET" not in html


@pytest.mark.parametrize("body", ["{{ cliente.__class__ }}", "{{ cliente.__dict__ }}", "{{ _x }}"])
def test_underscore_attributes_are_refused(body):
    with pytest.raises(documents.DocumentError):
        documents.generate(make_template(body))


@pytest.mark.parametrize(
    "body",
    [
        "{% debug %}",
        "{% include 'x.html' %}",
        "{% extends 'base.html' %}",
        "{% ssi '/etc/passwd' %}",
        "{%debug%}",
        "{%- include 'a' -%}",
        "{% load static %}{% static 'x' %}",
        "{% load i18n %}",
        "{% if %}",
        "{% nao_existe %}",
    ],
)
def test_forbidden_or_broken_templates_are_rejected(body):
    with pytest.raises(ValidationError) as exc:
        DocumentTemplate(name="X", kind="RECEIPT", body=body).full_clean()
    assert "body" in exc.value.message_dict
    with pytest.raises(documents.DocumentError):
        documents.generate(DocumentTemplate(name="X", kind="RECEIPT", body=body))


def test_valid_template_with_conditionals_and_filter():
    body = (
        "{% if cliente.nome %}{{ cliente.nome }}{% else %}sem nome{% endif %} "
        "{{ 1500|valor_por_extenso }}"
    )
    DocumentTemplate(name="X", kind="RECEIPT", body=body).full_clean()
    assert "sem nome mil e quinhentos reais" in documents.generate(make_template(body)).html


def test_history_keeps_the_text_when_the_template_changes():
    client = Client.objects.create(name="Ana")
    tpl = make_template("Olá {{ cliente.nome }}")
    doc = documents.generate(tpl, client=client)
    tpl.body = "Tchau"
    tpl.save()
    doc.refresh_from_db()
    assert "Olá Ana" in doc.html and doc.title == "Teste"


def test_base_templates_are_valid_and_render_with_demo_data():
    site = SiteSettings.load()
    site.creci, site.cnpj = "12345-J", "11.222.333/0001-81"
    site.save()
    prop = PropertyFactory(sale_price=350000)
    client = Client.objects.create(name="Ana Souza")
    assert len(BASE_TEMPLATES) == 5
    for kind, name, body in BASE_TEMPLATES:
        tpl = DocumentTemplate(name=name, kind=kind, body=body)
        tpl.full_clean()
        html = documents.render(tpl, documents.build_context(client=client, property=prop))
        assert "Ana Souza" in html and "{{" not in html and "{%" not in html, name


def test_seed_command_is_idempotent(capsys):
    call_command("seed_document_templates")
    assert DocumentTemplate.objects.count() == 5
    assert "5 modelo(s) criado(s)" in capsys.readouterr().out
    call_command("seed_document_templates")
    assert DocumentTemplate.objects.count() == 5
    assert "revise com seu jurídico" in DocumentTemplate.objects.first().description


# ---------- painel ----------


def test_new_page_and_generation_flow(admin_client, admin_user):
    call_command("seed_document_templates")
    tpl = DocumentTemplate.objects.get(kind="VISIT")
    prop = PropertyFactory(sale_price=350000)
    client = Client.objects.create(name="Ana Souza")
    url = reverse("admin:crm_generateddocument_new")
    page = admin_client.get(url, {"property": prop.pk, "client": client.pk}).content.decode()
    assert "Gerar documento" in page and "revise com seu jurídico" in page
    assert f'value="{prop.pk}" selected' in page and f'value="{client.pk}" selected' in page

    r = admin_client.post(url, {"template": tpl.pk, "client": client.pk, "property": prop.pk})
    doc = GeneratedDocument.objects.get()
    assert r.status_code == 302 and r["Location"] == reverse(
        "admin:crm_generateddocument_print", args=[doc.pk]
    )
    assert (doc.client, doc.property, doc.generated_by) == (client, prop, admin_user)

    site = SiteSettings.load()
    site.name, site.creci = "Imobiliária Teste", "99999-J"
    site.save()
    printed = admin_client.get(r["Location"]).content.decode()
    assert "Ana Souza" in printed and prop.code in printed and "TERMO DE VISITA" in printed
    assert "Imobiliária Teste" in printed and "CRECI 99999-J" in printed
    assert "Imprimir / Salvar PDF" in printed and "noindex" in printed


def test_new_requires_template_and_ignores_inactive(admin_client):
    inactive = make_template("x", is_active=False)
    r = admin_client.post(reverse("admin:crm_generateddocument_new"), {"template": inactive.pk})
    assert r.status_code == 200 and GeneratedDocument.objects.count() == 0
    r = admin_client.post(reverse("admin:crm_generateddocument_new"), {})
    assert r.status_code == 200 and GeneratedDocument.objects.count() == 0


def test_history_list_and_detail(admin_client):
    tpl = make_template("# Título\n\nTexto")
    doc = documents.generate(tpl, client=Client.objects.create(name="Ana"))
    listing = admin_client.get(reverse("admin:crm_generateddocument_changelist")).content.decode()
    assert "Teste" in listing and "Ana" in listing
    assert reverse("admin:crm_generateddocument_print", args=[doc.pk]) in listing
    detail = admin_client.get(reverse("admin:crm_generateddocument_change", args=[doc.pk]))
    assert detail.status_code == 200 and "<h2>Título</h2>" in detail.content.decode()
    # histórico é só leitura
    admin_client.post(
        reverse("admin:crm_generateddocument_change", args=[doc.pk]), {"title": "Alterado"}
    )
    doc.refresh_from_db()
    assert doc.title == "Teste"


def test_add_view_redirects_to_generator(admin_client):
    r = admin_client.get(reverse("admin:crm_generateddocument_add"))
    assert r.status_code == 302 and r["Location"] == reverse("admin:crm_generateddocument_new")


def test_buttons_on_property_and_client_redirect_with_selection(admin_client):
    prop = PropertyFactory()
    client = Client.objects.create(name="Ana")
    new = reverse("admin:crm_generateddocument_new")
    for name, obj, key in [
        ("admin:properties_property_generate_document_detail", prop, "property"),
        ("admin:properties_property_generate_document_row", prop, "property"),
        ("admin:crm_client_generate_document_detail", client, "client"),
        ("admin:crm_client_generate_document_row", client, "client"),
    ]:
        r = admin_client.get(reverse(name, args=[obj.pk]))
        assert r.status_code == 302 and r["Location"] == f"{new}?{key}={obj.pk}", name
    change = admin_client.get(reverse("admin:properties_property_change", args=[prop.pk]))
    assert reverse("admin:properties_property_generate_document_detail", args=[prop.pk]) in (
        change.content.decode()
    )


def test_template_admin_validates_body(admin_client):
    url = reverse("admin:crm_documenttemplate_add")
    bad = admin_client.post(
        url, {"name": "Ruim", "kind": "RECEIPT", "body": "{% debug %}", "is_active": "on"}
    )
    assert bad.status_code == 200 and DocumentTemplate.objects.count() == 0
    assert "não são permitidas" in bad.content.decode()
    ok = admin_client.post(
        url, {"name": "Bom", "kind": "RECEIPT", "body": "Olá {{ cliente.nome }}", "is_active": "on"}
    )
    assert ok.status_code == 302 and DocumentTemplate.objects.count() == 1


def _login(client, role, name):
    user = User.objects.create_user(name, password="pw")
    roles.apply_role(user, role)
    client.force_login(user)
    return user


def test_broker_generates_only_with_own_data_and_sees_own_history(client):
    user = _login(client, roles.BROKER, "corretor")
    mine = Broker.objects.create(name="Eu", user=user)
    other = Broker.objects.create(name="Outro")
    my_client = Client.objects.create(name="Meu cliente", broker=mine)
    foreign = Client.objects.create(name="Cliente alheio", broker=other)
    my_prop, foreign_prop = PropertyFactory(broker=mine), PropertyFactory(broker=other)
    tpl = make_template("Oi {{ cliente.nome }}")

    page = client.get(reverse("admin:crm_generateddocument_new")).content.decode()
    assert "Meu cliente" in page and "Cliente alheio" not in page
    assert my_prop.code in page and foreign_prop.code not in page
    bad = client.post(
        reverse("admin:crm_generateddocument_new"), {"template": tpl.pk, "client": foreign.pk}
    )
    assert bad.status_code == 200 and GeneratedDocument.objects.count() == 0

    r = client.post(
        reverse("admin:crm_generateddocument_new"), {"template": tpl.pk, "client": my_client.pk}
    )
    assert r.status_code == 302
    others = documents.generate(tpl, client=foreign)  # gerado por outra pessoa
    listing = client.get(reverse("admin:crm_generateddocument_changelist")).content.decode()
    assert "Meu cliente" in listing and "Cliente alheio" not in listing
    assert (
        client.get(reverse("admin:crm_generateddocument_print", args=[others.pk])).status_code
        == 404
    )


def test_roles_for_documents():
    for role, can_gen, can_edit in [
        (roles.ADMIN, True, True),
        (roles.MANAGER, True, True),
        (roles.BROKER, True, False),
        (roles.CLERK, True, False),
    ]:
        user = User.objects.create_user(role.lower(), password="pw")
        roles.apply_role(user, role)
        assert user.has_perm("crm.add_generateddocument") is can_gen, role
        assert user.has_perm("crm.view_documenttemplate"), role
        assert user.has_perm("crm.change_documenttemplate") is can_edit, role


def test_module_off_hides_documents(admin_client, settings):
    settings.SITE_FEATURES = ["searches"]
    assert admin_client.get(reverse("admin:crm_generateddocument_new")).status_code == 403
    assert admin_client.get(reverse("admin:crm_documenttemplate_changelist")).status_code == 403


def test_seed_demo_creates_templates(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    call_command("seed_demo")
    assert DocumentTemplate.objects.count() == 5
    call_command("seed_demo")
    assert DocumentTemplate.objects.count() == 5
