"""Importa imóveis de uma planilha (XLSX/CSV) ou de um XML VivaReal/ZAP, sem passar pelo painel."""

from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError

from apps.properties import importing
from apps.properties.models import ImportJob


class Command(BaseCommand):
    help = "Importa imóveis de um arquivo .xlsx/.csv (com --zip de fotos) ou .xml (VivaReal/ZAP)."

    def add_arguments(self, parser):
        parser.add_argument("file", help="Planilha (.xlsx/.csv) ou feed (.xml) local")
        parser.add_argument("--zip", dest="zip_file", help="ZIP de fotos (planilha)")
        parser.add_argument(
            "--map",
            action="append",
            default=[],
            metavar="TIPO=CATEGORIA",
            help='Tipo do portal -> categoria (XML). Use "TIPO=" para ignorar. Repetível.',
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Só mostra a prévia (nada é importado)"
        )

    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.is_file():
            raise CommandError(f"Arquivo não encontrado: {path}")
        source = ImportJob.Source.XML if path.suffix.lower() == ".xml" else ImportJob.Source.SHEET
        zip_upload = None
        if options["zip_file"]:
            zip_path = Path(options["zip_file"])
            if not zip_path.is_file():
                raise CommandError(f"ZIP não encontrado: {zip_path}")
            zip_upload = SimpleUploadedFile(zip_path.name, zip_path.read_bytes())
        upload = SimpleUploadedFile(path.name, path.read_bytes())
        try:
            job = importing.create_job(source, None, upload=upload, zip_upload=zip_upload)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc

        mapping = {}
        for item in options["map"]:
            portal_type, _sep, category = item.partition("=")
            mapping[portal_type.strip()] = category.strip()
        if mapping:
            importing.set_type_map(job, mapping)
        missing = importing.unmapped_types(job)
        if missing:
            raise CommandError(
                "Tipos do portal sem categoria (use --map 'TIPO=CATEGORIA'): " + "; ".join(missing)
            )

        info = importing.preview(job)
        self.stdout.write(
            f"Prévia: {info['new']} novo(s), {info['updated']} atualizado(s), "
            f"{len(info['invalid'])} com erro, {info['skipped']} ignorado(s)."
        )
        for item in info["invalid"][:20]:
            self.stdout.write(f"  linha {item['row']} ({item['ref']}): {item['message']}")
        if options["dry_run"]:
            job.delete()
            return

        importing.confirm(job)
        importing.run_all(job)
        self.stdout.write(
            self.style.SUCCESS(
                f"Concluído: {job.created_count} criado(s), {job.updated_count} atualizado(s), "
                f"{job.error_count} com erro. Detalhes: importação #{job.pk} no painel."
            )
        )
        for issue in job.errors[:20]:
            self.stdout.write(f"  [{issue['level']}] linha {issue['row']}: {issue['message']}")
