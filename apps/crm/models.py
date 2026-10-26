import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.people.models import QualifiedPerson


def normalize_phone(text):
    """Só dígitos, sem o 55 do país. Número que não parece telefone vira "" (não casa)."""
    digits = re.sub(r"\D", "", text or "")
    if digits.startswith("55") and len(digits) in (12, 13):
        digits = digits[2:]
    return digits if len(digits) in (10, 11) else ""


class Client(QualifiedPerson, models.Model):
    class Source(models.TextChoices):
        SITE = "SITE", _("Site")
        SEARCH = "SEARCH", _("Procuro um imóvel")
        LISTING = "LISTING", _("Quer anunciar")
        REFERRAL = "REFERRAL", _("Indicação")
        PORTAL = "PORTAL", _("Portal")
        API = "API", _("API")
        OTHER = "OTHER", _("Outro")

    class Stage(models.TextChoices):
        NEW = "NEW", _("Novo")
        IN_PROGRESS = "IN_PROGRESS", _("Em atendimento")
        VISIT = "VISIT", _("Visita agendada")
        PROPOSAL = "PROPOSAL", _("Proposta")
        WON = "WON", _("Fechado")
        LOST = "LOST", _("Perdido")

    class Purpose(models.TextChoices):
        SALE = "SALE", _("Comprar")
        RENT = "RENT", _("Alugar")

    name = models.CharField(_("nome"), max_length=150)
    whatsapp = models.CharField(_("WhatsApp"), max_length=30, blank=True)
    phone_key = models.CharField(max_length=11, blank=True, editable=False)
    email = models.EmailField(_("email"), blank=True)
    source = models.CharField(_("origem"), max_length=10, choices=Source, default=Source.OTHER)
    broker = models.ForeignKey(
        "people.Broker",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="clients",
        verbose_name=_("corretor responsável"),
    )
    stage = models.CharField(_("etapa"), max_length=12, choices=Stage, default=Stage.NEW)
    purpose = models.CharField(
        _("quer"), max_length=4, choices=Purpose, blank=True, help_text=_("Comprar ou alugar.")
    )
    min_price = models.DecimalField(
        _("preço mínimo"), max_digits=12, decimal_places=2, null=True, blank=True
    )
    max_price = models.DecimalField(
        _("preço máximo"), max_digits=12, decimal_places=2, null=True, blank=True
    )
    tags = models.CharField(
        _("etiquetas"), max_length=200, blank=True, help_text=_("Separe por vírgula.")
    )
    notes = models.TextField(_("observações"), blank=True)
    lgpd_consent = models.BooleanField(_("aceite LGPD"), default=False)
    lgpd_consent_at = models.DateTimeField(_("aceite em"), null=True, blank=True)
    anonymized_at = models.DateTimeField(_("anonimizado em"), null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(_("cadastrado em"), auto_now_add=True)
    updated_at = models.DateTimeField(_("alterado em"), auto_now=True)

    class Meta:
        verbose_name = _("cliente")
        verbose_name_plural = _("clientes")
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["phone_key"],
                condition=~models.Q(phone_key=""),
                name="client_phone_key_unique",
            )
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.phone_key = normalize_phone(self.whatsapp)
        if self.lgpd_consent and not self.lgpd_consent_at:
            self.lgpd_consent_at = timezone.now()
        super().save(*args, **kwargs)

    def clean(self):
        self.phone_key = normalize_phone(self.whatsapp)
        if self.whatsapp and not self.phone_key:
            raise ValidationError({"whatsapp": _("Informe o DDD e o número.")})
        if self.phone_key:
            clash = Client.objects.filter(phone_key=self.phone_key).exclude(pk=self.pk).first()
            if clash:
                raise ValidationError(
                    {"whatsapp": _("Este WhatsApp já é do cliente %(name)s.") % {"name": clash}}
                )

    def matching_query(self):
        """Lookups do admin de imóveis para listar o que combina com o interesse do cliente."""
        purpose = self.purpose or "SALE"
        price = "rent_price" if purpose == "RENT" else "sale_price"
        params = {"purpose__in": f"{purpose},BOTH"}
        if self.min_price:
            params[f"{price}__gte"] = self.min_price
        if self.max_price:
            params[f"{price}__lte"] = self.max_price
        return params


