"""Geração de documentos a partir de modelos editáveis no painel.

O texto do modelo é editado por funcionários, então roda num engine de templates isolado e só
enxerga dicionários montados à mão (nunca models): ver `build_context`.
"""

import re
from urllib.parse import urlencode

from django.template import Context, Engine, TemplateSyntaxError
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from apps.core.features import enabled
from apps.core.models import SiteSettings

from .extenso import reais

MONTHS = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
    "outubro", "novembro", "dezembro",
]  # fmt: skip
FORBIDDEN = re.compile(r"\{%-?\s*(debug|include|extends|ssi)\b")

# Sem loaders (include/extends não encontram arquivo), só a biblioteca crm_docs e sem autoescape:
# quem escapa é `to_html`, uma vez, sobre o resultado inteiro.
_engine = Engine(
    loaders=[("django.template.loaders.locmem.Loader", {})],
    libraries={"crm_docs": "apps.crm.templatetags.crm_docs"},
    builtins=["apps.crm.templatetags.crm_docs"],
    autoescape=False,
)


class DocumentError(ValueError):
    """Modelo com erro de sintaxe ou com tag proibida."""


def _compile(body):
    if FORBIDDEN.search(body):
        raise DocumentError(
            "Tags {% debug %}, {% include %}, {% extends %} e {% ssi %} não são permitidas."
        )
    try:
        return _engine.from_string(body)
    except TemplateSyntaxError as exc:
        raise DocumentError(f"Erro no modelo: {exc}") from exc


def validate_body(body):
    _compile(body)


def brl(value):
    text = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {text}"


def _cpf(person):
    return getattr(person, "cpf", "") or ""


def _address(person):
    street = ", ".join(p for p in (person.street, person.number) if p)
    if person.complement:
        street = f"{street} ({person.complement})" if street else person.complement
    city = "/".join(p for p in (person.city, person.state) if p)
    parts = [street, person.neighborhood, city]
    text = " - ".join(p for p in parts if p)
    return f"{text}, CEP {person.zip_code}" if person.zip_code and text else text


def _spouse_dict(person):
    cpf = person.spouse_cpf
    nationality = person.spouse_nationality or person.nationality
    parts = [person.spouse_name, nationality, person.spouse_profession]
    text = ", ".join(p for p in parts if p)
    if text and cpf:
        text += f", CPF {cpf}"
    return {
        "nome": person.spouse_name,
        "cpf": cpf,
        "nacionalidade": person.spouse_nationality,
        "profissao": person.spouse_profession,
        "qualificacao": text if person.spouse_name else "",
    }


def _party(person, *, cpf=None):
    """Dados de uma parte do contrato (cliente, proprietário ou fiador) como dicionário."""
    empty = {
        "nome": "", "cpf": "", "nacionalidade": "", "estado_civil": "", "profissao": "",
        "endereco": "", "qualificacao": "", "conjuge": _spouse_dict_empty(),
    }  # fmt: skip
    if person is None:
        return empty
    cpf = cpf if cpf is not None else _cpf(person)
    marital = person.get_marital_status_display().lower() if person.marital_status else ""
    address = _address(person)
    parts = [person.name, person.nationality, marital, person.profession]
    text = ", ".join(p for p in parts if p)
    if cpf:
        text += f", CPF {cpf}"
    if address:
        text += f", residente e domiciliado(a) em {address}"
    spouse = _spouse_dict(person)
    if spouse["qualificacao"] and person.needs_spouse:
        text += f", e seu(sua) cônjuge {spouse['qualificacao']}"
    return {
        "nome": person.name,
        "cpf": cpf,
        "nacionalidade": person.nationality,
        "estado_civil": marital,
        "profissao": person.profession,
        "endereco": address,
        "qualificacao": text,
        "conjuge": spouse,
    }


def _spouse_dict_empty():
    return {"nome": "", "cpf": "", "nacionalidade": "", "profissao": "", "qualificacao": ""}


