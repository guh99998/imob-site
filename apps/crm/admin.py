from urllib.parse import urlencode

from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from apps.core.admin_filters import AdvancedSearchMixin
from apps.core.admin_masks import MaskedAdminMixin
from apps.core.features import FeatureGatedAdminMixin
from apps.people.scoping import ScopedByRoleMixin, is_scoped

from . import services
from .models import Client, FollowUp, Interaction

STAGE_LABELS = {
    Client.Stage.NEW: "warning",
    Client.Stage.IN_PROGRESS: "info",
    Client.Stage.VISIT: "info",
    Client.Stage.PROPOSAL: "info",
    Client.Stage.WON: "success",
    Client.Stage.LOST: "danger",
}


class InteractionInline(TabularInline):
    model = Interaction
    extra = 1
    tab = True
    fields = ("kind", "happened_at", "property", "text", "author")
    readonly_fields = ("author",)
    autocomplete_fields = ("property",)
    verbose_name = _("interação")
    verbose_name_plural = _("Histórico")


class FollowUpInline(TabularInline):
    model = FollowUp
    extra = 0
    tab = True
    fields = ("due_date", "note", "broker", "done")
    verbose_name = _("retorno")
    verbose_name_plural = _("Retornos")


def _stage_action(stage):
    @admin.action(description=_("Mover para: %s") % Client.Stage(stage).label)
    def move(self, request, queryset):
        n = queryset.update(stage=stage, updated_at=timezone.now())
        self.message_user(
            request,
            _("%(n)d cliente(s) movido(s) para “%(stage)s”.")
            % {"n": n, "stage": Client.Stage(stage).label},
            messages.SUCCESS,
        )

    move.__name__ = f"move_to_{stage.lower()}"
    return move


