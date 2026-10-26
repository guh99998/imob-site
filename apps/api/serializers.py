from rest_framework import serializers

from apps.crm.models import Client, Interaction, normalize_phone
from apps.leads.models import Lead
from apps.people.models import Broker
from apps.properties.models import Property


class LeadInSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    message = serializers.CharField(max_length=5000)
    property = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Código do imóvel (ex.: CA001), se o contato é sobre um imóvel.",
    )
    kind = serializers.ChoiceField(choices=Lead.Kind.choices, required=False)

    def validate(self, attrs):
        if not (attrs["email"] or normalize_phone(attrs["phone"])):
            raise serializers.ValidationError("Informe um email ou um telefone com DDD.")
        code = attrs.pop("property")
        attrs["property"] = None
        if code:
            prop = Property.objects.published().filter(code__iexact=code.strip()).first()
            if prop is None:
                raise serializers.ValidationError({"property": "Imóvel não encontrado."})
            attrs["property"] = prop
        attrs.setdefault("kind", Lead.Kind.PROPERTY if attrs["property"] else Lead.Kind.CONTACT)
        return attrs


class LeadOutSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    client = serializers.IntegerField(allow_null=True, help_text="Cliente criado ou reaproveitado.")


class ClientSerializer(serializers.ModelSerializer):
    broker = serializers.PrimaryKeyRelatedField(
        queryset=Broker.objects.filter(is_active=True), allow_null=True, required=False
    )

    class Meta:
        model = Client
        fields = [
            "id",
            "name",
            "whatsapp",
            "email",
            "source",
            "broker",
            "stage",
            "purpose",
            "min_price",
            "max_price",
            "tags",
            "notes",
            "lgpd_consent",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "source", "lgpd_consent", "created_at", "updated_at"]

    def validate_whatsapp(self, value):
        if not value:
            return value
        key = normalize_phone(value)
        if not key:
            raise serializers.ValidationError("Informe o DDD e o número.")
        clash = Client.objects.filter(phone_key=key)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("Este WhatsApp já pertence a outro cliente.")
        return value


class InteractionSerializer(serializers.ModelSerializer):
    property = serializers.CharField(
        required=False, allow_blank=True, default="", help_text="Código do imóvel, se houver."
    )

    class Meta:
        model = Interaction
        fields = ["id", "kind", "happened_at", "property", "text"]
        read_only_fields = ["id"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["property"] = instance.property.code if instance.property_id else ""
        return data

    def validate_property(self, value):
        if not value:
            return None
        prop = Property.objects.filter(code__iexact=value.strip()).first()
        if prop is None:
            raise serializers.ValidationError("Imóvel não encontrado.")
        return prop


class PropertySerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.name")
    neighborhood = serializers.CharField(source="neighborhood.name")
    city = serializers.CharField(source="neighborhood.city.name")
    state = serializers.CharField(source="neighborhood.city.state")
    address = serializers.CharField(source="full_address")
    url = serializers.SerializerMethodField()
    features = serializers.SerializerMethodField()
    photos = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            "code",
            "title",
            "url",
            "purpose",
            "status",
            "category",
            "neighborhood",
            "city",
            "state",
            "address",
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
            "description",
            "features",
            "photos",
            "published_at",
            "updated_at",
        ]

    def get_url(self, obj) -> str:
        return self.context["request"].build_absolute_uri(obj.get_absolute_url())

    def get_features(self, obj) -> list[str]:
        return [f.name for f in obj.features.all()]

    def get_photos(self, obj) -> list[str]:
        request = self.context["request"]
        return [request.build_absolute_uri(p.src_lg) for p in obj.photos.all()]


def _money(**kw):
    return serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True, **kw)


class PropertyWriteSerializer(serializers.Serializer):
    """Entrada de POST/PATCH de imóveis. Categoria, cidade, bairro e comodidades vão por nome."""

    external_ref = serializers.CharField(
        max_length=100,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Seu identificador do imóvel; reenviar o mesmo valor atualiza, não duplica.",
    )
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    purpose = serializers.ChoiceField(choices=Property.Purpose.choices, required=False)
    status = serializers.ChoiceField(
        choices=Property.Status.choices,
        required=False,
        help_text="Padrão ao criar: DRAFT (rascunho).",
    )
    category = serializers.CharField(help_text="Nome ou prefixo da categoria (ex.: Casa ou CA).")
    city = serializers.CharField(max_length=100, required=False)
    state = serializers.CharField(
        max_length=2, required=False, help_text="UF; só necessária para cadastrar uma cidade nova."
    )
    neighborhood = serializers.CharField(max_length=100, required=False)
    street = serializers.CharField(max_length=200, required=False, allow_blank=True)
    number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    complement = serializers.CharField(max_length=100, required=False, allow_blank=True)
    zip_code = serializers.CharField(max_length=9, required=False, allow_blank=True)
    show_address = serializers.BooleanField(required=False)
    sale_price = _money(required=False)
    rent_price = _money(required=False)
    condo_fee = _money(required=False)
    iptu = _money(required=False)
    bedrooms = serializers.IntegerField(min_value=0, max_value=255, required=False)
    suites = serializers.IntegerField(min_value=0, max_value=255, required=False)
    bathrooms = serializers.IntegerField(min_value=0, max_value=255, required=False)
    parking_spaces = serializers.IntegerField(min_value=0, max_value=255, required=False)
    area_total = serializers.DecimalField(
        max_digits=10, decimal_places=2, allow_null=True, required=False
    )
    area_built = serializers.DecimalField(
        max_digits=10, decimal_places=2, allow_null=True, required=False
    )
    features = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        help_text="Nomes das comodidades; as que não existem são criadas.",
    )

    def validate_external_ref(self, value):
        return value or None

    def validate(self, attrs):
        if not self.partial and not (attrs.get("city") and attrs.get("neighborhood")):
            raise serializers.ValidationError("Informe `city` e `neighborhood`.")
        return attrs


class PropertyWriteResultSerializer(PropertySerializer):
    created = serializers.BooleanField()
    possible_duplicates = serializers.ListField(child=serializers.DictField())

    class Meta(PropertySerializer.Meta):
        fields = [*PropertySerializer.Meta.fields, "created", "possible_duplicates"]


class PhotoInSerializer(serializers.Serializer):
    file = serializers.FileField(required=False, help_text="Imagem (multipart), até 10 MB.")
    url = serializers.URLField(required=False, help_text="Endereço http(s) público da imagem.")
    caption = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")


class PhotoOutSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    url = serializers.CharField()
    is_cover = serializers.BooleanField()
