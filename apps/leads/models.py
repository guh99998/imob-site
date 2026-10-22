from django.db import models
from django.utils.translation import gettext_lazy as _


class Lead(models.Model):
    class Status(models.TextChoices):
        NEW = "NEW", _("Novo")
        CONTACTED = "CONTACTED", _("Contatado")
        CLOSED = "CLOSED", _("Encerrado")

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
    created_at = models.DateTimeField(_("recebido em"), auto_now_add=True)

    class Meta:
        verbose_name = _("contato")
        verbose_name_plural = _("contatos")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.created_at:%d/%m/%Y})"
