import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def normalize_phone(text):
    """Só dígitos, sem o 55 do país. Número que não parece telefone vira "" (não casa)."""
    digits = re.sub(r"\D", "", text or "")
    if digits.startswith("55") and len(digits) in (12, 13):
        digits = digits[2:]
    return digits if len(digits) in (10, 11) else ""


class Client(models.Model):
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
