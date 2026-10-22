from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, When
from django.shortcuts import get_object_or_404, render

from apps.leads.forms import LeadForm

from .filters import PropertyFilter
from .models import Property


def _base_qs():
    return (
        Property.objects.published().select_related("neighborhood__city").prefetch_related("photos")
    )


def _active_filters(f, request):
    """Chips dos filtros ativos, cada um com a URL que o remove."""
    chips = []
    if not f.is_bound:
        return chips
    for name, field in f.form.fields.items():
        value = f.form.cleaned_data.get(name) if hasattr(f.form, "cleaned_data") else None
        if name == "order" or value in (None, ""):
            continue
        if isinstance(value, str):
            value = dict(field.choices).get(value, value)
        params = request.GET.copy()
        params.pop(name, None)
        params.pop("page", None)
        chips.append(
            {"label": f"{field.label}: {value}", "url": f"?{params.urlencode()}" if params else "?"}
        )
    return chips


def property_list(request):
    f = PropertyFilter(request.GET or None, queryset=_base_qs())
    page = Paginator(f.qs, 12).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    ctx = {
        "filter": f,
        "page": page,
        "querystring": params.urlencode(),
        "chips": _active_filters(f, request),
    }
    template = "properties/partials/results.html" if request.htmx else "properties/list.html"
    return render(request, template, ctx)


def property_detail(request, slug):
    prop = get_object_or_404(_base_qs().prefetch_related("features"), slug=slug)
    similar = (
        _base_qs()
        .filter(Q(category=prop.category) | Q(neighborhood__city=prop.neighborhood.city))
        .exclude(pk=prop.pk)
        .annotate(
            same_category=Case(
                When(category=prop.category, then=0), default=1, output_field=IntegerField()
            )
        )
        .order_by("same_category", "-published_at")[:3]
    )
    return render(
        request,
        "properties/detail.html",
        {
            "property": prop,
            "form": LeadForm(),
            "photos": list(prop.photos.all()),
            "similar": similar,
        },
    )
