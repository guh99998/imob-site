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
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )
    categories = forms.ModelMultipleChoiceField(
        label="Tipo de imóvel",
        queryset=Category.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    city = forms.ModelChoiceField(
        label="Cidade", queryset=City.objects.all(), required=False, empty_label="Qualquer"
    )
    min_price = BRDecimalField(
        label="Preço mínimo",
        required=False,
        max_digits=12,
        decimal_places=2,
        widget=forms.TextInput(
            attrs={"class": INPUT, "placeholder": "R$ 0,00", "inputmode": "decimal"}
        ),
    )
    max_price = BRDecimalField(
        label="Preço máximo",
        required=False,
        max_digits=12,
        decimal_places=2,
        widget=forms.TextInput(
            attrs={"class": INPUT, "placeholder": "R$ 0,00", "inputmode": "decimal"}
        ),
    )
    lgpd_consent = forms.BooleanField(
        label="Concordo em ser contatado e com a política de privacidade.",
        required=True,
        error_messages={"required": "Precisamos do seu aceite para entrar em contato."},
    )

    class Meta:
        model = PropertySearch
        fields = [
            "name",
            "whatsapp",
            "email",
            "purpose",
            "categories",
            "city",
            "neighborhoods",
            "min_price",
            "max_price",
            "min_bedrooms",
            "min_parking",
            "notes",
            "lgpd_consent",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT}),
            "whatsapp": forms.TextInput(
                attrs={"class": INPUT, "data-mask": "phone", "inputmode": "numeric"}
            ),
            "email": forms.EmailInput(attrs={"class": INPUT}),
            "purpose": forms.Select(attrs={"class": INPUT}),
            "neighborhoods": forms.TextInput(
                attrs={"class": INPUT, "placeholder": "Ex.: Centro, Vila Nova"}
            ),
            "min_bedrooms": forms.NumberInput(attrs={"class": INPUT, "min": 0, "max": 20}),
            "min_parking": forms.NumberInput(attrs={"class": INPUT, "min": 0, "max": 20}),
            "notes": forms.Textarea(attrs={"class": INPUT, "rows": 3}),
        }
        labels = {"name": "Seu nome", "purpose": "Quero", "neighborhoods": "Bairros de interesse",
                  "min_bedrooms": "Quartos (mín.)", "min_parking": "Vagas (mín.)",
                  "notes": "Mais detalhes", "email": "E-mail (opcional)"}  # fmt: skip

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["city"].widget.attrs["class"] = INPUT

    def clean_website(self):
        if self.cleaned_data["website"]:
            raise forms.ValidationError("Spam detectado.")
        return ""

    def clean_whatsapp(self):
        digits = "".join(c for c in self.cleaned_data["whatsapp"] if c.isdigit())
        if len(digits) not in (10, 11):
            raise forms.ValidationError("Informe o DDD e o número (ex.: (11) 90000-0000).")
        return self.cleaned_data["whatsapp"]

    def clean(self):
        data = super().clean()
        low, high = data.get("min_price"), data.get("max_price")
        if low and high and low > high:
            self.add_error("max_price", "O preço máximo deve ser maior que o mínimo.")
        return data
