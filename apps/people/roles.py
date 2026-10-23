"""Funções (grupos prontos). As permissões são recalculadas a cada `migrate`."""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission

ADMIN, MANAGER, BROKER, CLERK = "Administrador", "Gerente", "Corretor", "Atendente"
ROLE_CHOICES = [
    (ADMIN, "Administrador — acesso total"),
    (MANAGER, "Gerente — tudo, exceto equipe e configurações"),
    (BROKER, "Corretor — cadastra e edita os próprios imóveis"),
    (CLERK, "Atendente — mensagens e consulta de imóveis"),
]
ROLE_NAMES = [name for name, _label in ROLE_CHOICES]

APP_LABELS = ("core", "properties", "leads", "people", "crm", "api", "auth")


def _perms(*codenames):
    return Permission.objects.filter(codename__in=codenames)


CRM_DAILY = (
    "view_client",
    "add_client",
    "change_client",
    "view_interaction",
    "add_interaction",
    "change_interaction",
    "delete_interaction",
    "view_followup",
    "add_followup",
    "change_followup",
    "delete_followup",
    "view_documenttemplate",
    "view_generateddocument",
    "add_generateddocument",
)


def _permissions_for(role):
    everything = Permission.objects.filter(content_type__app_label__in=APP_LABELS)
    if role == ADMIN:
        return everything
    if role == MANAGER:
        return everything.exclude(content_type__app_label__in=("core", "auth", "api"))
    lookups = _perms(
        "view_category", "view_city", "view_neighborhood", "view_feature", "view_property"
    )
    if role == BROKER:
        return (
            lookups
            | _perms(
                "add_property",
                "change_property",
                "add_propertyphoto",
                "change_propertyphoto",
                "delete_propertyphoto",
                "view_lead",
                "change_lead",
                "view_owner",
                "add_owner",
                "change_owner",
                "view_guarantor",
                "add_guarantor",
                "change_guarantor",
                "view_partner",
                "add_partner",
                "change_partner",
                "view_broker",
                "view_propertysearch",
                "change_propertysearch",
                *CRM_DAILY,
            )
        ).distinct()
    return (
        lookups
        | _perms(
            "view_lead",
            "change_lead",
            "view_broker",
            "view_propertysearch",
            "change_propertysearch",
            *CRM_DAILY,
        )
    ).distinct()


def ensure_roles():
    for label in APP_LABELS:
        config = global_apps.get_app_config(label)
        create_permissions(config, verbosity=0)
    for name in ROLE_NAMES:
        group, _created = Group.objects.get_or_create(name=name)
        group.permissions.set(_permissions_for(name))


def role_of(user):
    """Função principal do usuário (superusuário conta como Administrador)."""
    if user.is_superuser:
        return ADMIN
    names = set(user.groups.values_list("name", flat=True))
    for name in ROLE_NAMES:
        if name in names:
            return name
    return None


def has_full_access(user):
    return role_of(user) in (ADMIN, MANAGER)


def apply_role(user, role):
    groups = Group.objects.filter(name__in=ROLE_NAMES)
    user.groups.remove(*groups)
    user.groups.add(Group.objects.get(name=role))
    if not user.is_staff:
        user.is_staff = True
        user.save(update_fields=["is_staff"])
