from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from apps.core.admin_masks import MaskedAdminMixin
from apps.core.features import FeatureGatedAdminMixin

from .models import Broker, Owner, Partner


class LinkedPropertiesMixin:
    """Mostra os imóveis vinculados e o atalho "Ver imóveis" (lista do painel já filtrada)."""

    property_filter = None  # nome do FK em Property: broker, partner ou owner
    actions_detail = ["view_properties_action"]

    def properties_url(self, obj):
        base = reverse("admin:properties_property_changelist")
        return f"{base}?{self.property_filter}__id__exact={obj.pk}"

    @action(description=_("Ver imóveis"), url_path="ver-imoveis", icon="home_work")
    def view_properties_action(self, request, object_id):
        return redirect(self.properties_url(self.get_object(request, object_id)))

    @display(description=_("imóveis vinculados"))
    def linked_properties(self, obj):
        if not obj or not obj.pk:
            return "-"
        items = obj.properties.all()[:50]
        if not items:
            return _("Nenhum imóvel vinculado.")
        return format_html(
            '<ul>{}</ul><p><a class="underline" href="{}">Ver na lista de imóveis</a></p>',
            format_html_join(
                "",
                '<li><a href="{}">{}</a></li>',
                ((reverse("admin:properties_property_change", args=[p.pk]), str(p)) for p in items),
            ),
            self.properties_url(obj),
        )

    @display(description=_("imóveis"))
    def properties_count(self, obj):
        n = obj.properties.count()
        label = f"Ver {n} imóve{'l' if n == 1 else 'is'}"
        return format_html('<a class="underline" href="{}">{}</a>', self.properties_url(obj), label)


@admin.register(Broker)
class BrokerAdmin(FeatureGatedAdminMixin, LinkedPropertiesMixin, MaskedAdminMixin, ModelAdmin):
    feature = "brokers"
    property_filter = "broker"
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
    property_filter = "partner"
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
    property_filter = "owner"
    masks = {"phone": "phone", "document": "cpf_cnpj"}
    list_display = ("name", "document", "phone", "properties_count")
    search_fields = ("name", "document", "email")
    readonly_fields = ("linked_properties",)
    fields = ("name", "document", "phone", "email", "notes", "linked_properties")
