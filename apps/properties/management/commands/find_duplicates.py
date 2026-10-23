from django.core.management.base import BaseCommand

from apps.properties import duplicates


class Command(BaseCommand):
    help = "Varre o estoque atrás de imóveis duplicados e atualiza o aviso no painel."

    def add_arguments(self, parser):
        parser.add_argument("--quiet", action="store_true", help="Mostra só o total.")

    def handle(self, *args, **options):
        pairs = duplicates.scan_all()
        if not options["quiet"]:
            for a, b, level in pairs:
                self.stdout.write(f"[{duplicates.LEVEL_LABELS[level]}] {a.code} x {b.code}")
        self.stdout.write(self.style.SUCCESS(f"{len(pairs)} par(es) de possíveis duplicados."))
