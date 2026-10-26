from urllib.parse import urlencode

from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from apps.core.admin_filters import AdvancedSearchMixin
from apps.core.admin_masks import MaskedAdminMixin
from apps.core.features import FeatureGatedAdminMixin
from apps.crm.models import normalize_phone
from apps.people.scoping import ScopedByRoleMixin
from apps.properties.admin import format_brl

from .models import Lead, PropertySearch

STATUS_LABELS = {
    Lead.Status.NEW: "warning",
    Lead.Status.CONTACTED: "info",
    Lead.Status.CLOSED: "success",
}


@admin.register(Lead)
class LeadAdmin(AdvancedSearchMixin, ScopedByRoleMixin, MaskedAdminMixin, ModelAdmin):
    scope_prefix = "property__"
    masks = {"phone": "phone"}
    list_display = (
        "name",
        "email",
        "phone",
        "kind",
        "property_link",
        "client_link",
        "status_badge",
        "created_at",
    )
    list_filter = ("status", "kind", "created_at")
    search_fields = ("name", "email", "phone", "message")
    search_help_text = _("Buscar por nome, e-mail, telefone ou mensagem")
    readonly_fields = ("created_at",)
    list_select_related = ("property", "client")
    actions = ["mark_contacted"]
    actions_row = ["mark_contacted_row"]

    @display(description=_("cliente"))
    def client_link(self, obj):
        if not obj.client_id:
            return "-"
        url = reverse("admin:crm_client_change", args=[obj.client_id])
        return format_html('<a href="{}">{}</a>', url, obj.client)

    @display(description=_("imóvel"))
    def property_link(self, obj):
        if not obj.property:
            return "-"
        url = reverse("admin:properties_property_change", args=[obj.property_id])
        return format_html('<a href="{}">{}</a>', url, obj.property.code)

    @display(description=_("situação"), ordering="status", label=STATUS_LABELS)
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()

    @admin.action(description=_("Marcar como contatado"))
    def mark_contacted(self, request, queryset):
        n = queryset.filter(status=Lead.Status.NEW).update(status=Lead.Status.CONTACTED)
        self.message_user(request, _("%d mensagem(ns) marcada(s) como contatada(s).") % n)

    @action(description=_("Marcar como contatado"), url_path="marcar-contatado")
    def mark_contacted_row(self, request, object_id):
        Lead.objects.filter(pk=object_id, status=Lead.Status.NEW).update(
            status=Lead.Status.CONTACTED
        )
        messages.success(request, _("Mensagem marcada como contatada."))
        return redirect(reverse("admin:leads_lead_changelist"))


SEARCH_STATUS_LABELS = {
    PropertySearch.Status.NEW: "warning",
    PropertySearch.Status.CONTACTED: "info",
    PropertySearch.Status.CLOSED: "success",
}


@admin.register(PropertySearch)
class PropertySearchAdmin(
    AdvancedSearchMixin, FeatureGatedAdminMixin, MaskedAdminMixin, ModelAdmin
):
    feature = "searches"
    masks = {"whatsapp": "phone", "min_price": "money", "max_price": "money"}
    list_display = (
        "name_link",
        "whatsapp_link",
        "wanted",
        "matching",
        "status_badge",
        "created_at",
    )
    list_display_links = None
    list_filter = ("status", "purpose", "city", "created_at")
    search_fields = ("name", "whatsapp", "email", "neighborhoods", "notes")
    search_help_text = _("Buscar por nome, WhatsApp ou observações")
    readonly_fields = ("created_at", "lgpd_consent")
    filter_horizontal = ("categories",)
    actions = ["mark_contacted"]
    actions_row = ["mark_contacted_row"]
    fieldsets = (
        (_("Contato"), {"fields": ("name", "whatsapp", "email", "created_at", "lgpd_consent")}),
        (
            _("O que procura"),
            {
                "fields": (
                    "purpose",
                    "categories",
                    "city",
                    "neighborhoods",
                    ("min_price", "max_price"),
                    ("min_bedrooms", "min_parking"),
                    "notes",
                )
            },
        ),
        (_("Atendimento"), {"fields": ("status",)}),
    )

    @display(description=_("nome"), ordering="name")
    def name_link(self, obj):
        edit = reverse("admin:leads_propertysearch_change", args=[obj.pk])
        if not obj.client_id:
            return format_html('<a href="{}">{}</a>', edit, obj.name)
        client = reverse("admin:crm_client_change", args=[obj.client_id])
        return format_html(
            '<a href="{}" class="font-medium">{}</a> <a href="{}" class="text-xs">({})</a>',
            edit,
            obj.name,
            client,
            _("ver cliente"),
        )

    @display(description=_("WhatsApp"))
    def whatsapp_link(self, obj):
        digits = normalize_phone(obj.whatsapp)
        if not digits:
            return obj.whatsapp or "-"
        return format_html(
            '<a href="https://wa.me/55{}" target="_blank" rel="noopener">{}</a>',
            digits,
            obj.whatsapp,
        )

    @display(description=_("procura"))
    def wanted(self, obj):
        parts = [obj.get_purpose_display()]
        names = ", ".join(c.name for c in obj.categories.all())
        if names:
            parts.append(names)
        where = obj.city.name if obj.city_id else ""
        if obj.neighborhoods:
            where = f"{obj.neighborhoods} ({where})" if where else obj.neighborhoods
        if where:
            parts.append(where)
        if obj.max_price:
            parts.append(_("até %s") % format_brl(obj.max_price))
        elif obj.min_price:
            parts.append(_("a partir de %s") % format_brl(obj.min_price))
        return " · ".join(str(p) for p in parts)

    @display(description=_("compatíveis"))
    def matching(self, obj):
        url = (
            reverse("admin:properties_property_changelist") + "?" + urlencode(obj.matching_query())
        )
        n = obj.matching_count()
        text = ngettext("Ver %(n)d imóvel compatível", "Ver %(n)d imóveis compatíveis", n) % {
            "n": n
        }
        return format_html('<a href="{}">{}</a>', url, text)

    @display(description=_("situação"), ordering="status", label=SEARCH_STATUS_LABELS)
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("city", "client")
            .prefetch_related("categories")
        )

    @admin.action(description=_("Marcar como contatado"))
    def mark_contacted(self, request, queryset):
        n = queryset.filter(status=PropertySearch.Status.NEW).update(
            status=PropertySearch.Status.CONTACTED
        )
        self.message_user(request, _("%d procura(s) marcada(s) como contatada(s).") % n)

    @action(description=_("Marcar como contatado"), url_path="marcar-contatado")
    def mark_contacted_row(self, request, object_id):
        PropertySearch.objects.filter(pk=object_id, status=PropertySearch.Status.NEW).update(
            status=PropertySearch.Status.CONTACTED
        )
        messages.success(request, _("Procura marcada como contatada."))
        return redirect(reverse("admin:leads_propertysearch_changelist"))
