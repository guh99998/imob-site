"""Importação em lote: cria o job a partir do arquivo, confirma e processa em lotes."""

import time
import zipfile
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils import timezone

from . import history, importers, services
from .models import ImportJob, Property

BATCH_ROWS = 20
TIME_BUDGET = 20  # segundos por lote: o passo termina antes do timeout do servidor

INTERNAL_KEYS = {"row", "errors", "parse_errors", "photos", "portal_type", "skipped"}


def _flatten(exc):
    if hasattr(exc, "message_dict"):
        return "; ".join(f"{field}: {' '.join(msgs)}" for field, msgs in exc.message_dict.items())
    return " ".join(exc.messages)


# ---------- criar e preparar ----------


def create_job(source, user, *, upload=None, zip_upload=None, feed_url=""):
    """Lê o arquivo (ou o feed), guarda as linhas e devolve o job em PREVIEW.

    Levanta ValidationError (mensagem para o usuário) se o arquivo não servir.
    """
    if source == ImportJob.Source.XML:
        if upload is not None:
            data, name = upload.read(importers.MAX_XML_BYTES + 1), upload.name
        elif feed_url:
            data = services.fetch_bytes(
                feed_url, importers.MAX_XML_BYTES, field="feed_url", timeout=60
            )
            name = "feed.xml"
        else:
            raise ValidationError("Envie o arquivo XML ou informe o endereço do feed.")
        rows = importers.parse_vrsync(data)
    else:
        if upload is None:
            raise ValidationError("Envie a planilha (XLSX ou CSV).")
        data, name = upload.read(importers.MAX_SHEET_BYTES + 1), upload.name
        rows = importers.parse_sheet(data, name)
    if zip_upload is not None:
        try:
            importers.PhotoArchive(zip_upload).close()
        except (ValidationError, zipfile.BadZipFile, OSError, ValueError) as exc:
            raise ValidationError("O ZIP de fotos é inválido ou grande demais.") from exc
        zip_upload.seek(0)

    job = ImportJob(source=source, created_by=user if getattr(user, "pk", None) else None)
    job.feed_url = feed_url if source == ImportJob.Source.XML and upload is None else ""
    job.file.save(name, ContentFile(data), save=False)
    if zip_upload is not None:
        job.zip_file.save(zip_upload.name, zip_upload, save=False)
    job.rows = rows
    job.total = len(rows)
    if source == ImportJob.Source.XML:
        suggestions = {t: importers.suggest_category(t) for t in importers.portal_types(rows)}
        job.type_map = {t: name for t, name in suggestions.items() if name}
    job.save()
    return job


def unmapped_types(job):
    """Tipos do portal ainda sem categoria (nem "ignorar")."""
    if job.source != ImportJob.Source.XML:
        return []
    return [t for t in importers.portal_types(job.rows) if t not in job.type_map]


def set_type_map(job, mapping):
    """Guarda o mapeamento tipo do portal -> categoria ("" = ignorar esses imóveis)."""
    job.type_map = {**job.type_map, **mapping}
    job.save(update_fields=["type_map"])


def preview(job):
    """Confere as linhas sem gravar. Devolve contagens e a lista de linhas com erro."""
    importers.apply_type_map(job.rows, job.type_map)
    refs = {r.get("external_ref") for r in job.rows if r.get("external_ref")}
    existing = set(
        Property.objects.filter(external_ref__in=refs).values_list("external_ref", flat=True)
    )
    new, updated, skipped = importers.check_rows(job.rows, existing)
    invalid = [
        {"row": r["row"], "ref": r.get("external_ref", ""), "message": "; ".join(r["errors"])}
        for r in job.rows
        if r.get("errors")
    ]
    return {"new": new, "updated": updated, "skipped": skipped, "invalid": invalid}


def confirm(job):
    """Fecha a prévia e coloca o job para rodar (as linhas com erro serão ignoradas)."""
    if job.status != ImportJob.Status.PREVIEW or unmapped_types(job):
        raise ValidationError("Esta importação não pode ser confirmada.")
    preview(job)  # deixa `errors` de cada linha atualizado
    job.status = ImportJob.Status.RUNNING
    job.processed = job.created_count = job.updated_count = job.error_count = 0
    job.errors = []
    job.save()
    return job


# ---------- processar ----------


def process_batch(job, *, max_rows=BATCH_ROWS, budget=TIME_BUDGET):
    """Processa o próximo lote (até `max_rows` linhas ou `budget` segundos)."""
    if job.status != ImportJob.Status.RUNNING:
        return job
    archive = importers.PhotoArchive(job.zip_file.open("rb")) if job.zip_file else None
    started, handled = time.monotonic(), 0
    try:
        while job.processed < job.total and handled < max_rows:
            _process_row(job, job.rows[job.processed], archive)
            job.processed += 1
            handled += 1
            if time.monotonic() - started >= budget:
                break
    finally:
        if archive:
            archive.close()
    if job.processed >= job.total:
        job.status = ImportJob.Status.DONE
        job.finished_at = timezone.now()
    job.save(
        update_fields=[
            "status",
            "processed",
            "created_count",
            "updated_count",
            "error_count",
            "errors",
            "finished_at",
        ]
    )
    return job


def run_all(job):
    """Processa tudo sem pausa (linha de comando)."""
    while job.status == ImportJob.Status.RUNNING:
        process_batch(job, max_rows=BATCH_ROWS, budget=10**9)
    return job


def _issue(job, row, message, level="error"):
    job.errors.append(
        {"row": row["row"], "ref": row.get("external_ref", ""), "message": message, "level": level}
    )
    if level == "error":
        job.error_count += 1


def _process_row(job, row, archive):
    if row.get("skipped"):
        return
    if row.get("errors"):
        _issue(job, row, "; ".join(row["errors"]))
        return
    data = {k: v for k, v in row.items() if k not in INTERNAL_KEYS}
    try:
        prop, created, _matches = services.upsert_property(data, source=job.source_label)
    except ValidationError as exc:
        _issue(job, row, _flatten(exc))
        return
    if created:
        job.created_count += 1
    else:
        job.updated_count += 1
    # Reimportar não duplica fotos: só entram quando o imóvel ainda não tem nenhuma.
    if created or not prop.photos.exists():
        _import_photos(job, row, prop, archive)


def _import_photos(job, row, prop, archive):
    names = row.get("photos", [])
    urls = [n for n in names if n.lower().startswith(("http://", "https://"))]
    files = [n for n in names if n not in urls]
    sources = []  # (rótulo, upload|None, url|None)
    if archive is not None and (files or not urls):
        found, missing = archive.photos_for(row.get("external_ref"), files)
        sources += [(name, BytesIO(data), None) for name, data in found]
        for name in missing:
            _issue(job, row, f"foto não encontrada no ZIP: {name}", "warning")
    elif files:
        _issue(job, row, "fotos citadas, mas nenhum ZIP foi enviado", "warning")
    sources += [(url, None, url) for url in urls]
    if not sources:
        return
    before = history.snapshot(prop)
    for label, upload, url in sources:
        try:
            services.add_photo(prop, upload=upload, url=url, source=job.source_label, record=False)
        except ValidationError as exc:
            _issue(job, row, f"foto {label}: {_flatten(exc)}", "warning")
    history.record_changes(prop, before, history.snapshot(prop), None, job.source_label)
