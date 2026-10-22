import django_filters as filters
from django import forms

from .models import Category, City, Neighborhood, Property

ORDERING_CHOICES = [
    ("-published_at", "Mais recentes"),
    ("price", "Menor preço"),
    ("-price", "Maior preço"),
    ("-area_total", "Maior área"),
]


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
    min_price = filters.NumberFilter(label="Preço mín.", method="filter_min_price")
    max_price = filters.NumberFilter(label="Preço máx.", method="filter_max_price")
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

    def filter_min_price(self, queryset, name, value):
        return queryset.filter(**{f"{self._price_field()}__gte": value})

    def filter_max_price(self, queryset, name, value):
        return queryset.filter(**{f"{self._price_field()}__lte": value})

    def filter_order(self, queryset, name, value):
        if value in ("price", "-price"):
            field = self._price_field()
            return queryset.order_by(("-" if value.startswith("-") else "") + field, "-id")
        return queryset.order_by(value, "-id")
