import django_filters as filters
from django import forms
from django.core.exceptions import ValidationError

from apps.core.widgets import parse_br_decimal

from .models import Category, City, Neighborhood, Property

PRICE_ATTRS = {"class": "field", "inputmode": "numeric", "data-mask": "money"}

ORDERING_CHOICES = [
    ("-published_at", "Mais recentes"),
    ("price", "Menor preço"),
    ("-price", "Maior preço"),
    ("-area_total", "Maior área"),
]


CATEGORY_GROUPS = [
    (
        "Residencial",
        [
            "apartamento",
            "casa",
            "sobrado",
            "casa-de-condominio",
            "cobertura",
            "studio-kitnet",
            "flat",
        ],
    ),
    ("Terrenos e rurais", ["terreno", "terreno-em-condominio", "chacara-sitio", "fazenda"]),
    ("Comercial", ["comercial", "sala-comercial", "loja", "galpao"]),
]


def grouped_categories():
    """[(rótulo, [categorias])] — categorias fora dos grupos conhecidos vão para "Outras"."""
    cats = list(Category.objects.all())
    used, groups = set(), []
    for label, slugs in CATEGORY_GROUPS:
        items = [c for c in cats if c.slug in slugs]
        used.update(c.pk for c in items)
        if items:
            groups.append((label, items))
    rest = [c for c in cats if c.pk not in used]
    if rest:
        groups.append(("Outras", rest))
    return groups


class PropertyFilter(filters.FilterSet):
    purpose = filters.ChoiceFilter(
        label="Finalidade",
        method="filter_purpose",
        choices=Property.Purpose.choices[:2],
        empty_label="Todas",
    )
    category = filters.ModelChoiceFilter(
        label="Categoria",
        queryset=Category.objects.all(),
        to_field_name="slug",
        empty_label="Todas",
    )
    city = filters.ModelChoiceFilter(
        label="Cidade",
        field_name="neighborhood__city",
        queryset=City.objects.all(),
        empty_label="Todas",
    )
    neighborhood = filters.ModelChoiceFilter(
        label="Bairro", queryset=Neighborhood.objects.select_related("city"), empty_label="Todos"
    )
    min_price = filters.CharFilter(
        label="Preço mín.", method="filter_min_price", widget=forms.TextInput(PRICE_ATTRS)
    )
    max_price = filters.CharFilter(
        label="Preço máx.", method="filter_max_price", widget=forms.TextInput(PRICE_ATTRS)
    )
    bedrooms = filters.NumberFilter(
        label="Quartos (mín.)", field_name="bedrooms", lookup_expr="gte"
    )
    parking_spaces = filters.NumberFilter(
        label="Vagas (mín.)", field_name="parking_spaces", lookup_expr="gte"
    )
    min_area = filters.NumberFilter(
        label="Área mín. (m²)", field_name="area_total", lookup_expr="gte"
    )
    max_area = filters.NumberFilter(
        label="Área máx. (m²)", field_name="area_total", lookup_expr="lte"
    )
    order = filters.ChoiceFilter(
        label="Ordenar por", choices=ORDERING_CHOICES, method="filter_order", empty_label=None
    )

    class Meta:
        model = Property
        fields = []

    def __init__(self, data=None, queryset=None, **kwargs):
        super().__init__(data, queryset, **kwargs)
        self.form.fields["category"].widget.choices = [("", "Todas")] + [
            (label, [(c.slug, c.name) for c in items]) for label, items in grouped_categories()
        ]
        for field in self.form.fields.values():
            if isinstance(field.widget, (forms.Select, forms.NumberInput)):
                field.widget.attrs.setdefault("class", "field")

    # O preço "efetivo" depende da finalidade escolhida.
    def _price_field(self):
        purpose = self.data.get("purpose") if self.data else None
        return "rent_price" if purpose == Property.Purpose.RENT else "sale_price"

    def filter_purpose(self, queryset, name, value):
        if value == Property.Purpose.SALE:
            return queryset.filter(purpose__in=[Property.Purpose.SALE, Property.Purpose.BOTH])
        if value == Property.Purpose.RENT:
            return queryset.filter(purpose__in=[Property.Purpose.RENT, Property.Purpose.BOTH])
        return queryset

    def _price(self, value):
        try:
            return parse_br_decimal(value)
        except ValidationError:
            return None

    def filter_min_price(self, queryset, name, value):
        price = self._price(value)
        if price is None:
            return queryset
        return queryset.filter(**{f"{self._price_field()}__gte": price})

    def filter_max_price(self, queryset, name, value):
        price = self._price(value)
        if price is None:
            return queryset
        return queryset.filter(**{f"{self._price_field()}__lte": price})

    def filter_order(self, queryset, name, value):
        if value in ("price", "-price"):
            field = self._price_field()
            return queryset.order_by(("-" if value.startswith("-") else "") + field, "-id")
        return queryset.order_by(value, "-id")
