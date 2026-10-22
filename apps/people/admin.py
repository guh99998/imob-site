from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display

from apps.core.admin_masks import MaskedAdminMixin
from apps.core.features import FeatureGatedAdminMixin

from .models import Broker, Owner, Partner


class LinkedPropertiesMixin:
    """Mostra, na página da pessoa, os imóveis vinculados a ela."""

    @display(description=_("imóveis vinculados"))
    def linked_properties(self, obj):
        if not obj or not obj.pk:
            return "-"
        items = obj.properties.all()[:50]
        if not items:
            return _("Nenhum imóvel vinculado.")
        return format_html(
            "<ul>{}</ul>",
            format_html_join(
                "",
                '<li><a href="{}">{}</a></li>',
                ((reverse("admin:properties_property_change", args=[p.pk]), str(p)) for p in items),
            ),
        )

    @display(description=_("imóveis"))
    def properties_count(self, obj):
        return obj.properties.count()


@admin.register(Broker)
class BrokerAdmin(FeatureGatedAdminMixin, LinkedPropertiesMixin, MaskedAdminMixin, ModelAdmin):
    feature = "brokers"
    masks = {"phone": "phone", "creci": "creci"}
    list_display = ("name", "creci", "phone", "is_active", "properties_count")
    list_filter = ("is_active",)
    search_fields = ("name", "creci", "email")
    readonly_fields = ("linked_properties",)
    fields = (
        "name",
        "user",
        "creci",
        "phone",
        "email",
        "photo",
        "is_active",
        "notes",
        "linked_properties",
    )


@admin.register(Partner)
class PartnerAdmin(FeatureGatedAdminMixin, LinkedPropertiesMixin, MaskedAdminMixin, ModelAdmin):
    feature = "partners"
    masks = {"phone": "phone", "creci": "creci"}
    list_display = ("name", "company", "creci", "phone", "properties_count")
    search_fields = ("name", "company", "creci", "email")
    readonly_fields = ("linked_properties",)
    fields = (
        "name",
        "company",
        "creci",
        "phone",
        "email",
        "commission",
        "notes",
        "linked_properties",
    )


@admin.register(Owner)
class OwnerAdmin(FeatureGatedAdminMixin, LinkedPropertiesMixin, MaskedAdminMixin, ModelAdmin):
    feature = "owners"
    masks = {"phone": "phone", "document": "cpf_cnpj"}
    list_display = ("name", "document", "phone", "properties_count")
    search_fields = ("name", "document", "email")
    readonly_fields = ("linked_properties",)
    fields = ("name", "document", "phone", "email", "notes", "linked_properties")
