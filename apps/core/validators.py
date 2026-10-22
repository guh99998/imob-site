"""Validadores de documentos brasileiros (dígitos verificadores)."""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def digits(value):
    return re.sub(r"\D", "", value or "")


def _check_digit(numbers, weights):
    total = sum(int(n) * w for n, w in zip(numbers, weights, strict=False))
    rest = total % 11
    return "0" if rest < 2 else str(11 - rest)


def is_valid_cpf(value):
    d = digits(value)
    if len(d) != 11 or len(set(d)) == 1:
        return False
    d1 = _check_digit(d[:9], range(10, 1, -1))
    d2 = _check_digit(d[:9] + d1, range(11, 1, -1))
    return d[9:] == d1 + d2


def is_valid_cnpj(value):
    d = digits(value)
    if len(d) != 14 or len(set(d)) == 1:
        return False
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    d1 = _check_digit(d[:12], w1)
    d2 = _check_digit(d[:12] + d1, [6, *w1])
    return d[12:] == d1 + d2


def validate_cpf(value):
    if value and not is_valid_cpf(value):
        raise ValidationError(_("CPF inválido."))


def validate_cnpj(value):
    if value and not is_valid_cnpj(value):
        raise ValidationError(_("CNPJ inválido."))


def validate_cpf_or_cnpj(value):
    if value and not (is_valid_cpf(value) or is_valid_cnpj(value)):
        raise ValidationError(_("Informe um CPF ou CNPJ válido."))
