"""Valor por extenso em reais (pt-BR)."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

UNITS = [
    "zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez",
    "onze", "doze", "treze", "quatorze", "quinze", "dezesseis", "dezessete", "dezoito",
    "dezenove",
]  # fmt: skip
TENS = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta"]
TENS += ["noventa"]
HUNDREDS = [
    "", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos",
    "setecentos", "oitocentos", "novecentos",
]  # fmt: skip
SCALES = [
    (10**12, "trilhão", "trilhões"),
    (10**9, "bilhão", "bilhões"),
    (10**6, "milhão", "milhões"),
    (1000, "mil", "mil"),
]


def _below_1000(n):
    if n == 100:
        return "cem"
    hundreds, rest = divmod(n, 100)
    parts = [HUNDREDS[hundreds]] if hundreds else []
    if rest:
        if rest < 20:
            parts.append(UNITS[rest])
        else:
            tens, unit = divmod(rest, 10)
            parts.append(TENS[tens] + (f" e {UNITS[unit]}" if unit else ""))
    return " e ".join(parts)


def cardinal(n):
    """Número inteiro >= 0 por extenso ("mil e quinhentos", "um milhão e duzentos mil")."""
    if n == 0:
        return "zero"
    groups = []  # [(valor do grupo, texto)] do maior para o menor
    for size, singular, plural in SCALES:
        value, n = divmod(n, size)
        if value:
            if size == 1000 and value == 1:
                groups.append((value, "mil"))
            else:
                groups.append((value, f"{_below_1000(value)} {singular if value == 1 else plural}"))
    if n:
        groups.append((n, _below_1000(n)))
    text = groups[0][1]
    for index, (value, words) in enumerate(groups[1:], start=1):
        last = index == len(groups) - 1
        text += (" e " if last and (value < 100 or value % 100 == 0) else " ") + words
    return text


def reais(value):
    """Valor em reais por extenso. Vazio quando não é um número."""
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return ""
    if amount < 0:
        return ""
    whole, cents = divmod(int(amount * 100), 100)
    parts = []
    if whole or not cents:
        unit = "real" if whole == 1 else "reais"
        if whole >= 10**6 and whole % 10**6 == 0:
            unit = "de reais"
        parts.append(f"{cardinal(whole)} {unit}")
    if cents:
        parts.append(f"{cardinal(cents)} {'centavo' if cents == 1 else 'centavos'}")
    return " e ".join(parts)
