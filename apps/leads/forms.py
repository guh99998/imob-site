from django import forms

from apps.core.widgets import BRDecimalField
from apps.properties.models import Category, City

from .models import Lead, PropertySearch

INPUT = "field"


def _price_widget():
    attrs = {"class": INPUT, "placeholder": "R$ 0,00", "inputmode": "decimal"}
    return forms.TextInput(attrs=attrs)


class LeadForm(forms.ModelForm):
    # Honeypot: humanos não preenchem; bots sim.
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )

    class Meta:
        model = Lead
        fields = ["name", "email", "phone", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT, "placeholder": "Seu nome"}),
            "email": forms.EmailInput(attrs={"class": INPUT, "placeholder": "Seu email"}),
            "phone": forms.TextInput(attrs={"class": INPUT, "placeholder": "Telefone / WhatsApp"}),
            "message": forms.Textarea(attrs={"class": INPUT, "rows": 4, "placeholder": "Mensagem"}),
        }

    def clean_website(self):
        if self.cleaned_data["website"]:
            raise forms.ValidationError("Spam detectado.")
        return ""


class PropertySearchForm(forms.ModelForm):
    """Versão enxuta: o essencial para o corretor retornar pelo WhatsApp."""

    field_order = ["name", "whatsapp", "purpose", "category", "city", "max_price", "notes"]

    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )
    category = forms.ModelChoiceField(
        label="Tipo de imóvel",
        queryset=Category.objects.all(),
        required=False,
        empty_label="Qualquer tipo",
    )
    city = forms.ModelChoiceField(
        label="Cidade", queryset=City.objects.all(), required=False, empty_label="Qualquer cidade"
    )
    max_price = BRDecimalField(
        label="Valor até",
        required=False,
        max_digits=12,
        decimal_places=2,
        widget=_price_widget(),
    )
    lgpd_consent = forms.BooleanField(
        label="Concordo em ser contatado e com a",
        required=True,
        error_messages={"required": "Precisamos do seu aceite para entrar em contato."},
    )

    class Meta:
        model = PropertySearch
        fields = ["name", "whatsapp", "purpose", "city", "max_price", "notes", "lgpd_consent"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT, "autocomplete": "name"}),
            "whatsapp": forms.TextInput(
                attrs={"class": INPUT, "data-mask": "phone", "inputmode": "numeric"}
            ),
            "purpose": forms.Select(attrs={"class": INPUT}),
            "notes": forms.Textarea(
                attrs={"class": INPUT, "rows": 3, "placeholder": "Ex.: 3 quartos, perto de escola"}
            ),
        }
        labels = {"name": "Seu nome", "purpose": "Quero", "notes": "Mensagem (opcional)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("category", "city"):
            self.fields[name].widget.attrs["class"] = INPUT
        self.fields["max_price"].widget.attrs["data-mask"] = "money"

    def clean_website(self):
        if self.cleaned_data["website"]:
            raise forms.ValidationError("Spam detectado.")
        return ""

    def clean_whatsapp(self):
        digits = "".join(c for c in self.cleaned_data["whatsapp"] if c.isdigit())
        if len(digits) not in (10, 11):
            raise forms.ValidationError("Informe o DDD e o número (ex.: (11) 90000-0000).")
        return self.cleaned_data["whatsapp"]

    def save(self, commit=True):
        search = super().save(commit=commit)
        if commit and self.cleaned_data.get("category"):
            search.categories.set([self.cleaned_data["category"]])
        return search
