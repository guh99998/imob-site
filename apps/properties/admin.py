import re
from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Max
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import DropdownFilter
from unfold.decorators import action, display
from unfold.widgets import UnfoldAdminCheckboxSelectMultipleWidget

from apps.core.admin_filters import AdvancedSearchMixin, dropdown_filter
from apps.core.admin_masks import MaskedAdminMixin
from apps.core.features import enabled
from apps.crm import documents as crm_documents
from apps.people.scoping import ScopedByRoleMixin, is_scoped

from . import duplicates, history, reviews
from .models import (
    PUBLIC_STATUSES,
    Category,
    City,
    Feature,
    Neighborhood,
    Property,
    PropertyPhoto,
)

REVIEW_LABELS = {"overdue": "danger", "soon": "warning", "ok": "success"}

STATUS_LABELS = {
    Property.Status.DRAFT: "warning",
    Property.Status.PUBLISHED: "success",
    Property.Status.RESERVED: "info",
    Property.Status.SOLD: "danger",
    Property.Status.RENTED: "danger",
}


format_brl = history.format_brl


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "code_prefix", "properties_count")
    search_fields = ("name",)
    fields = ("name", "code_prefix")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_count=Count("properties"))

    @display(description=_("imóveis"), ordering="_count")
    def properties_count(self, obj):
        return obj._count


class NeighborhoodInline(TabularInline):
    model = Neighborhood
    extra = 1
    fields = ("name",)
    verbose_name = _("bairro")
    verbose_name_plural = _("bairros desta cidade")


@admin.register(City)
class CityAdmin(MaskedAdminMixin, ModelAdmin):
    masks = {"state": "uf"}
    list_display = ("name", "state", "neighborhoods_count")
    search_fields = ("name",)
    fields = ("name", "state")
    inlines = [NeighborhoodInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_count=Count("neighborhoods"))

    @display(description=_("bairros"), ordering="_count")
    def neighborhoods_count(self, obj):
        return obj._count


@admin.register(Neighborhood)
class NeighborhoodAdmin(AdvancedSearchMixin, ModelAdmin):
    list_display = ("name", "city")
    list_filter = ("city",)
    search_fields = ("name", "city__name")
    autocomplete_fields = ("city",)
    fields = ("city", "name")


