from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.validators import validate_cpf, validate_cpf_or_cnpj


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


class QualifiedPerson(models.Model):
    """Qualificação para contratos: CPF, estado civil, profissão, endereço e cônjuge."""

    class MaritalStatus(models.TextChoices):
        SINGLE = "SINGLE", _("Solteiro(a)")
        MARRIED = "MARRIED", _("Casado(a)")
        STABLE_UNION = "STABLE_UNION", _("União estável")
        DIVORCED = "DIVORCED", _("Divorciado(a)")
        WIDOWED = "WIDOWED", _("Viúvo(a)")
        SEPARATED = "SEPARATED", _("Separado(a)")

    cpf = models.CharField(_("CPF"), max_length=14, blank=True, validators=[validate_cpf])
    nationality = models.CharField(
        _("nacionalidade"), max_length=60, blank=True, default="brasileiro(a)"
    )
    marital_status = models.CharField(
        _("estado civil"), max_length=12, choices=MaritalStatus, blank=True
    )
    profession = models.CharField(_("profissão"), max_length=100, blank=True)
    zip_code = models.CharField(_("CEP"), max_length=9, blank=True)
    street = models.CharField(_("rua"), max_length=200, blank=True)
    number = models.CharField(_("número"), max_length=20, blank=True)
    complement = models.CharField(_("complemento"), max_length=100, blank=True)
    neighborhood = models.CharField(_("bairro"), max_length=100, blank=True)
    city = models.CharField(_("cidade"), max_length=100, blank=True)
    state = models.CharField(_("UF"), max_length=2, blank=True)
    spouse_name = models.CharField(_("nome do cônjuge"), max_length=150, blank=True)
    spouse_cpf = models.CharField(
        _("CPF do cônjuge"), max_length=14, blank=True, validators=[validate_cpf]
    )
    spouse_nationality = models.CharField(_("nacionalidade do cônjuge"), max_length=60, blank=True)
    spouse_profession = models.CharField(_("profissão do cônjuge"), max_length=100, blank=True)

    class Meta:
        abstract = True

    @property
    def needs_spouse(self):
        return self.marital_status in (
            self.MaritalStatus.MARRIED,
            self.MaritalStatus.STABLE_UNION,
        )

    @property
    def has_spouse(self):
        return bool(self.spouse_name and self.spouse_cpf)

    @property
    def spouse_missing(self):
        return self.needs_spouse and not self.has_spouse


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


class Owner(QualifiedPerson, Person):
    """Proprietário do imóvel."""

    document = models.CharField(
        _("CPF/CNPJ"), max_length=18, blank=True, validators=[validate_cpf_or_cnpj]
    )

    class Meta(Person.Meta):
        verbose_name = _("proprietário")
        verbose_name_plural = _("proprietários")


class Guarantor(QualifiedPerson, Person):
    """Fiador de contrato de locação."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta(Person.Meta):
        verbose_name = _("fiador")
        verbose_name_plural = _("fiadores")
