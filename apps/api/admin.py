from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display

from apps.core.features import FeatureGatedAdminMixin

from .models import ApiKey


@admin.register(ApiKey)
class ApiKeyAdmin(FeatureGatedAdminMixin, ModelAdmin):
    feature = "api"
    list_display = ("name", "prefix_display", "permission", "source", "active", "last_used_at")
    list_filter = ("permission", "is_active")
    search_fields = ("name", "prefix")
    readonly_fields = ("prefix", "last_used_at", "created_by", "created_at")
    fields = (
        "name",
        "permission",
        "source",
        "is_active",
        "prefix",
        "last_used_at",
        "created_by",
        "created_at",
    )

    @display(description=_("chave"))
    def prefix_display(self, obj):
        return f"{obj.prefix}…"

    @display(description=_("ativa"), boolean=True, ordering="is_active")
    def active(self, obj):
        return obj.is_active

    def save_model(self, request, obj, form, change):
        if change:
            super().save_model(request, obj, form, change)
            return
        created, raw = ApiKey.create_with_key(
            name=obj.name,
            permission=obj.permission,
            source=obj.source,
            is_active=obj.is_active,
            created_by=request.user,
        )
        obj.pk, obj.prefix = created.pk, created.prefix  # o admin segue para a página da chave
        obj._state.adding = False
        self.message_user(
            request,
            format_html(
                "{} <code class='select-all font-semibold'>{}</code> {}",
                _("Chave criada. Copie agora:"),
                raw,
                _("Ela não será mostrada de novo."),
            ),
            messages.WARNING,
        )
