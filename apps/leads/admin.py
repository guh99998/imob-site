from urllib.parse import urlencode

from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from apps.core.admin_masks import MaskedAdminMixin
from apps.core.features import FeatureGatedAdminMixin
from apps.people.scoping import ScopedByRoleMixin
from apps.properties.admin import format_brl

from .models import Lead, PropertySearch

STATUS_LABELS = {
    Lead.Status.NEW: "warning",
    Lead.Status.CONTACTED: "info",
    Lead.Status.CLOSED: "success",
}


@admin.register(Lead)
class LeadAdmin(ScopedByRoleMixin, MaskedAdminMixin, ModelAdmin):
    scope_prefix = "property__"
    masks = {"phone": "phone"}
    list_display = ("name", "email", "phone", "kind", "property_link", "status_badge", "created_at")
    list_filter = ("status", "kind", "created_at")
    search_fields = ("name", "email", "phone", "message")
    readonly_fields = ("created_at",)
    list_select_related = ("property",)
    actions = ["mark_contacted"]
    actions_row = ["mark_contacted_row"]

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
class PropertySearchAdmin(FeatureGatedAdminMixin, MaskedAdminMixin, ModelAdmin):
    feature = "searches"
    masks = {"whatsapp": "phone", "min_price": "money", "max_price": "money"}
    list_display = (
        "name",
        "whatsapp",
        "purpose",
        "wanted",
        "city",
        "price_range",
        "status_badge",
        "created_at",
    )
    list_filter = ("status", "purpose", "city", "created_at")
    search_fields = ("name", "whatsapp", "email", "neighborhoods", "notes")
    readonly_fields = ("created_at", "lgpd_consent")
    filter_horizontal = ("categories",)
    actions = ["mark_contacted"]
    actions_row = ["matching_row", "mark_contacted_row"]

    @display(description=_("procura"))
    def wanted(self, obj):
        return ", ".join(c.name for c in obj.categories.all()) or "-"

    @display(description=_("faixa de preço"))
    def price_range(self, obj):
        if not (obj.min_price or obj.max_price):
            return "-"
        low = format_brl(obj.min_price) if obj.min_price else "…"
        high = format_brl(obj.max_price) if obj.max_price else "…"
        return f"{low} a {high}"

    @display(description=_("situação"), ordering="status", label=SEARCH_STATUS_LABELS)
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("city").prefetch_related("categories")

    @action(description=_("Ver imóveis compatíveis"), url_path="compativeis")
    def matching_row(self, request, object_id):
        search = PropertySearch.objects.get(pk=object_id)
        query = urlencode(search.matching_query())
        return redirect(reverse("admin:properties_property_changelist") + "?" + query)

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
