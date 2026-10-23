"""Favoritos do visitante, guardados num cookie (sem login)."""

import re

COOKIE = "favs"
MAX_ITEMS = 50
MAX_AGE = 365 * 24 * 60 * 60
_CODE = re.compile(r"^[A-Za-z0-9-]{1,20}$")


def read(request):
    """Códigos salvos, na ordem em que foram favoritados (sem repetidos nem lixo)."""
    codes = []
    for code in request.COOKIES.get(COOKIE, "").split(","):
        code = code.strip().upper()
        if _CODE.match(code) and code not in codes:
            codes.append(code)
    return codes[-MAX_ITEMS:]


def write(response, codes):
    if codes:
        response.set_cookie(
            COOKIE,
            ",".join(codes[-MAX_ITEMS:]),
            max_age=MAX_AGE,
            samesite="Lax",
            httponly=True,
        )
    else:
        response.delete_cookie(COOKIE, samesite="Lax")
    return response
