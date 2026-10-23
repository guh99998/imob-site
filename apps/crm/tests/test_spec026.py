import hashlib

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.crm import documents, services
from apps.crm.base_templates import BASE_TEMPLATES, LEGACY_HASHES, ensure_base_templates
from apps.crm.models import Client, DocumentTemplate, GeneratedDocument
from apps.people import roles
from apps.people.models import Broker, Guarantor, Owner
from apps.properties.tests.factories import PropertyFactory

from .test_spec020 import _make_user

pytestmark = pytest.mark.django_db
CPF = "529.982.247-25"
CPF2 = "111.444.777-35"
M = Owner.MaritalStatus


def _template(kind, body="x"):
    return DocumentTemplate.objects.create(name=f"T {kind}", kind=kind, body=body)


def _married_guarantor(**kw):
    return Guarantor.objects.create(
        name="Gilberto Fiador", cpf=CPF, marital_status=M.MARRIED, profession="contador", **kw
    )


# ---------- modelo ----------


def test_cpf_is_validated_on_all_parties():
    for obj in (Client(name="A", cpf="123"), Owner(name="A", spouse_cpf="123")):
        with pytest.raises(ValidationError) as exc:
            obj.full_clean()
        assert any("CPF" in m for m in sum(exc.value.message_dict.values(), []))
    Guarantor(name="G", cpf=CPF).full_clean()


def test_spouse_flags():
    g = Guarantor(name="G", marital_status=M.SINGLE)
    assert not g.needs_spouse and not g.spouse_missing
    g.marital_status = M.STABLE_UNION
    assert g.needs_spouse and g.spouse_missing
    g.spouse_name, g.spouse_cpf = "Maria", CPF2
    assert g.has_spouse and not g.spouse_missing


# ---------- contexto dos documentos ----------


def test_qualification_text_and_spouse_in_context():
    g = _married_guarantor(
        street="Rua A",
        number="10",
        neighborhood="Centro",
        city="Santos",
        state="SP",
        zip_code="11000-000",
        spouse_name="Maria Fiadora",
        spouse_cpf=CPF2,
        spouse_profession="médica",
    )
    ctx = documents.build_context(guarantor=g)
    text = ctx["fiador"]["qualificacao"]
    assert "Gilberto Fiador, brasileiro(a), casado(a), contador, CPF 529.982.247-25" in text
    assert "residente e domiciliado(a) em Rua A, 10 - Centro - Santos/SP, CEP 11000-000" in text
    assert "cônjuge Maria Fiadora" in text and CPF2 in text
    assert ctx["fiador"]["conjuge"]["nome"] == "Maria Fiadora"


def test_context_is_dicts_only_and_empty_parties_are_safe():
    ctx = documents.build_context()
    for key in ("cliente", "proprietario", "fiador"):
        assert isinstance(ctx[key], dict) and ctx[key]["qualificacao"] == ""
        assert isinstance(ctx[key]["conjuge"], dict)

    def check(value):
        assert isinstance(value, dict | str | int | float | type(None)) or hasattr(
            value, "quantize"
        )
        if isinstance(value, dict):
            for v in value.values():
                check(v)

    owner = Owner.objects.create(name="Dono", document=CPF)
    ctx = documents.build_context(
        client=Client.objects.create(name="Ana"), property=PropertyFactory(owner=owner)
    )
    check(ctx)
    assert ctx["proprietario"]["cpf"] == CPF  # cai para `document` quando não há `cpf`


def test_owner_cpf_has_priority_over_document():
    owner = Owner.objects.create(name="Dono", document="11.222.333/0001-81", cpf=CPF)
    ctx = documents.build_context(property=PropertyFactory(owner=owner))
    assert ctx["proprietario"]["cpf"] == CPF


# ---------- avisos do cônjuge ----------


def test_warning_guarantor_married_without_spouse_only_in_rental():
    g = _married_guarantor()
    rental = documents.spouse_warnings(DocumentTemplate.Kind.RENTAL, guarantor=g)
    assert rental == [
        "O fiador é casado: para o contrato ser válido é necessário incluir o(a) cônjuge."
    ]
    assert not documents.spouse_warnings(DocumentTemplate.Kind.VISIT, guarantor=g)
    g.spouse_name, g.spouse_cpf = "Maria", CPF2
    assert not documents.spouse_warnings(DocumentTemplate.Kind.RENTAL, guarantor=g)


def test_warning_owner_in_brokerage_but_not_rental_or_buyer():
    owner = Owner.objects.create(name="Dono", marital_status=M.MARRIED)
    prop = PropertyFactory(owner=owner)
    brokerage = documents.spouse_warnings(DocumentTemplate.Kind.BROKERAGE, property=prop)
    assert len(brokerage) == 1 and "proprietário é casado" in brokerage[0]
    assert not documents.spouse_warnings(DocumentTemplate.Kind.RENTAL, property=prop)
    assert not documents.spouse_warnings(DocumentTemplate.Kind.PROPOSAL, property=prop)


def test_buyer_or_tenant_never_triggers_warning():
    prop = PropertyFactory()
    assert not documents.spouse_warnings(DocumentTemplate.Kind.RENTAL, property=prop)
    assert not documents.spouse_warnings(DocumentTemplate.Kind.BROKERAGE, property=prop)


# ---------- tela de gerar ----------


def _post(admin_client, tpl, prop, guarantor, **extra):
    data = {"template": tpl.pk, "property": prop.pk, "guarantor": guarantor.pk, **extra}
    return admin_client.post(reverse("admin:crm_generateddocument_new"), data)


