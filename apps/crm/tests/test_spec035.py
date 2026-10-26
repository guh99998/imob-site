import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.crm import documents
from apps.crm.models import Client, DocumentTemplate, GeneratedDocument
from apps.people import roles
from apps.people.models import Broker

pytestmark = pytest.mark.django_db
User = get_user_model()

BODY = "# RECIBO\n\nRecebi de {{ cliente.nome }} a quantia de R$ 1.000,00.\nLocal e data."


@pytest.fixture
def admin_client(client):
    client.force_login(User.objects.create_superuser("admin", "a@a.com", "pw"))
    return client


@pytest.fixture
def doc(admin_client):
    crm = Client.objects.create(name="Maria Cliente")
    template = DocumentTemplate.objects.create(name="Recibo", kind="RECEIPT", body=BODY)
    return documents.generate(template, client=crm)


def edit_url(doc):
    return reverse("admin:crm_generateddocument_edit", args=[doc.pk])


def test_print_page_offers_editing_to_who_can_generate(admin_client, doc):
    html = admin_client.get(
        reverse("admin:crm_generateddocument_print", args=[doc.pk])
    ).content.decode()
    assert 'id="doc-body"' in html and "Editar texto" in html and "Salvar alterações" in html
    assert "Maria Cliente" in html and "Restaurar original" not in html


def test_edit_replaces_text_keeps_original_and_escapes_html(admin_client, doc):
    original = doc.html
    r = admin_client.post(
        edit_url(doc), {"text": "# RECIBO\n\nRecebi R$ 2.500,00 <script>alert(1)</script>\nLinha 2"}
    )
    assert r.status_code == 200 and r.json()["ok"] is True
    doc.refresh_from_db()
    assert "2.500,00" in doc.html and "<h2>RECIBO</h2>" in doc.html and "Linha 2" in doc.html
    assert "<script>" not in doc.html and "&lt;script&gt;" in doc.html
    assert doc.original_html == original and doc.edited_at


def test_second_edit_keeps_the_first_original(admin_client, doc):
    original = doc.html
    admin_client.post(edit_url(doc), {"text": "Primeira edição"})
    admin_client.post(edit_url(doc), {"text": "Segunda edição"})
    doc.refresh_from_db()
    assert "Segunda" in doc.html and doc.original_html == original


def test_restore_original(admin_client, doc):
    original = doc.html
    admin_client.post(edit_url(doc), {"text": "Outro texto"})
    r = admin_client.post(reverse("admin:crm_generateddocument_restore", args=[doc.pk]))
    assert r.status_code == 302
    doc.refresh_from_db()
    assert doc.html == original and doc.original_html == "" and doc.edited_at is None
    html = admin_client.get(
        reverse("admin:crm_generateddocument_print", args=[doc.pk])
    ).content.decode()
    assert "Restaurar original" not in html


def test_print_page_shows_restore_after_edit(admin_client, doc):
    admin_client.post(edit_url(doc), {"text": "Outro texto"})
    html = admin_client.get(
        reverse("admin:crm_generateddocument_print", args=[doc.pk])
    ).content.decode()
    assert "Restaurar original" in html and "Texto editado em" in html


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("", id="vazio"),
        pytest.param("   \n  ", id="so-espacos"),
        pytest.param("x" * 200_001, id="grande"),
    ],
)
def test_empty_or_huge_text_is_refused(admin_client, doc, text):
    before = doc.html
    r = admin_client.post(edit_url(doc), {"text": text})
    assert r.status_code == 400 and r.json()["ok"] is False
    doc.refresh_from_db()
    assert doc.html == before and doc.edited_at is None


def test_edit_and_restore_are_post_only(admin_client, doc):
    assert admin_client.get(edit_url(doc)).status_code == 405
    assert (
        admin_client.get(reverse("admin:crm_generateddocument_restore", args=[doc.pk])).status_code
        == 405
    )


def test_other_brokers_document_is_not_editable(client):
    owner = User.objects.create_user("dono", password="pw", is_staff=True)
    roles.apply_role(owner, roles.BROKER)
    Broker.objects.create(name="Dono", user=owner)
    template = DocumentTemplate.objects.create(name="Recibo", kind="RECEIPT", body=BODY)
    doc = documents.generate(template, user=owner)
    other = User.objects.create_user("outro", password="pw", is_staff=True)
    roles.apply_role(other, roles.BROKER)
    client.force_login(other)
    assert client.post(edit_url(doc), {"text": "invasão"}).status_code == 404
    client.force_login(owner)
    assert client.post(edit_url(doc), {"text": "meu texto"}).status_code == 200


def test_view_only_user_cannot_edit(client, doc):
    viewer = User.objects.create_user("leitor", password="pw", is_staff=True)
    from django.contrib.auth.models import Permission

    viewer.user_permissions.add(Permission.objects.get(codename="view_generateddocument"))
    client.force_login(viewer)
    assert client.post(edit_url(doc), {"text": "x"}).status_code == 403
    html = client.get(reverse("admin:crm_generateddocument_print", args=[doc.pk])).content.decode()
    assert "Editar texto" not in html and 'id="doc-edit"' not in html


def test_history_marks_edited_documents(admin_client, doc):
    admin_client.post(edit_url(doc), {"text": "Outro texto"})
    html = admin_client.get(reverse("admin:crm_generateddocument_changelist")).content.decode()
    assert "Editado" in html
    assert GeneratedDocument.objects.filter(edited_at__isnull=False).count() == 1
