from django import template

from apps.crm.extenso import reais

register = template.Library()


@register.filter
def valor_por_extenso(value):
    """{{ 1500|valor_por_extenso }} → "mil e quinhentos reais"."""
    return reais(value)
