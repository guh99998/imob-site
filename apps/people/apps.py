from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _ensure_roles(sender, **kwargs):
    from .roles import ensure_roles

    ensure_roles()


class PeopleConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.people"
    verbose_name = "Pessoas"

    def ready(self):
        # Quando as permissões do último app já existem, criamos/atualizamos os grupos.
        post_migrate.connect(_ensure_roles, sender=self, dispatch_uid="people-ensure-roles")