@admin.register(Feature)
class FeatureAdmin(ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True
    frame_template = "admin/properties/widgets/bulk_photos.html"

    def render(self, name, value, attrs=None, renderer=None):
        # O renderer de formulários só enxerga templates dos apps; a moldura fica em templates/.
        input_html = super().render(name, value, attrs, renderer)
        return render_to_string(self.frame_template, {"input_html": input_html})


class MultipleImageField(forms.ImageField):
    """Aceita vários arquivos de uma vez (cada um validado como imagem)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleImageInput(attrs={"accept": "image/*"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single = super().clean
        if isinstance(data, (list, tuple)):
            return [single(d, initial) for d in data if d]
        return [single(data, initial)] if data else []


def duplicates_panel(matches, fallback=False):
    """Painel "possível duplicado" (cards) usado pela checagem ao vivo e pelo erro do formulário."""
    items = [
        {
            "prop": prop,
            "level": duplicates.LEVEL_LABELS[level],
            "price": format_brl(prop.display_price) if prop.display_price else "",
            "cover": prop.cover,
            "url": reverse("admin:properties_property_change", args=[prop.pk]),
        }
        for prop, level in matches
    ]
    return render_to_string(
        "admin/properties/duplicates_panel.html", {"items": items, "fallback": fallback}
    )


class PropertyAdminForm(forms.ModelForm):
    bulk_photos = MultipleImageField(
        label=_("Adicionar várias fotos"),
        required=False,
        help_text=_(
            "Selecione várias fotos de uma vez (Ctrl/Shift + clique). Elas entram no fim da "
            "lista; depois é só arrastar na aba Fotos para mudar a ordem."
        ),
    )

    PLACEHOLDERS = {
        "title": _("Ex.: Casa 3 quartos com piscina no Jardim América"),
        "zip_code": "00000-000",
        "number": _("Ex.: 120"),
        "complement": _("Ex.: Apto 42, bloco B"),
        "sale_price": _("R$ 0,00"),
        "rent_price": _("R$ 0,00"),
        "condo_fee": _("R$ 0,00"),
        "iptu": _("R$ 0,00"),
        "area_total": _("m²"),
        "area_built": _("m²"),
    }

    # Ids dos imóveis que o usuário marcou como "não é duplicado" (ou "on" na confirmação sem JS).
    not_duplicate = forms.CharField(required=False, widget=forms.HiddenInput)
    user = None  # preenchido por PropertyAdmin.get_form

    class Meta:
        model = Property
        fields = "__all__"  # noqa: DJ007 - o admin limita aos campos dos fieldsets

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "category" in self.fields:
            self.fields["category"].empty_label = _("Selecione a categoria")
        for name, text in self.PLACEHOLDERS.items():
            if name in self.fields:
                self.fields[name].widget.attrs.setdefault("placeholder", str(text))

    def confirmed_ids(self):
        """None = sem confirmação; conjunto de ids confirmados (vazio = todos os parecidos)."""
        raw = (self.cleaned_data.get("not_duplicate") or "").strip()
        if not raw or raw.lower() in {"false", "0"}:
            return None
        return {int(n) for n in re.findall(r"\d+", raw)}

    def duplicate_matches(self):
        """Parecidos de um cadastro novo. O Corretor não vê imóveis dos outros: só o aviso."""
        if self.instance.pk or (self.user is not None and is_scoped(self.user)):
            return []
        return duplicates.find_duplicates(duplicates.unsaved_from(self.cleaned_data))

    def clean(self):
        cleaned = super().clean()
        matches = self.duplicate_matches()
        ids = self.confirmed_ids()
        pending = [m for m in matches if ids is None or (ids and m[0].pk not in ids)]
        if pending:
            # Sem JS: o painel vira erro e o campo escondido vira a caixa de confirmação.
            field = self.fields["not_duplicate"]
            field.widget = forms.CheckboxInput()
            field.label = _("Confirmo que este imóvel não é duplicado")
            raise ValidationError(mark_safe(duplicates_panel(matches, fallback=True)))  # noqa: S308
        return cleaned


class PropertyPhotoInline(TabularInline):
    model = PropertyPhoto
    extra = 3
    tab = True
    fields = ("image", "preview", "caption", "is_cover")
    readonly_fields = ("preview",)
    ordering_field = "order"
    hide_ordering_field = True
    verbose_name = _("foto")
    verbose_name_plural = _("Fotos (arraste para mudar a ordem)")

    @display(description=_("pré-visualização"))
    def preview(self, obj):
        if obj.pk and obj.image:
            return format_html('<img src="{}" style="height:60px">', obj.image.url)
        return "-"


class ReviewFilter(DropdownFilter):
    title = _("revisão")
    parameter_name = "review"

    def lookups(self, request, model_admin):
        return [
            ("overdue", _("Vencida")),
            ("soon", _("Vence em 7 dias")),
            ("ok", _("Em dia")),
        ]

    def queryset(self, request, queryset):
        public = queryset.filter(status__in=PUBLIC_STATUSES)
        today = timezone.localdate()
        value = self.value()
        if value == "overdue":
            return reviews.pending(queryset)
        if value == "soon":
            return public.filter(
                review_due__gt=today, review_due__lte=today + timedelta(days=reviews.SOON_DAYS)
            )
        if value == "ok":
            return public.filter(review_due__gt=today + timedelta(days=reviews.SOON_DAYS))
        return queryset


@admin.register(Property)
class PropertyAdmin(AdvancedSearchMixin, ScopedByRoleMixin, MaskedAdminMixin, ModelAdmin):
    masks = {
        "sale_price": "money",
        "rent_price": "money",
        "condo_fee": "money",
        "iptu": "money",
        "area_total": "area",
        "area_built": "area",
        "zip_code": "cep",
    }
    readonly_fields = (
        "code_display",
        "audit_created",
        "audit_updated",
        "audit_reviewed",
        "favorites_count",
        "external_ref",
    )
    list_display = (
        "cover_preview",
        "code",
        "title",
        "category",
        "price",
        "status_badge",
        "review_badge",
        "duplicate_badge",
        "favorites_count",
        "is_featured",
    )
    list_display_links = ("code", "title")
    list_filter = (
        "status",
        "purpose",
        "category",
        "neighborhood__city",
        "duplicate_hint",
        ReviewFilter,
    )
    list_editable = ("is_featured",)
    list_select_related = ("category", "neighborhood__city")
    search_fields = ("code", "title", "street", "neighborhood__name")
    search_help_text = _("Buscar por código, título, rua ou bairro")
    autocomplete_fields = ("neighborhood",)
    form = PropertyAdminForm
    change_form_before_template = "admin/properties/duplicates_slot.html"
    change_form_after_template = "admin/properties/history.html"
    inlines = [PropertyPhotoInline]

    class Media:
        js = ("properties/admin/duplicates.js",)

    actions = [
        "publish",
        "mark_sold",
        "mark_rented",
        "feature",
        "mark_reviewed",
        "dismiss_duplicates",
    ]
    actions_row = ["view_on_site_action", "mark_reviewed_row", "generate_document_row"]
    actions_detail = ["generate_document_detail"]
    warn_unsaved_form = True
    fieldsets = (
        (
            _("Informações"),
            {
                "classes": ["tab"],
                "fields": (
                    "code_display",
                    "title",
                    "category",
                    "purpose",
                    "status",
                    "is_featured",
                    "review_due",
                    "description",
                    "not_duplicate",
                ),
            },
        ),
        (
            _("Valores"),
            {"classes": ["tab"], "fields": ("sale_price", "rent_price", "condo_fee", "iptu")},
        ),
        (
            _("Enviar fotos"),
            {"classes": ["tab"], "fields": ("bulk_photos",)},
        ),
        (
            _("Características"),
            {
                "classes": ["tab"],
                "fields": (
                    "bedrooms",
                    "suites",
                    "bathrooms",
                    "parking_spaces",
                    "area_total",
                    "area_built",
                    "features",
                ),
            },
        ),
        (
            _("Localização"),
            {
                "classes": ["tab"],
                "fields": (
                    "neighborhood",
                    "street",
                    "number",
                    "complement",
                    "zip_code",
                    "show_address",
                ),
            },
        ),
    )

    PEOPLE_FIELDS = {"broker": "brokers", "partner": "partners", "owner": "owners"}

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        hidden = {f for f, feat in self.PEOPLE_FIELDS.items() if not enabled(feat)}
        people = ["source", *(f for f in self.PEOPLE_FIELDS if f not in hidden)]
        fieldsets.append((_("Responsáveis"), {"classes": ["tab"], "fields": people}))
        if obj is not None:
            fieldsets.append(
                (
                    _("Registro"),
                    {
                        "classes": ["tab"],
                        "fields": (
                            "audit_created",
                            "audit_updated",
                            "audit_reviewed",
                            "favorites_count",
                            "external_ref",
                        ),
                    },
                )
            )
        return fieldsets

    def get_list_filter(self, request):
        extra = [f for f, feat in self.PEOPLE_FIELDS.items() if enabled(feat)]
        return [*super().get_list_filter(request), *(dropdown_filter(Property, f) for f in extra)]

    def get_search_fields(self, request):
        extra = [f"{f}__name" for f, feat in self.PEOPLE_FIELDS.items() if enabled(feat)]
        return (*self.search_fields, *extra)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        broker = getattr(request.user, "broker", None)
        if broker and "broker" not in initial:
            initial["broker"] = broker.pk
        return initial

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "broker":
            from apps.people.models import Broker

            kwargs["queryset"] = Broker.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        prop = self.get_queryset(request).filter(pk=object_id).first()
        if prop is not None:
            extra_context["history_entries"] = list(prop.changes.select_related("user")[:50])
        return super().change_view(request, object_id, form_url, extra_context)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.user = request.user
        return form

    def get_urls(self):
        custom = [
            path(
                "check-duplicates/",
                self.admin_site.admin_view(self.check_duplicates),
                name="properties_property_check_duplicates",
            )
        ]
        return custom + super().get_urls()

    def check_duplicates(self, request):
        """Checagem ao vivo do cadastro: devolve o painel de parecidos (204 se não há)."""
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        if not self.has_add_permission(request):
            return HttpResponse(status=403)
        form = self.get_form(request)(request.POST)
        form._clean_fields()  # só interessa o que já é válido; erros de campo não importam aqui
        prop = duplicates.unsaved_from(form.cleaned_data)
        matches = duplicates.find_duplicates(prop)
        if not matches:
            return HttpResponse(status=204)
        if is_scoped(request.user):  # o Corretor não vê imóveis dos outros
            return HttpResponse(
                render_to_string("admin/properties/duplicates_panel.html", {"generic": True})
            )
        return HttpResponse(duplicates_panel(matches))

    def save_model(self, request, obj, form, change):
        adding = not obj.pk
        before = None if adding else history.snapshot(Property.objects.get(pk=obj.pk))
        if adding:
            obj.created_by = request.user
        obj.updated_by = request.user
        if is_scoped(request.user) and not obj.broker_id:
            obj.broker = getattr(request.user, "broker", None)
        super().save_model(request, obj, form, change)
        if form is not None:
            form._history_before, form._history_row = before, None
            if adding:
                form._history_row = history.record_created(obj, request.user)
            elif before is not None:
                form._history_row = history.record_changes(
                    obj, before, history.snapshot(obj), request.user
                )
        ids = form.confirmed_ids() if adding and not is_scoped(request.user) else None
        if ids is not None:
            others = ids or {m.pk for m, _level in duplicates.find_duplicates(obj)}
            duplicates.dismiss_pair_ids(request.user, obj, others)
        self.warn_duplicates(request, obj)

    def warn_duplicates(self, request, obj):
        """Aviso (não bloqueia): pode ser outra unidade do mesmo prédio."""
        matches = duplicates.refresh_hints(obj)
        if not matches:
            return
        if is_scoped(request.user):  # o Corretor não vê imóveis dos outros
            self.message_user(
                request,
                _("Já existe no sistema um imóvel parecido com este. Fale com o gerente."),
                messages.WARNING,
            )
            return
        links = format_html_join(
            ", ",
            '<a href="{}" class="underline">{}</a> ({})',
            (
                (
                    reverse("admin:properties_property_change", args=[m.pk]),
                    f"{m.code} – {m.title}",
                    duplicates.LEVEL_LABELS[level],
                )
                for m, level in matches[:5]
            ),
        )
        self.message_user(
            request,
            format_html("{} {}", _("Possível duplicado de:"), links),
            messages.WARNING,
        )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        self._add_photos(request, form)
        before = getattr(form, "_history_before", None)
        if before is not None:  # comodidades e fotos só mudam depois do save_model
            form._history_row = history.append_changes(
                getattr(form, "_history_row", None),
                form.instance,
                before,
                history.snapshot(form.instance),
                request.user,
            )

    def _add_photos(self, request, form):
        files = form.cleaned_data.get("bulk_photos") or []
        if not files:
            return
        prop = form.instance
        last = prop.photos.aggregate(m=Max("order"))["m"]
        start = 0 if last is None else last + 1
        has_cover = prop.photos.filter(is_cover=True).exists()
        for i, upload in enumerate(files):
            PropertyPhoto.objects.create(
                property=prop, image=upload, order=start + i, is_cover=not has_cover and i == 0
            )
        self.message_user(request, _("%d foto(s) adicionada(s).") % len(files), messages.SUCCESS)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and not is_scoped(request.user)

    @display(description=_("cadastrado por"))
    def audit_created(self, obj):
        if not obj or not obj.created_by:
            return "-"
        return (
            f"{obj.created_by.get_full_name() or obj.created_by} em {obj.created_at:%d/%m/%Y %H:%M}"
        )

    @display(description=_("última revisão"))
    def audit_reviewed(self, obj):
        if not obj or not obj.last_reviewed_at:
            return "-"
        who = obj.last_reviewed_by
        name = (who.get_full_name() or who) if who else "-"
        return f"{name} em {timezone.localtime(obj.last_reviewed_at):%d/%m/%Y %H:%M}"

    @display(description=_("revisão"), ordering="review_due", label=REVIEW_LABELS)
    def review_badge(self, obj):
        if obj.status not in PUBLIC_STATUSES or not obj.review_due:
            return "-"
        today = timezone.localdate()
        if obj.review_due <= today:
            return "overdue", _("Vencida (%s)") % f"{obj.review_due:%d/%m}"
        if obj.review_due <= today + timedelta(days=reviews.SOON_DAYS):
            return "soon", _("Até %s") % f"{obj.review_due:%d/%m}"
        return "ok", f"{obj.review_due:%d/%m/%Y}"

    @display(description=_("última edição"))
    def audit_updated(self, obj):
        if not obj or not obj.updated_by:
            return "-"
        return (
            f"{obj.updated_by.get_full_name() or obj.updated_by} em {obj.updated_at:%d/%m/%Y %H:%M}"
        )

    @display(description=_("código"))
    def code_display(self, obj):
        return obj.code if obj and obj.pk else _("Gerado ao salvar")

    @display(description=_("preço"), ordering="sale_price")
    def price(self, obj):
        value = obj.display_price
        return format_brl(value) if value else "-"

    @display(description=_("situação"), ordering="status", label=STATUS_LABELS)
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()

    @display(description=_("duplicado?"), ordering="duplicate_hint", label={True: "warning"})
    def duplicate_badge(self, obj):
        return (True, _("Possível")) if obj.duplicate_hint else "-"

    @display(description=_("capa"))
    def cover_preview(self, obj):
        cover = obj.cover
        if cover:
            return format_html(
                '<img src="{}" style="height:40px;width:56px;object-fit:cover">', cover.image.url
            )
        return "-"

    SEARCH_LOOKUPS = {
        "purpose__in",
        "category__id__in",
        "neighborhood__city__id__exact",
        "sale_price__gte",
        "sale_price__lte",
        "rent_price__gte",
        "rent_price__lte",
        "bedrooms__gte",
        "parking_spaces__gte",
    }

    def lookup_allowed(self, lookup, value, request):
        """Permite os filtros de "Ver imóveis compatíveis" (procuras de clientes)."""
        return lookup in self.SEARCH_LOOKUPS or super().lookup_allowed(lookup, value, request)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("photos")

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "features":
            kwargs["widget"] = UnfoldAdminCheckboxSelectMultipleWidget
            kwargs["queryset"] = Feature.objects.order_by("name")
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def has_generate_document_permission(self, request, object_id=None):
        return crm_documents.can_generate(request)

    @action(
        description=_("Gerar documento"),
        url_path="gerar-documento",
        permissions=["generate_document"],
    )
    def generate_document_row(self, request, object_id):
        prop = get_object_or_404(self.get_queryset(request), pk=object_id)
        return redirect(crm_documents.new_document_url(property=prop))

    @action(
        description=_("Gerar documento"),
        url_path="gerar-documento-detalhe",
        permissions=["generate_document"],
    )
    def generate_document_detail(self, request, object_id):
        prop = get_object_or_404(self.get_queryset(request), pk=object_id)
        return redirect(crm_documents.new_document_url(property=prop))

    @action(description=_("Ver no site"), url_path="ver-no-site")
    def view_on_site_action(self, request, object_id):
        prop = get_object_or_404(Property, pk=object_id)
        if prop.status not in PUBLIC_STATUSES:
            self.message_user(request, _("Este imóvel não está visível no site."), messages.WARNING)
            return redirect(reverse("admin:properties_property_change", args=[prop.pk]))
        return redirect(prop.get_absolute_url())

    def _apply(self, request, queryset, mutate):
        """Aplica `mutate` a cada imóvel pelo save() (prazos e histórico); devolve o total."""
        total = 0
        for prop in queryset:
            before = history.snapshot(prop)
            mutate(prop)
            prop.updated_by = request.user
            prop.save()
            history.record_changes(
                prop, before, history.snapshot(prop), request.user, source="Ação em lote"
            )
            total += 1
        return total

    @admin.action(description=_("Publicar selecionados"))
    def publish(self, request, queryset):
        n = self._apply(
            request, queryset, lambda p: setattr(p, "status", Property.Status.PUBLISHED)
        )
        self.message_user(request, _("%d imóvel(is) publicado(s).") % n, messages.SUCCESS)

    @admin.action(description=_("Marcar como vendido"))
    def mark_sold(self, request, queryset):
        self._apply(request, queryset, lambda p: setattr(p, "status", Property.Status.SOLD))

    @admin.action(description=_("Marcar como alugado"))
    def mark_rented(self, request, queryset):
        self._apply(request, queryset, lambda p: setattr(p, "status", Property.Status.RENTED))

    @admin.action(description=_("Marcar como revisado"), permissions=["change"])
    def mark_reviewed(self, request, queryset):
        n = self._apply(request, queryset, lambda p: reviews.mark_reviewed(p, request.user))
        self.message_user(
            request, _("%d imóvel(is) marcado(s) como revisado(s).") % n, messages.SUCCESS
        )

    @action(
        description=_("Marcar como revisado"),
        url_path="marcar-revisado",
        permissions=["change"],
    )
    def mark_reviewed_row(self, request, object_id):
        self._apply(
            request,
            self.get_queryset(request).filter(pk=object_id),
            lambda p: reviews.mark_reviewed(p, request.user),
        )
        messages.success(request, _("Imóvel marcado como revisado."))
        return redirect(reverse("admin:properties_property_changelist"))

    @admin.action(description=_("Marcar como não duplicado"), permissions=["change"])
    def dismiss_duplicates(self, request, queryset):
        pairs = duplicates.dismiss(request.user, queryset)
        self.message_user(
            request, _("%d par(es) marcado(s) como não duplicado.") % pairs, messages.SUCCESS
        )

    @admin.action(description=_("Destacar selecionados"))
    def feature(self, request, queryset):
        limit = settings.MAX_FEATURED
        current = Property.objects.filter(is_featured=True, status__in=PUBLIC_STATUSES).count()
        to_add = queryset.filter(is_featured=False, status__in=PUBLIC_STATUSES).count()
        if current + to_add > limit:
            self.message_user(
                request,
                _(
                    "Limite de %(limit)d destaques. Hoje há %(current)d; tire o destaque de "
                    "algum imóvel antes."
                )
                % {"limit": limit, "current": current},
                messages.ERROR,
            )
            return
        self._apply(request, queryset, lambda p: setattr(p, "is_featured", True))


from . import admin_import  # noqa: E402,F401 - registra o ImportJobAdmin
