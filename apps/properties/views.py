from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, When
from django.shortcuts import get_object_or_404, redirect, render

from apps.core import seo
from apps.leads.forms import LeadForm

from .filters import PropertyFilter
from .models import Category, City, Property

PAGE_SIZE = 12  # 4 linhas de 3 no desktop; leve no celular (fotos com lazy loading)


def _base_qs():
    return (
        Property.objects.published()
        .select_related("category", "neighborhood__city")
        .prefetch_related("photos")
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
        if isinstance(value, str) and hasattr(field, "choices"):
            value = dict(field.choices).get(value, value)
        params = request.GET.copy()
        params.pop(name, None)
        params.pop("page", None)
        chips.append(
            {"label": f"{field.label}: {value}", "url": f"?{params.urlencode()}" if params else "?"}
        )
    return chips


def property_list(request, landing=None):
    code = request.GET.get("code", "").strip()
    if code:
        found = Property.objects.published().filter(code__iexact=code).first()
        if found:
            return redirect(found.get_absolute_url())
    data = request.GET.copy()
    data.pop("code", None)
    if landing:
        data["purpose"] = landing["purpose"]
        data["category"] = landing["category"].slug
        if landing.get("city"):
            data["city"] = str(landing["city"].pk)
    f = PropertyFilter(data or None, queryset=_base_qs())
    paginator = Paginator(f.qs, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    ctx = {
        "filter": f,
        "page": page,
        "page_range": paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1),
        "querystring": params.urlencode(),
        "chips": _active_filters(f, request),
        "landing": landing,
        "code_not_found": code,
        # Só a lista "limpa" e as landings sem filtros extras são indexáveis.
        "noindex": bool(request.GET),
    }
    template = "properties/partials/results.html" if request.htmx else "properties/list.html"
    return render(request, template, ctx)


def landing(request, kind, category, city=None):
    cat = get_object_or_404(Category, slug=category)
    city_obj = get_object_or_404(City, slug=city) if city else None
    purpose = Property.Purpose.SALE if kind == "comprar" else Property.Purpose.RENT
    info = {
        "purpose": purpose,
        "category": cat,
        "city": city_obj,
        "verb": "à venda" if kind == "comprar" else "para alugar",
    }
    where = f" em {city_obj.name}/{city_obj.state}" if city_obj else ""
    info["title"] = f"{cat.name} {info['verb']}{where}"
    return property_list(request, landing=info)


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
    photos = list(prop.photos.all())
    return render(
        request,
        "properties/detail.html",
        {
            "property": prop,
            "form": LeadForm(),
            "photos": photos,
            "gallery": seo.dumps(
                [{"src": ph.src_lg, "alt": ph.caption or prop.title} for ph in photos]
            ),
            "jsonld": seo.listing(request, prop, photos),
            "similar": similar,
        },
    )