@admin.register(Client)
class ClientAdmin(
    AdvancedSearchMixin, FeatureGatedAdminMixin, ScopedByRoleMixin, MaskedAdminMixin, ModelAdmin
):
    feature = "crm"
    masks = {"whatsapp": "phone", "min_price": "money", "max_price": "money"}
    list_display = (
        "name",
        "whatsapp",
        "stage_badge",
        "broker",
        "source",
        "next_followup",
        "updated_at",
    )
    list_filter = ("stage", "broker", "source", "purpose", "created_at")
    list_select_related = ("broker",)
    search_fields = ("name", "whatsapp", "email", "tags", "notes")
    search_help_text = _("Buscar por nome, WhatsApp, email ou etiqueta")
    readonly_fields = ("lgpd_consent_at", "anonymized_at", "audit_created", "audit_updated")
    inlines = [InteractionInline, FollowUpInline]
    actions_row = ["matching_row"]
    actions_detail = ["matching_detail"]
    warn_unsaved_form = True
    actions = [
        *[f"move_to_{s.lower()}" for s in Client.Stage.values],
        "assign_to_me",
        "anonymize_clients",
    ]
    fieldsets = (
        (
            _("Cliente"),
            {
                "classes": ["tab"],
                "fields": ("name", "whatsapp", "email", "source", "broker", "stage"),
            },
        ),
        (
            _("Interesse"),
            {
                "classes": ["tab"],
                "fields": ("purpose", "min_price", "max_price", "tags", "notes"),
            },
        ),
        (
            _("LGPD e registro"),
            {
                "classes": ["tab"],
                "fields": (
                    "lgpd_consent",
                    "lgpd_consent_at",
                    "anonymized_at",
                    "audit_created",
                    "audit_updated",
                ),
            },
        ),
    )

    # Uma ação por etapa do funil: move_to_new, move_to_in_progress, ...
    for _stage in Client.Stage.values:
        locals()[f"move_to_{_stage.lower()}"] = _stage_action(_stage)
    del _stage

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("followups")

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        broker = getattr(request.user, "broker", None)
        if broker and "broker" not in initial:
            initial["broker"] = broker.pk
        return initial

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        if is_scoped(request.user) and not obj.broker_id:
            obj.broker = getattr(request.user, "broker", None)
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for obj in instances:
            if isinstance(obj, Interaction) and not obj.author_id:
                obj.author = request.user
            if isinstance(obj, FollowUp) and not obj.broker_id:
                obj.broker = form.instance.broker
            obj.save()
        formset.save_m2m()

    @display(description=_("etapa"), ordering="stage", label=STAGE_LABELS)
    def stage_badge(self, obj):
        return obj.stage, obj.get_stage_display()

    @display(description=_("próximo retorno"))
    def next_followup(self, obj):
        pending = sorted((f for f in obj.followups.all() if not f.done), key=lambda f: f.due_date)
        if not pending:
            return "-"
        first = pending[0]
        text = f"{first.due_date:%d/%m/%Y}"
        if first.is_overdue:
            return format_html(
                '<span class="text-red-600 font-semibold">{} (atrasado)</span>', text
            )
        return text

    @display(description=_("cadastrado por"))
    def audit_created(self, obj):
        if not obj or not obj.created_by:
            return "-"
        name = obj.created_by.get_full_name() or obj.created_by
        return f"{name} em {obj.created_at:%d/%m/%Y %H:%M}"

    @display(description=_("última edição"))
    def audit_updated(self, obj):
        if not obj or not obj.updated_by:
            return "-"
        name = obj.updated_by.get_full_name() or obj.updated_by
        return f"{name} em {obj.updated_at:%d/%m/%Y %H:%M}"

    def _matching_redirect(self, client):
        query = urlencode(client.matching_query())
        return redirect(reverse("admin:properties_property_changelist") + "?" + query)

    @action(description=_("Ver imóveis compatíveis"), url_path="compativeis")
    def matching_row(self, request, object_id):
        return self._matching_redirect(get_object_or_404(self.get_queryset(request), pk=object_id))

    @action(description=_("Ver imóveis compatíveis"), url_path="compativeis-detalhe")
    def matching_detail(self, request, object_id):
        return self._matching_redirect(get_object_or_404(self.get_queryset(request), pk=object_id))

    @admin.action(description=_("Atribuir a mim"))
    def assign_to_me(self, request, queryset):
        broker = getattr(request.user, "broker", None)
        if broker is None:
            self.message_user(
                request,
                _("Seu usuário não está ligado a um corretor (cadastre em Pessoas → Corretores)."),
                messages.ERROR,
            )
            return
        n = queryset.update(broker=broker, updated_at=timezone.now())
        self.message_user(request, _("%d cliente(s) atribuído(s) a você.") % n, messages.SUCCESS)

    @admin.action(description=_("Anonimizar cliente (LGPD)"), permissions=["delete"])
    def anonymize_clients(self, request, queryset):
        n = 0
        for client in queryset.filter(anonymized_at__isnull=True):
            services.anonymize(client)
            n += 1
        self.message_user(request, _("%d cliente(s) anonimizado(s).") % n, messages.SUCCESS)


@admin.register(FollowUp)
class FollowUpAdmin(AdvancedSearchMixin, FeatureGatedAdminMixin, ScopedByRoleMixin, ModelAdmin):
    feature = "crm"
    scope_prefix = "client__"
    list_display = ("client", "due_date", "note", "broker", "status")
    list_filter = ("done", "broker", "due_date")
    list_select_related = ("client", "broker")
    search_fields = ("client__name", "client__whatsapp", "note")
    search_help_text = _("Buscar por cliente ou observação")
    autocomplete_fields = ("client",)
    readonly_fields = ("done_at",)
    actions = ["mark_done"]

    @display(
        description=_("situação"),
        ordering="done",
        label={"overdue": "danger", "today": "warning", "done": "success", "pending": "info"},
    )
    def status(self, obj):
        if obj.done:
            return "done", _("Feito")
        if obj.is_overdue:
            return "overdue", _("Atrasado")
        if obj.due_date == timezone.localdate():
            return "today", _("Hoje")
        return "pending", _("A fazer")

    @admin.action(description=_("Marcar como feito"))
    def mark_done(self, request, queryset):
        n = queryset.filter(done=False).update(done=True, done_at=timezone.now())
        self.message_user(request, _("%d retorno(s) marcado(s) como feito(s).") % n)
