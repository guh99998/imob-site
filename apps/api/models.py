import hashlib
import hmac
import secrets

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.crm.models import Client

KEY_PREFIX_LENGTH = 12


def hash_key(raw):
    """SHA-256 basta: a chave tem 256 bits de entropia (não é senha escolhida por gente)."""
    return hashlib.sha256(raw.encode()).hexdigest()


class ApiKey(models.Model):
    class Permission(models.TextChoices):
        LEADS = "LEADS", _("Só enviar contatos")
        FULL = "FULL", _("Contatos, clientes e imóveis")

    name = models.CharField(
        _("integração"), max_length=100, help_text=_("Ex.: Portal X, Landing page, Zapier.")
    )
    prefix = models.CharField(
        _("prefixo"), max_length=KEY_PREFIX_LENGTH, unique=True, editable=False
    )
    key_hash = models.CharField(max_length=64, editable=False)
    permission = models.CharField(
        _("permissão"), max_length=5, choices=Permission, default=Permission.LEADS
    )
    source = models.CharField(
        _("origem dos clientes"),
        max_length=10,
        choices=Client.Source,
        default=Client.Source.API,
        help_text=_("Como os clientes enviados por esta chave aparecem no CRM."),
    )
    is_active = models.BooleanField(_("ativa"), default=True)
    last_used_at = models.DateTimeField(_("último uso"), null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(_("criada em"), auto_now_add=True)

    class Meta:
        verbose_name = _("chave de API")
        verbose_name_plural = _("chaves de API")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.prefix}…)"

    @classmethod
    def create_with_key(cls, **fields):
        """Cria a chave e devolve (objeto, chave em texto). O texto não é guardado."""
        while True:
            raw = "imob_" + secrets.token_urlsafe(32)
            if not cls.objects.filter(prefix=raw[:KEY_PREFIX_LENGTH]).exists():
                break
        obj = cls.objects.create(prefix=raw[:KEY_PREFIX_LENGTH], key_hash=hash_key(raw), **fields)
        return obj, raw

    @classmethod
    def lookup(cls, raw):
        """Chave ativa que corresponde ao texto recebido, ou None."""
        candidate = cls.objects.filter(prefix=raw[:KEY_PREFIX_LENGTH], is_active=True).first()
        if candidate and hmac.compare_digest(candidate.key_hash, hash_key(raw)):
            return candidate
        return None
