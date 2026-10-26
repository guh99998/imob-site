from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.crm.models import Client
from apps.crm.services import register_lead
from apps.leads.models import Lead
from apps.leads.services import notify_lead
from apps.properties import services
from apps.properties.filters import PropertyFilter
from apps.properties.models import Property

from .permissions import ApiEnabled, FullAccess, HasApiKey
from .serializers import (
    ClientSerializer,
    InteractionSerializer,
    LeadInSerializer,
    LeadOutSerializer,
    PhotoInSerializer,
    PhotoOutSerializer,
    PropertySerializer,
    PropertyWriteResultSerializer,
    PropertyWriteSerializer,
)

BASE = [ApiEnabled, HasApiKey]
FULL = [ApiEnabled, HasApiKey, FullAccess]


class LeadCreateView(APIView):
    permission_classes = BASE

    @extend_schema(
        request=LeadInSerializer,
        responses={201: LeadOutSerializer},
        summary="Enviar um contato",
        description=(
            "Cria o contato na caixa de entrada do painel e o cliente no CRM. Se já existe um "
            "cliente com o mesmo WhatsApp ou email, ele é reaproveitado."
        ),
    )
    def post(self, request):
        ser = LeadInSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        lead = Lead.objects.create(
            kind=data["kind"],
            property=data["property"],
            name=data["name"],
            email=data["email"],
            phone=data["phone"],
            message=data["message"],
        )
        source = Client.Source.LISTING if lead.kind == Lead.Kind.LISTING else request.auth.source
        client = register_lead(lead, source=source)
        notify_lead(lead)
        return Response(
            {"id": lead.pk, "client": client.pk if client else None},
            status=status.HTTP_201_CREATED,
        )


def _clients():
    return Client.objects.filter(anonymized_at__isnull=True).select_related("broker")


@extend_schema(
    parameters=[
        OpenApiParameter("stage", enum=Client.Stage.values, description="Etapa do funil."),
        OpenApiParameter("source", enum=Client.Source.values, description="Origem."),
        OpenApiParameter("q", description="Busca por nome, WhatsApp ou email."),
    ],
    summary="Listar clientes",
)
class ClientListView(ListAPIView):
    permission_classes = FULL
    serializer_class = ClientSerializer

    def get_queryset(self):
        qs = _clients()
        params = self.request.query_params
        if params.get("stage") in Client.Stage.values:
            qs = qs.filter(stage=params["stage"])
        if params.get("source") in Client.Source.values:
            qs = qs.filter(source=params["source"])
        q = params.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(whatsapp__icontains=q) | Q(email__icontains=q))
        return qs.order_by("-updated_at", "-id")


@extend_schema(summary="Ver ou atualizar um cliente")
class ClientDetailView(RetrieveUpdateAPIView):
    permission_classes = FULL
    serializer_class = ClientSerializer
    queryset = _clients()
    http_method_names = ["get", "patch", "head", "options"]


class InteractionListCreateView(ListCreateAPIView):
    permission_classes = FULL
    serializer_class = InteractionSerializer

    def _client(self):
        return get_object_or_404(_clients(), pk=self.kwargs["pk"])

    def get_queryset(self):
        return self._client().interactions.select_related("property")

    def perform_create(self, serializer):
        serializer.save(client=self._client())

    @extend_schema(summary="Histórico do cliente")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(summary="Registrar uma interação (ligação, visita, anotação…)")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


def _properties():
    return (
        Property.objects.published()
        .select_related("category", "neighborhood__city")
        .prefetch_related("photos", "features")
    )


def _source(request):
    return f"API: {request.auth.name}"


def _service_errors(exc):
    """ValidationError do Django (serviços) -> 400 do DRF com erros por campo."""
    return ValidationError(exc.message_dict if hasattr(exc, "error_dict") else exc.messages)


def _properties_all():
    return Property.objects.select_related("category", "neighborhood__city").prefetch_related(
        "photos", "features"
    )


