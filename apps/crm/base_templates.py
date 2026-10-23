"""Modelos-base (exemplos): o cliente revisa com o jurídico antes de usar."""

from .models import DocumentTemplate

KIND = DocumentTemplate.Kind
NOTICE = "Modelo de exemplo: revise com seu jurídico antes de usar."

HEADER = ""  # nome, CRECI e CNPJ já saem no cabeçalho da página de impressão
SIGN = """

______________________________
{{ cliente.nome }}

______________________________
{{ imobiliaria.nome }}{% if corretor.nome %} — {{ corretor.nome }}{% endif %}
"""

BASE_TEMPLATES = [
    (
        KIND.VISIT,
        "Termo de visita",
        """# TERMO DE VISITA

"""
        + HEADER
        + """
Eu, {{ cliente.nome }}, declaro que visitei em {{ data }}, acompanhado(a) por representante da imobiliária, o imóvel {{ imovel.codigo }} — {{ imovel.titulo }}, situado em {{ imovel.endereco }}, anunciado por {{ imovel.valor }}.

Declaro ainda que:
1. as informações sobre o imóvel me foram apresentadas pela imobiliária;
2. a visita não gera obrigação de compra ou de locação;
3. qualquer negociação sobre este imóvel será feita por intermédio de {{ imobiliaria.nome }}.

{{ data_extenso }}.
"""
        + SIGN,
    ),
    (
        KIND.PROPOSAL,
        "Proposta de compra ou locação",
        """# PROPOSTA

"""
        + HEADER
        + """
{{ cliente.nome }} apresenta proposta para o imóvel {{ imovel.codigo }} — {{ imovel.titulo }}, situado em {{ imovel.endereco }}, anunciado por {{ imovel.valor }}{% if imovel.valor_extenso %} ({{ imovel.valor_extenso }}){% endif %}.

Valor proposto: R$ ______________ (______________________________________).
Forma de pagamento: ______________________________________.
Prazo de validade da proposta: ______ dias, a contar de {{ data }}.

A proposta não obriga o proprietário e só se confirma com a assinatura do contrato.

{{ data_extenso }}.
"""
        + SIGN,
    ),
    (
        KIND.RENTAL,
        "Contrato de locação (exemplo)",
        """# CONTRATO DE LOCAÇÃO

"""
        + HEADER
        + """
LOCATÁRIO(A): {{ cliente.nome }}, WhatsApp {{ cliente.whatsapp }}.
IMÓVEL: {{ imovel.codigo }} — {{ imovel.titulo }}, situado em {{ imovel.endereco }}.

CLÁUSULA 1ª — O prazo da locação é de ______ meses, com início em ____/____/______.

CLÁUSULA 2ª — O aluguel mensal é de {{ imovel.valor }}{% if imovel.valor_extenso %} ({{ imovel.valor_extenso }}){% endif %}, a ser pago até o dia ____ de cada mês.

CLÁUSULA 3ª — O imóvel destina-se exclusivamente ao uso ________________, sendo vedada a sublocação sem autorização por escrito.

CLÁUSULA 4ª — Garantia da locação: ______________________________.

CLÁUSULA 5ª — O LOCATÁRIO devolverá o imóvel nas mesmas condições em que o recebeu, ressalvado o desgaste natural.

{{ data_extenso }}.
"""
        + SIGN,
    ),
    (
        KIND.BROKERAGE,
        "Contrato de intermediação (exemplo)",
        """# CONTRATO DE INTERMEDIAÇÃO IMOBILIÁRIA

"""
        + HEADER
        + """
CONTRATANTE: {{ cliente.nome }}, WhatsApp {{ cliente.whatsapp }}, e-mail {{ cliente.email }}.
IMÓVEL: {{ imovel.codigo }} — {{ imovel.titulo }}, situado em {{ imovel.endereco }}.

CLÁUSULA 1ª — O CONTRATANTE autoriza {{ imobiliaria.nome }}{% if imobiliaria.cnpj %}, CNPJ {{ imobiliaria.cnpj }}{% endif %}, a intermediar a {{ imovel.finalidade }} do imóvel pelo valor de {{ imovel.valor }}{% if imovel.valor_extenso %} ({{ imovel.valor_extenso }}){% endif %}.

CLÁUSULA 2ª — A comissão é de ______ % sobre o valor do negócio, devida quando ele for concluído.

CLÁUSULA 3ª — A autorização vale por ______ dias, com exclusividade: ( ) sim  ( ) não.

CLÁUSULA 4ª — O CONTRATANTE declara ser o titular do imóvel ou ter poderes para negociá-lo.

{{ data_extenso }}.
"""
        + SIGN,
    ),
    (
        KIND.RECEIPT,
        "Recibo",
        """# RECIBO

"""
        + HEADER
        + """
Recebi de {{ cliente.nome }} a quantia de R$ ______________ (______________________________________), referente a ______________________________________, relativa ao imóvel {{ imovel.codigo }} — {{ imovel.titulo }}.

Por ser verdade, firmo o presente recibo.

{{ data_extenso }}.
"""
        + SIGN,
    ),
]


def ensure_base_templates():
    """Cria os modelos-base que ainda não existem (por tipo + nome). Devolve quantos criou."""
    created = 0
    for kind, name, body in BASE_TEMPLATES:
        _obj, new = DocumentTemplate.objects.get_or_create(
            kind=kind, name=name, defaults={"body": body, "description": NOTICE}
        )
        created += new
    return created
