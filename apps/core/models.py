from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .validators import validate_cnpj

DEFAULT_WHATSAPP_MESSAGE = (
    "Olá! Tenho interesse no imóvel {codigo} – {titulo} ({bairro}), {preco}. {link}"
)


class SiteSettings(models.Model):
    """Singleton com os dados de contato da imobiliária."""

    name = models.CharField(_("nome"), max_length=120, default="Imobiliária")
    phone = models.CharField(_("telefone"), max_length=30, blank=True)
    whatsapp = models.CharField(
        _("WhatsApp"),
        max_length=20,
        blank=True,
        help_text=_("Somente dígitos, com DDI. Ex.: 5511999998888"),
    )
    email = models.EmailField(_("email"), blank=True)
    address = models.CharField(_("endereço"), max_length=255, blank=True)
    instagram = models.URLField(_("Instagram"), blank=True)
    facebook = models.URLField(_("Facebook"), blank=True)
    logo = models.ImageField(_("logo"), upload_to="site/", blank=True)
    creci = models.CharField(_("CRECI"), max_length=30, blank=True)
    cnpj = models.CharField(_("CNPJ"), max_length=18, blank=True, validators=[validate_cnpj])
    about = models.TextField(_("sobre a imobiliária"), blank=True, max_length=500)
    meta_description = models.CharField(
        _("descrição para buscadores"),
        max_length=160,
        blank=True,
        help_text=_("Resumo que aparece nos resultados do Google (até 160 caracteres)."),
    )
    whatsapp_message = models.TextField(
        _("mensagem do WhatsApp"),
        default=DEFAULT_WHATSAPP_MESSAGE,
        blank=True,
        help_text=_(
            "Texto enviado ao clicar no WhatsApp de um imóvel. Pode usar {codigo}, {titulo}, "
            "{bairro}, {preco} e {link}."
        ),
    )
    max_featured = models.PositiveSmallIntegerField(
        _("máximo de destaques"),
        default=3,
        validators=[MaxValueValidator(3)],
        help_text=_("Quantos imóveis podem ficar em destaque (a home mostra até 3)."),
    )

    class Meta:
        verbose_name = _("configurações do site")
        verbose_name_plural = _("configurações do site")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def whatsapp_digits(self):
        return "".join(c for c in self.whatsapp if c.isdigit())
