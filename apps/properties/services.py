"""Escrita de imóveis fora do painel (API; depois a importação em lote): upsert e fotos."""

import ipaddress
import socket
import urllib.error
import urllib.request
from io import BytesIO
from urllib.parse import urljoin, urlparse

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Max
from PIL import Image

from . import duplicates, history
from .models import Category, City, Feature, Neighborhood, Property, PropertyPhoto

MAX_PHOTO_BYTES = 10 * 1024 * 1024
FETCH_TIMEOUT = 10
MAX_REDIRECTS = 3
IMAGE_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}

DIRECT_FIELDS = (
    "external_ref",
    "title",
    "description",
    "purpose",
    "status",
    "street",
    "number",
    "complement",
    "zip_code",
    "show_address",
    "sale_price",
    "rent_price",
    "condo_fee",
    "iptu",
    "bedrooms",
    "suites",
    "bathrooms",
    "parking_spaces",
    "area_total",
    "area_built",
)


# ---------- relações ----------


def resolve_category(value):
    """Categoria pelo nome ou pelo prefixo do código (ex.: "Casa" ou "CA")."""
    value = (value or "").strip()
    category = (
        Category.objects.filter(name__iexact=value).first()
        or Category.objects.filter(code_prefix__iexact=value).first()
    )
    if category is None:
        raise ValidationError({"category": f"Categoria não encontrada: {value!r}."})
    return category


def resolve_neighborhood(city_name, state, name, fallback=None):
    """Bairro (e cidade) pelo nome; cria o que faltar. `fallback` é a cidade atual do imóvel."""
    errors = {}
    city = None
    if city_name:
        qs = City.objects.filter(name__iexact=city_name.strip())
        if state:
            qs = qs.filter(state__iexact=state.strip())
        city = qs.first()
        if city is None:
            if state:
                city = City(name=city_name.strip(), state=state.strip().upper())
            else:
                errors["state"] = "Informe a UF para cadastrar uma cidade nova."
    elif fallback is not None:
        city = fallback
    else:
        errors["city"] = "Informe a cidade."
    if not name:
        errors["neighborhood"] = "Informe o bairro."
    if errors:
        raise ValidationError(errors)
    if city.pk is None:
        city.save()
    neighborhood = Neighborhood.objects.filter(city=city, name__iexact=name.strip()).first()
    return neighborhood or Neighborhood.objects.create(city=city, name=name.strip())


def resolve_features(names):
    found = []
    for name in dict.fromkeys(n.strip() for n in names if n and n.strip()):
        found.append(
            Feature.objects.filter(name__iexact=name).first() or Feature.objects.create(name=name)
        )
    return found


# ---------- imóvel ----------


def upsert_property(data, *, instance=None, source="API"):
    """Cria ou atualiza um imóvel. Devolve (imóvel, criado, [(parecido, nível)]).

    Sem `instance`, casa por `external_ref`. Levanta ValidationError com erros por campo.
    Grava o histórico e atualiza o aviso de duplicado (que não bloqueia).
    """
    data = dict(data)
    if instance is None and data.get("external_ref"):
        instance = Property.objects.filter(external_ref=data["external_ref"]).first()
    created = instance is None
    prop = Property() if created else instance
    before = None if created else history.snapshot(prop)

    if "category" in data:
        prop.category = resolve_category(data["category"])
    if created or {"city", "neighborhood"} & data.keys():
        if not created and "neighborhood" not in data:
            raise ValidationError({"neighborhood": "Informe também o bairro ao trocar a cidade."})
        prop.neighborhood = resolve_neighborhood(
            data.get("city"),
            data.get("state"),
            data.get("neighborhood"),
            fallback=None if created or data.get("city") else prop.neighborhood.city,
        )
    for name in DIRECT_FIELDS:
        if name in data:
            setattr(prop, name, data[name])
    if created and "status" not in data:
        prop.status = Property.Status.DRAFT

    prop.full_clean(exclude=["code", "slug"], validate_unique=True)
    with transaction.atomic():
        prop.save()
        if "features" in data:
            prop.features.set(resolve_features(data["features"]))
        if created:
            history.record_created(prop, None, source)
        else:
            history.record_changes(prop, before, history.snapshot(prop), None, source)
    return prop, created, duplicates.refresh_hints(prop)


