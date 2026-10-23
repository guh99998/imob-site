from django.db import models
from django.utils.translation import gettext_lazy as _


class Lead(models.Model):
    class Status(models.TextChoices):
        NEW = "NEW", _("Novo")
        CONTACTED = "CONTACTED", _("Contatado")
        CLOSED = "CLOSED", _("Encerrado")

    class Kind(models.TextChoices):
        PROPERTY = "PROPERTY", _("Interesse em imóvel")
        CONTACT = "CONTACT", _("Contato")
        LISTING = "LISTING", _("Quer anunciar")

    kind = models.CharField(_("tipo"), max_length=8, choices=Kind, default=Kind.PROPERTY)
    property = models.ForeignKey(
        "properties.Property",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="leads",
        verbose_name=_("imóvel"),
    )
    name = models.CharField(_("nome"), max_length=120)
    email = models.EmailField(_("email"))
    phone = models.CharField(_("telefone"), max_length=30, blank=True)
    message = models.TextField(_("mensagem"))
    status = models.CharField(_("situação"), max_length=10, choices=Status, default=Status.NEW)
    client = models.ForeignKey(
        "crm.Client",
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="leads",
        verbose_name=_("cliente"),
    )
    created_at = models.DateTimeField(_("recebido em"), auto_now_add=True)

    class Meta:
        verbose_name = _("contato")
        verbose_name_plural = _("contatos")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.created_at:%d/%m/%Y})"


class PropertySearch(models.Model):
    """Cliente que "procura um imóvel": o corretor cruza com o estoque."""

    class Status(models.TextChoices):
        NEW = "NEW", _("Novo")
        CONTACTED = "CONTACTED", _("Contatado")
        CLOSED = "CLOSED", _("Encerrado")

    name = models.CharField(_("nome"), max_length=120)
    whatsapp = models.CharField(_("WhatsApp"), max_length=20)
    email = models.EmailField(_("email"), blank=True)
    purpose = models.CharField(
        _("finalidade"),
        max_length=4,
        choices=[("SALE", _("Comprar")), ("RENT", _("Alugar"))],
        default="SALE",
    )
    categories = models.ManyToManyField(
        "properties.Category", blank=True, related_name="searches", verbose_name=_("categorias")
    )
    city = models.ForeignKey(
        "properties.City",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="searches",
        verbose_name=_("cidade"),
    )
    neighborhoods = models.CharField(_("bairros"), max_length=200, blank=True)
    min_price = models.DecimalField(
        _("preço mínimo"), max_digits=12, decimal_places=2, null=True, blank=True
    )
    max_price = models.DecimalField(
        _("preço máximo"), max_digits=12, decimal_places=2, null=True, blank=True
    )
    min_bedrooms = models.PositiveSmallIntegerField(_("quartos (mín.)"), default=0)
    min_parking = models.PositiveSmallIntegerField(_("vagas (mín.)"), default=0)
    notes = models.TextField(_("observações"), blank=True)
    lgpd_consent = models.BooleanField(_("aceite LGPD"), default=False)
    status = models.CharField(_("situação"), max_length=10, choices=Status, default=Status.NEW)
    client = models.ForeignKey(
        "crm.Client",
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="searches",
        verbose_name=_("cliente"),
    )
    created_at = models.DateTimeField(_("recebida em"), auto_now_add=True)

    class Meta:
        verbose_name = _("procura de cliente")
        verbose_name_plural = _("procuras de clientes")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.created_at:%d/%m/%Y})"

    def matching_query(self):
        """Parâmetros (lookups de admin) para listar imóveis compatíveis."""
        params = {}
        price = "rent_price" if self.purpose == "RENT" else "sale_price"
        params["purpose__in"] = f"{self.purpose},BOTH"
        ids = list(self.categories.values_list("pk", flat=True))
        if ids:
            params["category__id__in"] = ",".join(map(str, ids))
        if self.city_id:
            params["neighborhood__city__id__exact"] = self.city_id
        if self.min_price:
            params[f"{price}__gte"] = self.min_price
        if self.max_price:
            params[f"{price}__lte"] = self.max_price
        if self.min_bedrooms:
            params["bedrooms__gte"] = self.min_bedrooms
        if self.min_parking:
            params["parking_spaces__gte"] = self.min_parking
        return params
