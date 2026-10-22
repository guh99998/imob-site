from django.db import models
from django.utils.translation import gettext_lazy as _


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
