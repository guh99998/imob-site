from django import forms
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

from apps.people.roles import ADMIN, ROLE_CHOICES, apply_role, role_of

from .admin_masks import MaskedAdminMixin
from .models import SiteSettings

# Grupos são gerenciados pelo campo "Função" do usuário (apps/people/roles.py).
admin.site.unregister(Group)
admin.site.unregister(User)


def _role_field():
    return forms.ChoiceField(
        label=_("Função"),
        choices=ROLE_CHOICES,
        help_text=_("Define o que a pessoa pode ver e fazer no painel."),
    )


class RoleUserChangeForm(UserChangeForm):
    role = _role_field()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["role"].initial = role_of(self.instance)


class RoleUserCreationForm(UserCreationForm):
    role = _role_field()


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = RoleUserChangeForm
    add_form = RoleUserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ("username", "first_name", "last_name", "email", "role_label", "is_active")
    list_filter = ("is_active", "groups")
    ordering = ("first_name", "last_name", "username")
    add_fieldsets = (
        *BaseUserAdmin.add_fieldsets,
        (_("Acesso"), {"fields": ("first_name", "last_name", "email", "role")}),
    )

    @display(description=_("função"))
    def role_label(self, obj):
        return role_of(obj) or "-"

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        fieldsets = [
            (None, {"fields": ("username", "password")}),
            (_("Dados pessoais"), {"fields": ("first_name", "last_name", "email")}),
            (_("Acesso"), {"fields": ("role", "is_active")}),
        ]
        if request.user.is_superuser:  # permissões cruas só para superusuário
            fieldsets.append(
                (
                    _("Avançado"),
                    {"fields": ("is_superuser", "groups", "user_permissions")},
                )
            )
        return fieldsets

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        role = form.cleaned_data.get("role")
        if role:
            apply_role(obj, role)

    # Só o Administrador gerencia a equipe.
    def _only_admin(self, request):
        return role_of(request.user) == ADMIN

    def has_module_permission(self, request):
        return self._only_admin(request) and super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return self._only_admin(request) and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return self._only_admin(request) and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return self._only_admin(request) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self._only_admin(request) and super().has_delete_permission(request, obj)


@admin.register(SiteSettings)
class SiteSettingsAdmin(MaskedAdminMixin, ModelAdmin):
    masks = {"phone": "phone", "whatsapp": "phone", "cnpj": "cpf_cnpj", "creci": "creci"}
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
