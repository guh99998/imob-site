from functools import cached_property
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from PIL import Image, ImageOps

MAX_PHOTO_SIZE = (1600, 1200)
CODE_PREFIX = "DLM-"


def _unique_slug(model, base, max_length, **scope):
    """Slug a partir de `base`, com sufixo numérico se já existir (dentro de `scope`)."""
    base = (slugify(base) or "item")[:max_length]
    slug, n = base, 2
    while model.objects.filter(slug=slug, **scope).exists():
        suffix = f"-{n}"
        slug = base[: max_length - len(suffix)] + suffix
        n += 1
    return slug


class Category(models.Model):
    name = models.CharField(_("nome"), max_length=60, unique=True)
    slug = models.SlugField(
        unique=True, blank=True, help_text=_("Deixe em branco para gerar automaticamente.")
    )
    order = models.PositiveSmallIntegerField(
        _("ordem"), default=0, help_text=_("Categorias com número menor aparecem primeiro.")
    )
    icon = models.CharField(
        _("ícone"),
        max_length=50,
        blank=True,
        help_text=_("Opcional. Nome de um ícone do Material Symbols (ex.: home)."),
    )

    class Meta:
        verbose_name = _("categoria")
        verbose_name_plural = _("categorias")
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Category, self.name, 50)
        super().save(*args, **kwargs)


class City(models.Model):
    name = models.CharField(_("nome"), max_length=100)
    state = models.CharField(_("UF"), max_length=2)
    slug = models.SlugField(
        unique=True, blank=True, help_text=_("Deixe em branco para gerar automaticamente.")
    )

    class Meta:
        verbose_name = _("cidade")
        verbose_name_plural = _("cidades")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}/{self.state}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(City, self.name, 50)
        super().save(*args, **kwargs)


class Neighborhood(models.Model):
    city = models.ForeignKey(
        City, on_delete=models.CASCADE, related_name="neighborhoods", verbose_name=_("cidade")
    )
    name = models.CharField(_("nome"), max_length=100)
    slug = models.SlugField(blank=True, help_text=_("Deixe em branco para gerar automaticamente."))

    class Meta:
        verbose_name = _("bairro")
        verbose_name_plural = _("bairros")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["city", "slug"], name="uniq_neighborhood_city_slug")
        ]

    def __str__(self):
        return f"{self.name} - {self.city}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Neighborhood, self.name, 50, city_id=self.city_id)
        super().save(*args, **kwargs)


class Feature(models.Model):
    name = models.CharField(_("nome"), max_length=80, unique=True)
    icon = models.CharField(_("ícone"), max_length=50, blank=True)

    class Meta:
        verbose_name = _("comodidade")
        verbose_name_plural = _("comodidades")
        ordering = ["name"]

    def __str__(self):
        return self.name


PUBLIC_STATUSES = ("PUBLISHED", "RESERVED")


class PropertyQuerySet(models.QuerySet):
    def published(self):
        """O que o público vê: publicado e reservado (o resto fica só no painel)."""
        return self.filter(status__in=PUBLIC_STATUSES).order_by("-published_at", "-id")

    def available(self):
        return self.filter(status=Property.Status.PUBLISHED)


