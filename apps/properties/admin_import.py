"""Tela "Importar imóveis" do painel: enviar, mapear tipos (XML), prévia, confirmar, lotes."""

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display

from . import importers, importing
from .models import Category, ImportJob

IGNORE = "__ignore__"
PREVIEW_ERRORS_SHOWN = 50
RESULT_ISSUES_SHOWN = 100


class ImportJobForm(forms.ModelForm):
    class Meta:
        model = ImportJob
        fields = ("source", "file", "zip_file", "feed_url")

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        try:
            self.job = importing.create_job(
                cleaned["source"],
                self.user,
                upload=cleaned.get("file") or None,
                zip_upload=cleaned.get("zip_file") or None,
                feed_url=cleaned.get("feed_url", ""),
            )
        except ValidationError as exc:
            raise ValidationError(exc.messages) from exc
        self.instance = self.job  # o admin "salva" o job que já foi criado
        return cleaned


STATUS_LABELS = {
    ImportJob.Status.PREVIEW: "warning",
    ImportJob.Status.RUNNING: "info",
    ImportJob.Status.DONE: "success",
}


@admin.register(ImportJob)
class ImportJobAdmin(ModelAdmin):
    form = ImportJobForm
    list_display = (
        "created_at",
        "source",
        "status_badge",
        "total",
        "created_count",
        "updated_count",
        "error_count",
        "created_by",
    )
    list_display_links = ("created_at",)
    change_form_before_template = "admin/properties/importjob_help.html"
    fields = ("source", "file", "zip_file", "feed_url")

    @display(description=_("situação"), ordering="status", label=STATUS_LABELS)
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.user = request.user
        return form

    def has_change_permission(self, request, obj=None):
        return self.has_add_permission(request)

    def save_model(self, request, obj, form, change):
        """O job já foi criado (arquivo lido e validado) em `form.clean()`: nada a gravar."""

    def response_add(self, request, obj, post_url_continue=None):
        return redirect(reverse("admin:properties_importjob_change", args=[obj.pk]))

    def get_urls(self):
        custom = [
            path(
                "modelo-planilha/",
                self.admin_site.admin_view(self.sheet_template),
                name="properties_importjob_template",
            ),
            path(
                "<int:pk>/passo/",
                self.admin_site.admin_view(self.step),
                name="properties_importjob_step",
            ),
        ]
        return custom + super().get_urls()

    # ---- download do modelo ----

    def sheet_template(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied
        response = HttpResponse(
            importers.sheet_template(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="modelo-importacao-imoveis.xlsx"'
        return response

    # ---- página do job (prévia, progresso e resultado) ----

    def _job(self, request, pk):
        if not self.has_change_permission(request):
            raise PermissionDenied
        job = ImportJob.objects.filter(pk=pk).first()
        if job is None:
            raise Http404
        return job

    def change_view(self, request, object_id, form_url="", extra_context=None):
        job = self._job(request, object_id)
        if request.method == "POST":
            return self._handle_post(request, job)
        context = {
            **self.admin_site.each_context(request),
            "title": str(job),
            "opts": self.model._meta,
            "job": job,
            "categories": Category.objects.order_by("name").values_list("name", flat=True),
            "ignore_value": IGNORE,
        }
        if job.status == ImportJob.Status.PREVIEW:
            context["unmapped"] = importing.unmapped_types(job)
            context["type_map"] = job.type_map
            if not context["unmapped"]:
                info = importing.preview(job)
                context["preview"] = info
                context["invalid_shown"] = info["invalid"][:PREVIEW_ERRORS_SHOWN]
                context["invalid_more"] = max(0, len(info["invalid"]) - PREVIEW_ERRORS_SHOWN)
        context["progress_html"] = self._progress(request, job)
        return TemplateResponse(request, "admin/properties/importjob.html", context)

    def _handle_post(self, request, job):
        action = request.POST.get("action")
        back = redirect(reverse("admin:properties_importjob_change", args=[job.pk]))
        if job.status != ImportJob.Status.PREVIEW:
            return back
        if action == "map":
            valid = set(Category.objects.values_list("name", flat=True))
            mapping = {}
            for key, value in request.POST.items():
                portal_type = key.removeprefix("map__")
                if key.startswith("map__") and value == IGNORE:
                    mapping[portal_type] = ""
                elif key.startswith("map__") and value in valid:
                    mapping[portal_type] = value
            importing.set_type_map(job, mapping)
        elif action == "confirm":
            try:
                importing.confirm(job)
            except ValidationError as exc:
                messages.error(request, exc.messages[0])
        return back

    # ---- progresso (HTMX) ----

    def _progress(self, request, job):
        return render_to_string(
            "admin/properties/import_progress.html",
            {
                "job": job,
                "percent": int(job.processed * 100 / job.total) if job.total else 100,
                "issues": job.errors[:RESULT_ISSUES_SHOWN],
                "more_issues": max(0, len(job.errors) - RESULT_ISSUES_SHOWN),
                "step_url": reverse("admin:properties_importjob_step", args=[job.pk]),
            },
            request=request,
        )

    def step(self, request, pk):
        job = self._job(request, pk)
        if request.method != "POST":
            return redirect(reverse("admin:properties_importjob_change", args=[job.pk]))
        importing.process_batch(job)
        if getattr(request, "htmx", False):
            return HttpResponse(self._progress(request, job))
        return redirect(reverse("admin:properties_importjob_change", args=[job.pk]))
