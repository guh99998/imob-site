from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, Permission, User
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.widgets import UnfoldAdminCheckboxSelectMultipleWidget

from apps.people.roles import ADMIN, ROLE_CHOICES, apply_role, role_of

from .admin_masks import MaskedAdminMixin
from .models import SiteSettings

# Grupos são gerenciados pelo campo "Função" do usuário (apps/people/roles.py).
admin.site.unregister(Group)
admin.site.unregister(User)


PERMISSION_ACTIONS = {
    "add": _("Cadastrar"),
    "change": _("Editar"),
    "delete": _("Excluir"),
    "view": _("Ver"),
}


def permission_label(permission):
    """ "Cliente: Ver" em vez de "crm | cliente | Can view cliente" (que vem em inglês)."""
    action, _sep, _model = permission.codename.partition("_")
    model = permission.content_type.model_class()
    name = str(model._meta.verbose_name) if model else permission.content_type.model
    if action in PERMISSION_ACTIONS:
        return f"{name.capitalize()}: {PERMISSION_ACTIONS[action]}"
    return f"{name.capitalize()}: {permission.name}"


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

    readonly_fields = ("password_reset",)
    filter_horizontal = ()  # grupos e permissões viram listas de caixas (checklist)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name in ("groups", "user_permissions"):
            kwargs["widget"] = UnfoldAdminCheckboxSelectMultipleWidget
            if db_field.name == "user_permissions":
                kwargs["queryset"] = Permission.objects.select_related("content_type").order_by(
                    "content_type__app_label", "content_type__model", "codename"
                )
        field = super().formfield_for_manytomany(db_field, request, **kwargs)
        if db_field.name == "user_permissions":
            field.label_from_instance = permission_label
        return field

    @display(description=_("função"))
    def role_label(self, obj):
        return role_of(obj) or "-"

    @display(description=_("senha"))
    def password_reset(self, obj):
        """Só o botão: a pessoa não precisa ver algoritmo, iterações nem o hash."""
        if not obj or not obj.pk:
            return "-"
        return format_html(
            '<a href="{}" style="display:inline-block;padding:.5rem 1rem;border-radius:4px;'
            "background:var(--color-primary-600,#7c3aed);color:#fff;font-weight:500;"
            'text-decoration:none">{}</a>',
            reverse("admin:auth_user_password_change", args=[obj.pk]),
            _("Redefinir senha"),
        )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        fieldsets = [
            (None, {"fields": ("username", "password_reset")}),
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
        (_("Anúncios"), {"fields": ("review_interval_days",)}),
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
