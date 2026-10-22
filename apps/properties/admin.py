from django import forms
from django.contrib import admin, messages
from django.db.models import Count, Max
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action, display

from apps.core.admin_filters import AdvancedSearchMixin, dropdown_filter
from apps.core.admin_masks import MaskedAdminMixin
from apps.core.features import enabled
from apps.core.models import SiteSettings
from apps.people.scoping import ScopedByRoleMixin, is_scoped

from .models import (
    PUBLIC_STATUSES,
    Category,
    City,
    Feature,
    Neighborhood,
    Property,
    PropertyPhoto,
)

STATUS_LABELS = {
    Property.Status.DRAFT: "warning",
    Property.Status.PUBLISHED: "success",
    Property.Status.RESERVED: "info",
    Property.Status.SOLD: "danger",
    Property.Status.RENTED: "danger",
}


def format_brl(value):
    return "R$ " + f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "code_prefix", "properties_count")
    search_fields = ("name",)
    fields = ("name", "code_prefix", "order", "icon")
    ordering_field = "order"
    hide_ordering_field = True

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
    list_display = ("name", "icon")
    search_fields = ("name",)


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


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


class PropertyAdminForm(forms.ModelForm):
    bulk_photos = MultipleImageField(
        label=_("Adicionar várias fotos"),
        required=False,
        help_text=_(
            "Selecione várias fotos de uma vez (Ctrl/Shift + clique). Elas entram no fim da "
            "lista; depois é só arrastar na aba Fotos para mudar a ordem."
        ),
    )

    class Meta:
        model = Property
        fields = "__all__"  # noqa: DJ007 - o admin limita aos campos dos fieldsets


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
    readonly_fields = ("code_display", "audit_created", "audit_updated")
    list_display = (
        "cover_preview",
        "code",
        "title",
        "category",
        "price",
        "status_badge",
        "is_featured",
    )
    list_display_links = ("code", "title")
    list_filter = ("status", "purpose", "category", "neighborhood__city")
    list_editable = ("is_featured",)
    list_select_related = ("category", "neighborhood__city")
    search_fields = ("code", "title", "street", "neighborhood__name")
    search_help_text = _("Buscar por código, título, rua ou bairro")
    autocomplete_fields = ("neighborhood",)
    filter_horizontal = ("features",)
    form = PropertyAdminForm
    inlines = [PropertyPhotoInline]
    actions = ["publish", "mark_sold", "mark_rented", "feature"]
    actions_row = ["view_on_site_action"]
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
                    "description",
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
                (_("Registro"), {"classes": ["tab"], "fields": ("audit_created", "audit_updated")})
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

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        if is_scoped(request.user) and not obj.broker_id:
            obj.broker = getattr(request.user, "broker", None)
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
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

    @action(description=_("Ver no site"), url_path="ver-no-site")
    def view_on_site_action(self, request, object_id):
        prop = get_object_or_404(Property, pk=object_id)
        if prop.status not in PUBLIC_STATUSES:
            self.message_user(request, _("Este imóvel não está visível no site."), messages.WARNING)
            return redirect(reverse("admin:properties_property_change", args=[prop.pk]))
        return redirect(prop.get_absolute_url())

    @admin.action(description=_("Publicar selecionados"))
    def publish(self, request, queryset):
        queryset.filter(published_at__isnull=True).update(published_at=timezone.now())
        n = queryset.update(status=Property.Status.PUBLISHED)
        self.message_user(request, _("%d imóvel(is) publicado(s).") % n, messages.SUCCESS)

    @admin.action(description=_("Marcar como vendido"))
    def mark_sold(self, request, queryset):
        queryset.update(status=Property.Status.SOLD)

    @admin.action(description=_("Marcar como alugado"))
    def mark_rented(self, request, queryset):
        queryset.update(status=Property.Status.RENTED)

    @admin.action(description=_("Destacar selecionados"))
    def feature(self, request, queryset):
        limit = SiteSettings.load().max_featured
        current = Property.objects.filter(is_featured=True, status__in=PUBLIC_STATUSES).count()
        to_add = queryset.filter(is_featured=False, status__in=PUBLIC_STATUSES).count()
        if current + to_add > limit:
            self.message_user(
                request,
                _(
                    "Limite de %(limit)d destaques. Hoje há %(current)d; tire o destaque de "
                    "algum imóvel antes (ou aumente o limite em Configurações)."
                )
                % {"limit": limit, "current": current},
                messages.ERROR,
            )
            return
        queryset.update(is_featured=True)