def spouse_warnings(kind, *, property=None, guarantor=None):
    """Avisos (não bloqueiam): parte casada sem cônjuge cadastrado, conforme o tipo de contrato."""
    from .models import DocumentTemplate

    warnings = []
    if kind == DocumentTemplate.Kind.RENTAL and guarantor is not None and guarantor.spouse_missing:
        warnings.append(
            "O fiador é casado: para o contrato ser válido é necessário incluir o(a) cônjuge."
        )
    owner = property.owner if property is not None else None
    if kind == DocumentTemplate.Kind.BROKERAGE and owner is not None and owner.spouse_missing:
        warnings.append(
            "O proprietário é casado: para o contrato ser válido é necessário incluir o(a) cônjuge."
        )
    return warnings


def build_context(*, client=None, property=None, guarantor=None, user=None, today=None):
    """Contexto só com dicionários e textos (nada de instâncias de model)."""
    today = today or timezone.localdate()
    site = SiteSettings.load()
    price = property.display_price if property else None
    broker = (user.get_full_name() or user.get_username()) if user else ""
    return {
        "cliente": {
            "nome": client.name if client else "",
            "whatsapp": client.whatsapp if client else "",
            "email": client.email if client else "",
            **_party(client),
        },
        "proprietario": _party(
            property.owner if property else None,
            cpf=(property.owner.cpf or property.owner.document)
            if property and property.owner
            else None,
        ),
        "fiador": _party(guarantor),
        "imovel": {
            "codigo": property.code if property else "",
            "titulo": property.title if property else "",
            "endereco": property.full_address if property else "",
            "categoria": property.category.name if property else "",
            "bairro": property.neighborhood.name if property else "",
            "cidade": property.neighborhood.city.name if property else "",
            "finalidade": property.get_purpose_display().lower() if property else "",
            "valor": brl(price) if price else "valor a combinar",
            "valor_numero": price or "",
            "valor_extenso": reais(price) if price else "",
        },
        "imobiliaria": {
            "nome": site.name,
            "creci": site.creci,
            "cnpj": site.cnpj,
            "telefone": site.phone,
            "email": site.email,
            "endereco": site.address,
        },
        "corretor": {"nome": broker},
        "data": f"{today:%d/%m/%Y}",
        "data_extenso": f"{today.day} de {MONTHS[today.month - 1]} de {today.year}",
    }


def to_html(text):
    """Texto simples → HTML seguro: `# Título`, parágrafos por linha em branco, <br> por linha."""
    blocks = []
    for block in re.split(r"\n\s*\n", text.strip().replace("\r\n", "\n")):
        block = block.strip("\n")
        if not block.strip():
            continue
        if block.startswith("# "):
            blocks.append(f"<h2>{escape(block[2:].strip())}</h2>")
        else:
            blocks.append("<p>" + "<br>".join(escape(line) for line in block.split("\n")) + "</p>")
    return "\n".join(blocks)


def render(template, context):
    """HTML seguro do documento (o texto renderizado é escapado inteiro, uma vez)."""
    # autoescape=False: quem escapa é `to_html`, uma vez só (senão o texto sai com &amp;lt;)
    return to_html(_compile(template.body).render(Context(context, autoescape=False)))


def generate(template, *, client=None, property=None, guarantor=None, user=None):
    from .models import GeneratedDocument

    html = render(
        template,
        build_context(client=client, property=property, guarantor=guarantor, user=user),
    )
    return GeneratedDocument.objects.create(
        template=template,
        title=template.name,
        client=client,
        property=property,
        generated_by=user,
        html=html,
    )


def new_document_url(*, property=None, client=None):
    query = {k: v.pk for k, v in (("property", property), ("client", client)) if v}
    return reverse("admin:crm_generateddocument_new") + (f"?{urlencode(query)}" if query else "")


def can_generate(request):
    return enabled("crm") and request.user.has_perm("crm.add_generateddocument")