class Property(models.Model):
    class Purpose(models.TextChoices):
        SALE = "SALE", _("Venda")
        RENT = "RENT", _("Aluguel")
        BOTH = "BOTH", _("Venda e aluguel")

    class Status(models.TextChoices):
        DRAFT = "DRAFT", _("Rascunho")
        PUBLISHED = "PUBLISHED", _("Publicado")
        RESERVED = "RESERVED", _("Reservado")
        SOLD = "SOLD", _("Vendido")
        RENTED = "RENTED", _("Alugado")

    code = models.CharField(
        _("código"),
        max_length=20,
        unique=True,
        blank=True,
        help_text=_("Deixe em branco para gerar automaticamente (DLM-0001)."),
    )
    title = models.CharField(
        _("título"), max_length=200, help_text=_("Aparece no topo do anúncio.")
    )
    slug = models.SlugField(
        unique=True,
        max_length=220,
        blank=True,
        help_text=_("Endereço do anúncio no site. Deixe em branco para gerar automaticamente."),
    )
    description = models.TextField(
        _("descrição"), blank=True, help_text=_("Conte o que torna este imóvel especial.")
    )
    purpose = models.CharField(
        _("finalidade"),
        max_length=4,
        choices=Purpose,
        default=Purpose.SALE,
        help_text=_("O imóvel é para vender, alugar ou os dois?"),
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="properties", verbose_name=_("categoria")
    )
    status = models.CharField(
        _("situação"),
        max_length=10,
        choices=Status,
        default=Status.DRAFT,
        help_text=_("Rascunho não aparece no site. Mude para Publicado quando estiver pronto."),
    )

    sale_price = models.DecimalField(
        _("preço de venda"), max_digits=12, decimal_places=2, null=True, blank=True
    )
    rent_price = models.DecimalField(
        _("valor do aluguel"), max_digits=12, decimal_places=2, null=True, blank=True
    )
    condo_fee = models.DecimalField(
        _("condomínio"), max_digits=12, decimal_places=2, null=True, blank=True
    )
    iptu = models.DecimalField(_("IPTU"), max_digits=12, decimal_places=2, null=True, blank=True)

    bedrooms = models.PositiveSmallIntegerField(_("quartos"), default=0)
    suites = models.PositiveSmallIntegerField(_("suítes"), default=0)
    bathrooms = models.PositiveSmallIntegerField(_("banheiros"), default=0)
    parking_spaces = models.PositiveSmallIntegerField(_("vagas"), default=0)
    area_total = models.DecimalField(
        _("área total (m²)"), max_digits=10, decimal_places=2, null=True, blank=True
    )
    area_built = models.DecimalField(
        _("área construída (m²)"), max_digits=10, decimal_places=2, null=True, blank=True
    )

    street = models.CharField(_("rua"), max_length=200, blank=True)
    number = models.CharField(_("número"), max_length=20, blank=True)
    complement = models.CharField(_("complemento"), max_length=100, blank=True)
    zip_code = models.CharField(_("CEP"), max_length=9, blank=True)
    show_address = models.BooleanField(
        _("exibir endereço completo"),
        default=False,
        help_text=_("Desmarcado, o site mostra só o bairro e a cidade."),
    )
    neighborhood = models.ForeignKey(
        Neighborhood, on_delete=models.PROTECT, related_name="properties", verbose_name=_("bairro")
    )
    features = models.ManyToManyField(
        Feature, blank=True, related_name="properties", verbose_name=_("comodidades")
    )

    is_featured = models.BooleanField(
        _("destaque"), default=False, help_text=_("Imóveis em destaque aparecem na página inicial.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(_("publicado em"), null=True, blank=True)

    objects = PropertyQuerySet.as_manager()

    class Meta:
        verbose_name = _("imóvel")
        verbose_name_plural = _("imóveis")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.next_code()
        if not self.slug:
            self.slug = _unique_slug(Property, f"{self.code}-{self.title}", 220)
        if self.status != self.Status.DRAFT and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("properties:detail", kwargs={"slug": self.slug})

    def clean(self):
        errors = {}
        if self.purpose in (self.Purpose.SALE, self.Purpose.BOTH) and not self.sale_price:
            errors["sale_price"] = _("Informe o preço de venda.")
        if self.purpose in (self.Purpose.RENT, self.Purpose.BOTH) and not self.rent_price:
            errors["rent_price"] = _("Informe o valor do aluguel.")
        if self.is_featured and self.status in PUBLIC_STATUSES:
            from apps.core.models import SiteSettings

            limit = SiteSettings.load().max_featured
            others = Property.objects.filter(is_featured=True, status__in=PUBLIC_STATUSES)
            if self.pk:
                others = others.exclude(pk=self.pk)
            if others.count() >= limit:
                errors["is_featured"] = _(
                    "Já existem %(n)d imóveis em destaque (limite das configurações). "
                    "Tire o destaque de outro imóvel primeiro."
                ) % {"n": limit}
        if errors:
            raise ValidationError(errors)

    @classmethod
    def next_code(cls):
        numbers = [
            int(c[len(CODE_PREFIX) :])
            for c in cls.objects.filter(code__startswith=CODE_PREFIX).values_list("code", flat=True)
            if c[len(CODE_PREFIX) :].isdigit()
        ]
        return f"{CODE_PREFIX}{max(numbers, default=0) + 1:04d}"

    @property
    def cover(self):
        photos = list(self.photos.all())
        for photo in photos:
            if photo.is_cover:
                return photo
        return photos[0] if photos else None

    @property
    def is_available(self):
        return self.status == self.Status.PUBLISHED

    @property
    def display_price(self):
        if self.purpose == self.Purpose.RENT:
            return self.rent_price
        return self.sale_price or self.rent_price

    @property
    def full_address(self):
        if not self.show_address:
            return f"{self.neighborhood.name}, {self.neighborhood.city}"
        parts = [
            f"{self.street}, {self.number}".strip(", "),
            self.complement,
            str(self.neighborhood),
        ]
        return " - ".join(p for p in parts if p)


class PropertyPhoto(models.Model):
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="photos", verbose_name=_("imóvel")
    )
    image = models.ImageField(_("imagem"), upload_to="properties/%Y/%m/")
    thumb_sm = models.ImageField(upload_to="properties/thumbs/", blank=True, editable=False)
    thumb_lg = models.ImageField(upload_to="properties/thumbs/", blank=True, editable=False)
    caption = models.CharField(_("legenda"), max_length=150, blank=True)
    order = models.PositiveSmallIntegerField(_("ordem"), default=0)
    is_cover = models.BooleanField(_("capa"), default=False)

    class Meta:
        verbose_name = _("foto")
        verbose_name_plural = _("fotos")
        ordering = ["order", "id"]

    def __str__(self):
        return self.caption or f"Foto {self.pk}"

    def save(self, *args, **kwargs):
        if self.image and not self.image._committed:
            self._resize_image()
        new_image = bool(self.image) and not self.image._committed
        super().save(*args, **kwargs)
        if new_image or (self.image and not self.thumb_sm):
            self._make_thumbs()
        if self.is_cover:
            PropertyPhoto.objects.filter(property=self.property).exclude(pk=self.pk).update(
                is_cover=False
            )

    def _make_thumbs(self):
        """Miniaturas WebP (640 e 1200 px). Se falhar, o site usa a imagem original."""
        try:
            with self.image.open("rb") as fh:
                base = ImageOps.exif_transpose(Image.open(fh))
                base.load()
            if base.mode not in ("RGB", "L"):
                base = base.convert("RGB")
            stem = self.image.name.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            for field, width in (("thumb_sm", 640), ("thumb_lg", 1200)):
                img = base.copy()
                img.thumbnail((width, width * 3 // 4 + 400))
                buf = BytesIO()
                img.save(buf, format="WEBP", quality=80)
                getattr(self, field).save(
                    f"{stem}-{width}.webp", ContentFile(buf.getvalue()), save=False
                )
            super().save(update_fields=["thumb_sm", "thumb_lg"])
        except Exception:  # noqa: BLE001 - miniatura é otimização, nunca bloqueia o upload
            return

    @cached_property
    def src_sm(self):
        return (self.thumb_sm or self.image).url

    @cached_property
    def src_lg(self):
        return (self.thumb_lg or self.image).url

    @cached_property
    def srcset(self):
        if self.thumb_sm and self.thumb_lg:
            return f"{self.thumb_sm.url} 640w, {self.thumb_lg.url} 1200w"
        return ""

    def _resize_image(self):
        img = ImageOps.exif_transpose(Image.open(self.image))
        if img.width <= MAX_PHOTO_SIZE[0] and img.height <= MAX_PHOTO_SIZE[1]:
            self.image.seek(0)
            return
        fmt = "PNG" if img.format == "PNG" else "JPEG"
        if fmt == "JPEG" and img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.thumbnail(MAX_PHOTO_SIZE)
        buf = BytesIO()
        img.save(buf, format=fmt, quality=85)
        name = self.image.name.rsplit(".", 1)[0] + (".png" if fmt == "PNG" else ".jpg")
        self.image.save(name, ContentFile(buf.getvalue()), save=False)
