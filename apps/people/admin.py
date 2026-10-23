from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from apps.core.admin_filters import AdvancedSearchMixin
from apps.core.admin_masks import MaskedAdminMixin
from apps.core.features import FeatureGatedAdminMixin

from .models import Broker, Guarantor, Owner, Partner
from .scoping import is_scoped


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
class BrokerAdmin(
    AdvancedSearchMixin,
    FeatureGatedAdminMixin,
    LinkedPropertiesMixin,
    MaskedAdminMixin,
    ModelAdmin,
):
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


QUALIFICATION_MASKS = {
    "cpf": "cpf_cnpj",
    "spouse_cpf": "cpf_cnpj",
    "zip_code": "cep",
    "state": "uf",
}
QUALIFICATION_FIELDSETS = (
    (
        _("Qualificação (para contratos)"),
        {
            "fields": (
                "cpf",
                "nationality",
                "marital_status",
                "profession",
                ("zip_code", "street", "number"),
                ("complement", "neighborhood"),
                ("city", "state"),
            )
        },
    ),
    (
        _("Cônjuge"),
        {
            "description": _("Obrigatório quando casado(a) ou em união estável."),
            "fields": (
                "spouse_status",
                "spouse_name",
                "spouse_cpf",
                "spouse_nationality",
                "spouse_profession",
            ),
        },
    ),
)


class SpouseStatusMixin:
    """Aviso na ficha: pessoa casada sem cônjuge cadastrado (não bloqueia o salvamento)."""

    @display(description=_("situação do cônjuge"))
    def spouse_status(self, obj):
        if obj and obj.pk and obj.spouse_missing:
            return format_html(
                '<span class="text-red-600 font-semibold">{}</span>',
                _("Casado(a): informe nome e CPF do cônjuge para o contrato ser válido."),
            )
        return "-"


@admin.register(Owner)
class OwnerAdmin(
    FeatureGatedAdminMixin, LinkedPropertiesMixin, SpouseStatusMixin, MaskedAdminMixin, ModelAdmin
):
    feature = "owners"
    property_filter = "owner"
    masks = {"phone": "phone", "document": "cpf_cnpj", **QUALIFICATION_MASKS}
    list_display = ("name", "document", "phone", "properties_count")
    search_fields = ("name", "document", "cpf", "email")
    readonly_fields = ("linked_properties", "spouse_status")
    fieldsets = (
        (None, {"fields": ("name", "document", "phone", "email", "notes", "linked_properties")}),
        *QUALIFICATION_FIELDSETS,
    )


@admin.register(Guarantor)
class GuarantorAdmin(FeatureGatedAdminMixin, SpouseStatusMixin, MaskedAdminMixin, ModelAdmin):
    """Fiadores de locação. O Corretor só enxerga os que cadastrou."""

    feature = "owners"
    masks = {"phone": "phone", **QUALIFICATION_MASKS}
    list_display = ("name", "cpf", "phone", "marital_status")
    search_fields = ("name", "cpf", "email")
    readonly_fields = ("spouse_status",)
    fieldsets = (
        (None, {"fields": ("name", "phone", "email", "notes")}),
        *QUALIFICATION_FIELDSETS,
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(created_by=request.user) if is_scoped(request.user) else qs

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
