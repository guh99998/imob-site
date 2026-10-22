from django.db.models import Count, Q
from django.shortcuts import render

from apps.properties.models import Category, City, Neighborhood, Property

PUBLIC = ~Q(properties__status=Property.Status.DRAFT)


def home(request):
    qs = (
        Property.objects.published().select_related("neighborhood__city").prefetch_related("photos")
    )
    featured = list(qs.filter(is_featured=True)[:6])
    categories = list(
        Category.objects.annotate(total=Count("properties", filter=PUBLIC))
        .filter(total__gt=0)
        .order_by("order", "name")
    )
    for cat in categories:
        cat.sample = qs.filter(category=cat).first()
    cities = City.objects.annotate(
        total=Count(
            "neighborhoods__properties",
            filter=~Q(neighborhoods__properties__status=Property.Status.DRAFT),
        )
    ).filter(total__gt=0)
    neighborhoods = (
        Neighborhood.objects.select_related("city")
        .annotate(total=Count("properties", filter=PUBLIC))
        .filter(total__gt=0)
        .order_by("-total", "name")[:8]
    )
    return render(
        request,
        "core/home.html",
        {
            "featured": featured,
            "highlights": list(featured[:3]) or list(qs[:3]),
            "recent": qs[:6],
            "categories": categories,
            "category_choices": Category.objects.all(),
            "city_choices": City.objects.all(),
            "cities": cities,
            "neighborhoods": neighborhoods,
        },
    )
