"""Filtros do painel em "Pesquisa avançada": em linha, logo abaixo da busca.

O ModelAdmin continua declarando `list_filter` com nomes de campo; o mixin troca cada um
pelo filtro dropdown do Unfold adequado ao tipo do campo e marca todos como horizontais.
"""

from django.contrib.admin.utils import get_fields_from_path
from django.db import models
from unfold.contrib.filters.admin import (
    BooleanRadioFilter,
    ChoicesDropdownFilter,
    RangeDateFilter,
    RelatedDropdownFilter,
)


class _AllHorizontal(dict):
    """Responde "horizontal" para qualquer filtro (o Unfold usa `in`, `[]` e `.get`)."""

    def __contains__(self, key):
        return True

    def __getitem__(self, key):
        return {"horizontal": True}

    def get(self, key, default=None):
        return {"horizontal": True}


def dropdown_filter(model, path):
    field = get_fields_from_path(model, path)[-1]
    if field.is_relation:
        return (path, RelatedDropdownFilter)
    if isinstance(field, models.BooleanField):
        return (path, BooleanRadioFilter)
    if isinstance(field, models.DateField):
        return (path, RangeDateFilter)
    if field.choices:
        return (path, ChoicesDropdownFilter)
    return path


class AdvancedSearchMixin:
    list_before_template = "admin/partials/advanced_search.html"
    list_filter_options = _AllHorizontal()

    def get_list_filter(self, request):
        return [
            dropdown_filter(self.model, f) if isinstance(f, str) else f
            for f in super().get_list_filter(request)
        ]
