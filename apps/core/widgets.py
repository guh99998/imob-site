"""Campos e widgets com máscara (a máscara em si vive em static/core/admin/masks.js)."""

import re
from decimal import Decimal, InvalidOperation

from django import forms
from django.core.exceptions import ValidationError
from unfold.widgets import UnfoldAdminTextInputWidget

MASKS = ("money", "area", "cep", "phone", "uf", "cpf_cnpj", "creci")


class MaskedTextInput(UnfoldAdminTextInputWidget):
    def __init__(self, mask, attrs=None):
        attrs = {"data-mask": mask, "autocomplete": "off", **(attrs or {})}
        if mask in ("money", "area"):
            attrs["inputmode"] = "decimal"
        elif mask in ("cep", "phone", "cpf_cnpj"):
            attrs["inputmode"] = "numeric"
        super().__init__(attrs=attrs)

    def format_value(self, value):
        # Decimal vindo do banco: o JS formata na carga; aqui só garante vírgula decimal.
        if isinstance(value, Decimal):
            return f"{value:f}".replace(".", ",")
        return super().format_value(value)


def parse_br_decimal(value):
    """Aceita '1.234,56', 'R$ 1.234,56', '320 m²', '1234.56' e '1234,5'."""
    if value is None:
        return None
    text = re.sub(r"[^\d,.\-]", "", str(value))
    if not text:
        return None
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    elif re.fullmatch(r"-?\d{1,3}\.\d{3}", text):
        text = text.replace(".", "")  # 1.234 → mil duzentos e trinta e quatro
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValidationError("Informe um número válido.", code="invalid") from exc


class BRDecimalField(forms.DecimalField):
    """DecimalField que entende o formato brasileiro (vírgula decimal, ponto de milhar)."""

    widget = forms.TextInput

    def to_python(self, value):
        if value in self.empty_values:
            return None
        return super().to_python(str(parse_br_decimal(value)))
