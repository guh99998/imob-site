from django.conf import settings
from django.db.models import Count, Q
from django.shortcuts import render
from django.urls import reverse

from apps.leads.forms import LeadForm
from apps.leads.models import Lead
from apps.leads.views import lead_page
from apps.properties.filters import grouped_categories
from apps.properties.models import PUBLIC_STATUSES, Category, City, Neighborhood, Property
from apps.properties.searches import popular

from . import seo
from .models import SiteSettings

PUBLIC = Q(properties__status__in=PUBLIC_STATUSES)


def home(request):
    site = SiteSettings.load()
    qs = (
        Property.objects.published()
        .select_related("category", "neighborhood__city")
        .prefetch_related("photos")
    )
    featured = list(qs.filter(is_featured=True)[: settings.MAX_FEATURED])
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
            filter=Q(neighborhoods__properties__status__in=PUBLIC_STATUSES),
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
            "jsonld": seo.agency(request, site),
            "featured": featured,
            "highlights": featured[:3] or list(qs[:3]),
            "recent": qs[:6],
            "categories": categories,
            "category_groups": grouped_categories(),
            "city_choices": City.objects.all(),
            "neighborhood_groups": City.objects.prefetch_related("neighborhoods"),
            "listing_form": LeadForm(),
            "listing_action": reverse("core:advertise"),
            "cities": cities,
            "neighborhoods": neighborhoods,
            "popular_searches": popular(),
        },
    )


def advertise(request):
    return lead_page(request, Lead.Kind.LISTING, "core/advertise.html", reverse("core:advertise"))


def contact(request):
    return lead_page(request, Lead.Kind.CONTACT, "core/contact.html", reverse("core:contact"))


def privacy(request):
    return render(request, "core/privacy.html")