def _write_response(request, prop, created, matches):
    prop = _properties_all().get(pk=prop.pk)
    data = dict(PropertySerializer(prop, context={"request": request}).data)
    data["created"] = created
    data["possible_duplicates"] = [
        {"code": other.code, "title": other.title, "match": level} for other, level in matches
    ]
    return Response(data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@extend_schema(
    summary="Listar imóveis publicados",
    description="Aceita os mesmos filtros da busca do site (`purpose`, `category`, `city`, "
    "`neighborhood`, `min_price`, `max_price`, `bedrooms`, `parking_spaces`, `min_area`, "
    "`max_area`, `order`).",
)
class PropertyListView(ListAPIView):
    permission_classes = BASE
    serializer_class = PropertySerializer

    def get_permissions(self):
        return [p() for p in (FULL if self.request.method == "POST" else BASE)]

    def get_queryset(self):
        return PropertyFilter(self.request.query_params, queryset=_properties()).qs

    @extend_schema(
        request=PropertyWriteSerializer,
        responses={201: PropertyWriteResultSerializer, 200: PropertyWriteResultSerializer},
        summary="Cadastrar um imóvel (ou atualizar por `external_ref`)",
        description=(
            "Exige chave com permissão total. Entra como rascunho, a menos que `status` seja "
            "enviado. Com `external_ref` já existente, atualiza esse imóvel (200). "
            "`possible_duplicates` avisa de imóveis parecidos, sem bloquear."
        ),
    )
    def post(self, request):
        ser = PropertyWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            prop, created, matches = services.upsert_property(
                ser.validated_data, source=_source(request)
            )
        except DjangoValidationError as exc:
            raise _service_errors(exc) from exc
        return _write_response(request, prop, created, matches)


@extend_schema(summary="Ver um imóvel pelo código")
class PropertyDetailView(RetrieveAPIView):
    permission_classes = BASE
    serializer_class = PropertySerializer
    queryset = _properties()
    lookup_field = "code__iexact"
    lookup_url_kwarg = "code"

    def get_permissions(self):
        return [p() for p in (FULL if self.request.method == "PATCH" else BASE)]

    @extend_schema(
        request=PropertyWriteSerializer(partial=True),
        responses={200: PropertyWriteResultSerializer},
        summary="Atualizar um imóvel (campos enviados)",
    )
    def patch(self, request, code):
        prop = get_object_or_404(Property, code__iexact=code)
        ser = PropertyWriteSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        try:
            prop, created, matches = services.upsert_property(
                ser.validated_data, instance=prop, source=_source(request)
            )
        except DjangoValidationError as exc:
            raise _service_errors(exc) from exc
        return _write_response(request, prop, created, matches)


class PropertyPhotoCreateView(APIView):
    permission_classes = FULL
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        request=PhotoInSerializer,
        responses={201: PhotoOutSerializer},
        summary="Adicionar uma foto (arquivo ou URL)",
        description=(
            "Envie `file` (multipart) ou `url` (JSON). Até 10 MB; JPEG, PNG, WEBP ou GIF. "
            "A URL precisa ser pública (endereços internos são recusados). A primeira foto "
            "vira a capa."
        ),
    )
    def post(self, request, code):
        prop = get_object_or_404(Property, code__iexact=code)
        ser = PhotoInSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            photo = services.add_photo(
                prop,
                upload=ser.validated_data.get("file"),
                url=ser.validated_data.get("url"),
                caption=ser.validated_data["caption"],
                source=_source(request),
            )
        except DjangoValidationError as exc:
            raise _service_errors(exc) from exc
        body = {
            "id": photo.pk,
            "url": request.build_absolute_uri(photo.src_lg),
            "is_cover": photo.is_cover,
        }
        return Response(body, status=status.HTTP_201_CREATED)


class PropertyPhotoDeleteView(APIView):
    permission_classes = FULL

    @extend_schema(responses={204: None}, summary="Remover uma foto")
    def delete(self, request, code, photo_id):
        prop = get_object_or_404(Property, code__iexact=code)
        photo = get_object_or_404(prop.photos, pk=photo_id)
        services.remove_photo(prop, photo, source=_source(request))
        return Response(status=status.HTTP_204_NO_CONTENT)


# A documentação some junto com o módulo (404) e não usa autenticação.
class ApiSchemaView(SpectacularAPIView):
    permission_classes = [ApiEnabled]
    authentication_classes = []


class ApiDocsView(SpectacularSwaggerView):
    permission_classes = [ApiEnabled]
    authentication_classes = []
