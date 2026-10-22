"""JSON-LD (schema.org) público. Nunca inclui dados internos (corretor, proprietário, usuário)."""

import json

from django.urls import reverse


def dumps(data):
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")


def agency(request, site):
    data = {
        "@context": "https://schema.org",
        "@type": "RealEstateAgent",
        "name": site.name,
        "url": request.build_absolute_uri(reverse("core:home")),
    }
    if site.logo:
        data["logo"] = request.build_absolute_uri(site.logo.url)
    if site.phone:
        data["telephone"] = site.phone
    if site.email:
        data["email"] = site.email
    if site.address:
        data["address"] = site.address
    if site.creci:
        data["identifier"] = f"CRECI {site.creci}"
    return dumps(data)


def listing(request, prop, photos):
    url = request.build_absolute_uri(prop.get_absolute_url())
    city = prop.neighborhood.city
    price = prop.sale_price if prop.purpose != "RENT" else prop.rent_price
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "RealEstateListing",
                "name": prop.title,
                "url": url,
                "description": prop.description[:300] or prop.title,
                "datePosted": prop.published_at.date().isoformat() if prop.published_at else None,
                "image": [request.build_absolute_uri(p.src_lg) for p in photos[:6]],
                "offers": {"@type": "Offer", "priceCurrency": "BRL", "price": str(price or "")},
                "about": {
                    "@type": "Residence",
                    "numberOfBedrooms": prop.bedrooms,
                    "numberOfBathroomsTotal": prop.bathrooms,
                    "address": {
                        "@type": "PostalAddress",
                        "addressLocality": city.name,
                        "addressRegion": city.state,
                        "addressCountry": "BR",
                    },
                },
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Imóveis",
                        "item": request.build_absolute_uri(reverse("properties:list")),
                    },
                    {"@type": "ListItem", "position": 2, "name": prop.title, "item": url},
                ],
            },
        ],
    }
    return dumps(data)