class Interaction(models.Model):
    class Kind(models.TextChoices):
        CALL = "CALL", _("Ligação")
        WHATSAPP = "WHATSAPP", _("WhatsApp")
        EMAIL = "EMAIL", _("Email")
        VISIT = "VISIT", _("Visita")
        NOTE = "NOTE", _("Anotação")

    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="interactions", verbose_name=_("cliente")
    )
    kind = models.CharField(_("tipo"), max_length=10, choices=Kind, default=Kind.NOTE)
    happened_at = models.DateTimeField(_("quando"), default=timezone.now)
    property = models.ForeignKey(
        "properties.Property",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="interactions",
        verbose_name=_("imóvel"),
    )
    text = models.TextField(_("o que aconteceu"), blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("registrado por"),
    )

    class Meta:
        verbose_name = _("interação")
        verbose_name_plural = _("histórico")
        ordering = ["-happened_at", "-id"]

    def __str__(self):
        return f"{self.get_kind_display()} – {self.client}"


class FollowUp(models.Model):
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="followups", verbose_name=_("cliente")
    )
    broker = models.ForeignKey(
        "people.Broker",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="followups",
        verbose_name=_("corretor"),
    )
    due_date = models.DateField(_("retornar em"), default=timezone.localdate)
    note = models.CharField(_("o que fazer"), max_length=200, blank=True)
    done = models.BooleanField(_("feito"), default=False)
    done_at = models.DateTimeField(_("feito em"), null=True, blank=True)

    class Meta:
        verbose_name = _("retorno")
        verbose_name_plural = _("retornos")
        ordering = ["done", "due_date", "id"]

    def __str__(self):
        return f"{self.client} – {self.due_date:%d/%m/%Y}"

    def save(self, *args, **kwargs):
        if self.done and not self.done_at:
            self.done_at = timezone.now()
        elif not self.done:
            self.done_at = None
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        return not self.done and self.due_date < timezone.localdate()


class DocumentTemplate(models.Model):
    """Modelo de documento em texto simples com variáveis (ver `apps/crm/documents.py`)."""

    class Kind(models.TextChoices):
        VISIT = "VISIT", _("Termo de visita")
        PROPOSAL = "PROPOSAL", _("Proposta")
        RENTAL = "RENTAL", _("Contrato de locação")
        BROKERAGE = "BROKERAGE", _("Contrato de intermediação")
        RECEIPT = "RECEIPT", _("Recibo")

    name = models.CharField(_("nome"), max_length=120)
    kind = models.CharField(_("tipo"), max_length=10, choices=Kind)
    description = models.CharField(_("observação interna"), max_length=200, blank=True)
    body = models.TextField(
        _("texto do modelo"),
        help_text=_(
            "Texto simples. Variáveis: {{ cliente.nome }}, {{ cliente.whatsapp }}, "
            "{{ imovel.codigo }}, {{ imovel.titulo }}, {{ imovel.endereco }}, {{ imovel.valor }}, "
            "{{ imovel.valor_extenso }}, {{ imobiliaria.nome }}, {{ imobiliaria.creci }}, "
            "{{ corretor.nome }}, {{ data }}, {{ data_extenso }}. "
            "Linha começando com # vira título."
        ),
    )
    is_active = models.BooleanField(_("ativo"), default=True)
    updated_at = models.DateTimeField(_("alterado em"), auto_now=True)

    class Meta:
        verbose_name = _("modelo de documento")
        verbose_name_plural = _("modelos de documento")
        ordering = ["kind", "name"]

    def __str__(self):
        return self.name

    def clean(self):
        from .documents import DocumentError, validate_body

        try:
            validate_body(self.body)
        except DocumentError as exc:
            raise ValidationError({"body": str(exc)}) from exc


class GeneratedDocument(models.Model):
    """Histórico: o texto final no momento em que foi gerado (não muda se o modelo mudar)."""

    template = models.ForeignKey(
        DocumentTemplate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
        verbose_name=_("modelo"),
    )
    title = models.CharField(_("documento"), max_length=120)
    client = models.ForeignKey(
        Client,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
        verbose_name=_("cliente"),
    )
    property = models.ForeignKey(
        "properties.Property",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
        verbose_name=_("imóvel"),
    )
    html = models.TextField(_("conteúdo"))
    original_html = models.TextField(
        _("texto original"),
        blank=True,
        editable=False,
        help_text=_("Guardado na primeira edição, para restaurar."),
    )
    edited_at = models.DateTimeField(_("editado em"), null=True, blank=True, editable=False)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("gerado por"),
    )
    created_at = models.DateTimeField(_("gerado em"), auto_now_add=True)

    class Meta:
        verbose_name = _("documento gerado")
        verbose_name_plural = _("documentos gerados")
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.title} – {self.created_at:%d/%m/%Y}"
