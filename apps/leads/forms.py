from django import forms

from .models import Lead

INPUT = "field"


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