def test_generate_warns_then_allows_confirmation(admin_client):
    tpl = _template(DocumentTemplate.Kind.RENTAL, "Fiador: {{ fiador.qualificacao }}")
    g = _married_guarantor()
    prop = PropertyFactory()
    r = _post(admin_client, tpl, prop, g)
    assert r.status_code == 200 and "O fiador é casado" in r.content.decode()
    assert not GeneratedDocument.objects.exists()
    r = _post(admin_client, tpl, prop, g, confirm="1")
    assert r.status_code == 302 and GeneratedDocument.objects.count() == 1


def test_generate_with_spouse_has_no_warning_and_spouse_in_text(admin_client):
    tpl = _template(DocumentTemplate.Kind.RENTAL, "Fiador: {{ fiador.qualificacao }}")
    g = _married_guarantor(spouse_name="Maria Fiadora", spouse_cpf=CPF2)
    r = _post(admin_client, tpl, PropertyFactory(), g)
    assert r.status_code == 302
    assert "Maria Fiadora" in GeneratedDocument.objects.get().html


def test_broker_only_sees_own_guarantors(client):
    user = _make_user(roles.BROKER, "corretor")
    Broker.objects.create(name="Eu", user=user)
    mine = Guarantor.objects.create(name="Meu Fiador", created_by=user)
    other = Guarantor.objects.create(name="Fiador Alheio")
    client.force_login(user)
    html = client.get(reverse("admin:people_guarantor_changelist")).content.decode()
    assert "Meu Fiador" in html and "Fiador Alheio" not in html
    assert client.get(reverse("admin:people_guarantor_change", args=[other.pk])).status_code in (
        302,
        404,
    )
    form = client.get(reverse("admin:crm_generateddocument_new")).context["form"]
    assert list(form.fields["guarantor"].queryset) == [mine]


def test_guarantor_created_by_is_set_in_admin(admin_client, admin_user):
    r = admin_client.post(
        reverse("admin:people_guarantor_add"),
        {"name": "Novo", "nationality": "brasileiro(a)", "marital_status": "SINGLE"},
    )
    assert r.status_code == 302
    assert Guarantor.objects.get().created_by == admin_user


# ---------- fichas ----------


def test_person_pages_render_and_show_spouse_notice(admin_client):
    g = _married_guarantor()
    owner = Owner.objects.create(name="Dono", marital_status=M.MARRIED)
    crm = Client.objects.create(name="Ana", marital_status=M.MARRIED)
    for url in (
        reverse("admin:people_guarantor_change", args=[g.pk]),
        reverse("admin:people_owner_change", args=[owner.pk]),
        reverse("admin:crm_client_change", args=[crm.pk]),
        reverse("admin:people_guarantor_add"),
    ):
        r = admin_client.get(url)
        assert r.status_code == 200
    html = admin_client.get(reverse("admin:people_guarantor_change", args=[g.pk])).content.decode()
    assert "informe nome e CPF do cônjuge" in html


def test_guarantor_in_sidebar(admin_client):
    assert (
        reverse("admin:people_guarantor_changelist") in admin_client.get("/admin/").content.decode()
    )


def test_guarantor_permissions_for_roles():
    assert _make_user(roles.BROKER, "c").has_perm("people.add_guarantor")
    assert _make_user(roles.MANAGER, "g").has_perm("people.delete_guarantor")
    assert not _make_user(roles.CLERK, "a").has_perm("people.view_guarantor")


# ---------- LGPD ----------


def test_anonymize_wipes_qualification():
    crm = Client.objects.create(
        name="Ana",
        cpf=CPF,
        profession="x",
        street="Rua",
        spouse_name="Beto",
        spouse_cpf=CPF2,
        marital_status=M.MARRIED,
    )
    services.anonymize(crm)
    crm.refresh_from_db()
    for field in services.PERSONAL_QUALIFICATION_FIELDS:
        assert getattr(crm, field) == "", field


# ---------- modelos-base ----------


def test_base_templates_render_with_qualification():
    owner = Owner.objects.create(name="Dono", cpf=CPF, marital_status=M.SINGLE)
    prop = PropertyFactory(owner=owner)
    crm = Client.objects.create(name="Ana", cpf=CPF2, profession="engenheira")
    g = _married_guarantor(spouse_name="Maria Fiadora", spouse_cpf=CPF2)
    for kind, name, body in BASE_TEMPLATES:
        tpl = DocumentTemplate(name=name, kind=kind, body=body)
        tpl.full_clean()
        html = documents.render(
            tpl, documents.build_context(client=crm, property=prop, guarantor=g)
        )
        assert "{{" not in html and "{%" not in html, name
        if kind == DocumentTemplate.Kind.RENTAL:
            assert "Maria Fiadora" in html and "engenheira" in html and "Dono" in html
        if kind == DocumentTemplate.Kind.BROKERAGE:
            assert "Dono" in html


def test_ensure_updates_only_untouched_legacy_templates(monkeypatch):
    kind, name, new_body = next(t for t in BASE_TEMPLATES if t[0] == DocumentTemplate.Kind.RENTAL)
    untouched = DocumentTemplate.objects.create(name=name, kind=kind, body="texto antigo")
    monkeypatch.setitem(LEGACY_HASHES, (kind, name), hashlib.sha256(b"texto antigo").hexdigest())
    ensure_base_templates()
    untouched.refresh_from_db()
    assert untouched.body == new_body

    untouched.body = "editado pelo cliente"
    untouched.save()
    ensure_base_templates()
    untouched.refresh_from_db()
    assert untouched.body == "editado pelo cliente"
