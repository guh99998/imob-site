from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import SiteSettings

# Grupos não são usados: permissões são dadas direto na Equipe.
admin.site.unregister(Group)
admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ("username", "first_name", "last_name", "email", "is_staff", "is_active")


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    readonly_fields = ("logo_preview",)
    fieldsets = (
        (
            _("Identidade"),
            {
                "fields": (
                    "name",
                    "logo",
                    "logo_preview",
                    "creci",
                    "cnpj",
                    "about",
                    "meta_description",
                )
            },
        ),
        (
            _("Contato"),
            {"fields": ("phone", "whatsapp", "email", "address", "instagram", "facebook")},
        ),
        (_("Site"), {"fields": ("max_featured",)}),
    )

    @display(description=_("pré-visualização"))
    def logo_preview(self, obj):
        if obj.pk and obj.logo:
            return format_html('<img src="{}" style="height:48px">', obj.logo.url)
        return "-"

    def changelist_view(self, request, extra_context=None):
        obj = SiteSettings.load()
        return redirect(reverse("admin:core_sitesettings_change", args=[obj.pk]))

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
