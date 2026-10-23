from django.core.management.base import BaseCommand

from apps.crm.base_templates import ensure_base_templates


class Command(BaseCommand):
    help = "Cria os modelos-base de documentos (visita, proposta, contratos, recibo) que faltam."

    def handle(self, *args, **options):
        created = ensure_base_templates()
        self.stdout.write(self.style.SUCCESS(f"{created} modelo(s) criado(s)."))