# ---------- fotos ----------


def _check_public_host(url, field="url"):
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValidationError({field: "Use um endereço http:// ou https://."})
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(parts.hostname, port)
    except OSError as exc:
        raise ValidationError({field: "Não foi possível resolver o endereço."}) from exc
    for info in infos:
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise ValidationError({field: "Endereço não permitido."})


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch_bytes(url, max_bytes=MAX_PHOTO_BYTES, field="url", timeout=FETCH_TIMEOUT):
    """Baixa um arquivo (http/https, IP público, 3 redirecionamentos, limite de bytes e tempo)."""
    too_big = {field: f"Arquivo maior que {max_bytes // (1024 * 1024)} MB."}
    opener = urllib.request.build_opener(_NoRedirect)
    for _hop in range(MAX_REDIRECTS + 1):
        _check_public_host(url, field)
        request = urllib.request.Request(url, headers={"User-Agent": "imob-site/1.0"})
        try:
            response = opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            location = exc.headers.get("Location") if exc.headers else None
            if exc.code in (301, 302, 303, 307, 308) and location:
                url = urljoin(url, location)
                continue
            raise ValidationError({field: f"O servidor respondeu {exc.code}."}) from exc
        except (urllib.error.URLError, OSError) as exc:
            raise ValidationError({field: "Não foi possível baixar o arquivo."}) from exc
        with response:
            if int(response.headers.get("Content-Length") or 0) > max_bytes:
                raise ValidationError(too_big)
            data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValidationError(too_big)
        return data
    raise ValidationError({field: "Redirecionamentos demais."})


def fetch_image_bytes(url):
    return fetch_bytes(url, MAX_PHOTO_BYTES, "url")


def _validated_image(data, field):
    if len(data) > MAX_PHOTO_BYTES:
        raise ValidationError({field: "Imagem maior que 10 MB."})
    try:
        image = Image.open(BytesIO(data))
        image.verify()
        fmt = image.format
    except Exception as exc:  # noqa: BLE001 - qualquer falha do Pillow = arquivo inválido
        raise ValidationError({field: "O arquivo não é uma imagem válida."}) from exc
    if fmt not in IMAGE_FORMATS:
        raise ValidationError({field: "Formato não aceito (use JPEG, PNG, WEBP ou GIF)."})
    return ContentFile(data, name=f"api-photo.{IMAGE_FORMATS[fmt]}")


def add_photo(prop, *, upload=None, url=None, caption="", source="API", record=True):
    """Adiciona uma foto (arquivo enviado ou URL) ao fim da lista; a primeira vira capa.

    `record=False` pula o histórico (quem importa várias fotos grava uma linha só).
    """
    if bool(upload) == bool(url):
        raise ValidationError({"photo": "Envie um arquivo (`file`) ou uma `url`, não os dois."})
    if upload is not None:
        content = _validated_image(upload.read(MAX_PHOTO_BYTES + 1), "file")
    else:
        content = _validated_image(fetch_image_bytes(url), "url")
    before = history.snapshot(prop)
    last = prop.photos.aggregate(m=Max("order"))["m"]
    photo = PropertyPhoto.objects.create(
        property=prop,
        image=content,
        caption=caption[:150],
        order=0 if last is None else last + 1,
        is_cover=not prop.photos.filter(is_cover=True).exists(),
    )
    if record:
        history.record_changes(prop, before, history.snapshot(prop), None, source)
    return photo


def remove_photo(prop, photo, *, source="API"):
    before = history.snapshot(prop)
    was_cover = photo.is_cover
    photo.delete()
    if was_cover:
        first = prop.photos.first()
        if first:
            first.is_cover = True
            first.save()
    history.record_changes(prop, before, history.snapshot(prop), None, source)
