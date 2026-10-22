from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from apps.core.admin_masks import MaskedAdminMixin

from .models import Lead

STATUS_LABELS = {
    Lead.Status.NEW: "warning",
    Lead.Status.CONTACTED: "info",
    Lead.Status.CLOSED: "success",
}


@admin.register(Lead)
class LeadAdmin(MaskedAdminMixin, ModelAdmin):
    masks = {"phone": "phone"}
    list_display = ("name", "email", "phone", "property_link", "status_badge", "created_at")
    list_filter = ("status", "created_at")
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
