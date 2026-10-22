from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.validators import validate_cpf_or_cnpj


class Person(models.Model):
    """Base abstrata: contatos comuns. Cadastros internos, nunca públicos."""

    name = models.CharField(_("nome"), max_length=150)
    phone = models.CharField(_("telefone"), max_length=30, blank=True)
    email = models.EmailField(_("email"), blank=True)
    notes = models.TextField(_("observações"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return self.name


class Broker(Person):
    """Corretor da casa."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="broker",
        verbose_name=_("usuário do painel"),
        help_text=_("Liga o corretor a um login: ele passa a ver os próprios imóveis."),
    )
    creci = models.CharField(_("CRECI"), max_length=30, blank=True)
    photo = models.ImageField(_("foto"), upload_to="people/", blank=True)
    is_active = models.BooleanField(_("ativo"), default=True)

    class Meta(Person.Meta):
        verbose_name = _("corretor")
        verbose_name_plural = _("corretores")


class Partner(Person):
    """Corretor ou imobiliária parceira."""

    company = models.CharField(_("imobiliária"), max_length=150, blank=True)
    creci = models.CharField(_("CRECI"), max_length=30, blank=True)
    commission = models.CharField(
        _("comissão combinada"), max_length=100, blank=True, help_text=_("Ex.: 50% da comissão.")
    )

    class Meta(Person.Meta):
        verbose_name = _("parceiro")
        verbose_name_plural = _("parceiros")


class Owner(Person):
    """Proprietário do imóvel."""

    document = models.CharField(
        _("CPF/CNPJ"), max_length=18, blank=True, validators=[validate_cpf_or_cnpj]
    )

    class Meta(Person.Meta):
        verbose_name = _("proprietário")
        verbose_name_plural = _("proprietários")
