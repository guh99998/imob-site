"""Popula o site com conteúdo de exemplo (fotos do Pexels em demo/photos). Idempotente."""

from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.core.models import SiteSettings
from apps.properties.models import Category, City, Feature, Neighborhood, Property, PropertyPhoto

PHOTOS_DIR = Path(settings.BASE_DIR) / "demo" / "photos"

CATEGORIES = ["Apartamento", "Casa", "Cobertura", "Terreno", "Comercial"]
FEATURES = [
    "Piscina",
    "Churrasqueira",
    "Varanda gourmet",
    "Ar-condicionado",
    "Armários planejados",
    "Quintal",
    "Portaria 24h",
    "Academia",
    "Elevador",
    "Aceita pets",
]
CITIES = {
    ("Vila Serena", "SP"): ["Jardim das Acácias", "Alto da Colina", "Centro Antigo", "Lagoa Azul"],
    ("Porto Claro", "SC"): ["Praia do Sol", "Morro Verde", "Beira-Rio", "Vila Nova"],
}

S, R, B = Property.Purpose.SALE, Property.Purpose.RENT, Property.Purpose.BOTH

# code, title, category, city, neighborhood, purpose, sale, rent, beds, suites, baths, park, m²,
# featured, status, fotos, descrição
PROPERTIES = [
    ("01", "Casa de esquina com varanda para o jardim", "Casa", "Vila Serena", "Jardim das Acácias",
     S, 980000, None, 4, 2, 4, 3, 320, True, "PUBLISHED",
     ["106399", "1080721", "1571460", "3754594", "3315291"],
     "Casa ampla em rua tranquila, com cozinha integrada à sala e jardim nos fundos."),
    ("02", "Sobrado com garagem para três carros", "Casa", "Vila Serena", "Alto da Colina",
     S, 1250000, None, 5, 3, 5, 3, 410, True, "PUBLISHED",
     ["1396122", "2635038", "1571463", "4857775"],
     "Sobrado de esquina com suíte máster, escritório e área de lazer completa."),
    ("03", "Casa com varanda e vista para o canal", "Casa", "Porto Claro", "Beira-Rio",
     B, 870000, 5200, 3, 1, 3, 2, 210, True, "PUBLISHED",
     ["1438832", "2724749", "1457842"],
     "Casa em condomínio fechado, a poucos passos do canal. Pode ser comprada ou alugada."),
    ("04", "Casa térrea com amplo gramado", "Casa", "Porto Claro", "Morro Verde",
     S, 1490000, None, 4, 2, 4, 4, 520, False, "PUBLISHED",
     ["259588", "534151", "1643383", "3935350"],
     "Terreno de esquina com gramado e casa térrea bem iluminada."),
    ("05", "Casa de vila para alugar perto do centro", "Casa", "Vila Serena", "Centro Antigo",
     R, None, 3800, 2, 0, 2, 1, 95, False, "PUBLISHED",
     ["1029599", "4846097", "462235"],
     "Casa charmosa de vila, com quintal e entrada independente."),
    ("06", "Casa moderna com piscina", "Casa", "Porto Claro", "Praia do Sol",
     S, 2100000, None, 4, 4, 5, 4, 380, True, "PUBLISHED",
     ["280229", "5997967", "1918291"],
     "Casa contemporânea, térrea, com piscina aquecida e espaço gourmet."),
    ("07", "Apartamento de dois quartos com varanda", "Apartamento", "Vila Serena", "Lagoa Azul",
     R, None, 3200, 2, 1, 2, 1, 78, False, "PUBLISHED",
     ["323780", "3797991", "2121120"],
     "Apartamento em prédio novo, com varanda e armários planejados."),
    ("08", "Apartamento claro no centro", "Apartamento", "Vila Serena", "Centro Antigo",
     S, 540000, None, 2, 0, 2, 1, 68, False, "PUBLISHED",
     ["1115804", "2343468", "276724"],
     "Apartamento de frente, andar alto, a duas quadras do comércio."),
    ("09", "Apartamento em condomínio com lazer completo", "Apartamento", "Porto Claro",
     "Vila Nova", B, 720000, 4500, 3, 1, 2, 2, 105, False, "PUBLISHED",
     ["1475938", "2251247"],
     "Condomínio com academia, piscina e salão de festas."),
    ("10", "Cobertura duplex com terraço", "Cobertura", "Porto Claro", "Praia do Sol",
     S, 1890000, None, 3, 3, 4, 3, 240, False, "PUBLISHED",
     ["7031406", "2102587"],
     "Cobertura com terraço privativo e vista aberta."),
    ("11", "Terreno com vista para o morro", "Terreno", "Porto Claro", "Morro Verde",
     S, 310000, None, 0, 0, 0, 0, 600, False, "PUBLISHED",
     ["2581922"],
     "Terreno plano, escriturado, pronto para construir."),
    ("12", "Sala comercial no centro, já vendida", "Comercial", "Vila Serena", "Centro Antigo",
     S, 450000, None, 0, 0, 1, 1, 60, False, "SOLD",
     ["2251247", "2343468"],
     "Sala comercial com recepção e duas salas de atendimento."),
]  # fmt: skip


class Command(BaseCommand):
    help = "Cria dados de exemplo (DevLopesMóveis). Use --reset para recriar os imóveis de exemplo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true", help="Apaga os imóveis de exemplo antes de recriar."
        )

    def handle(self, *args, **options):
        if options["reset"]:
            titles = [row[1] for row in PROPERTIES]
            n, _ = Property.objects.filter(title__in=titles).delete()
            self.stdout.write(f"{n} registro(s) de exemplo removido(s).")

        site = SiteSettings.load()
        if site.name in ("Imobiliária", ""):
            site.name = "DevLopesMóveis"
            site.phone = site.phone or "(11) 4000-1234"
            site.email = site.email or "contato@devlopesmoveis.example"
            site.address = site.address or "Rua das Palmeiras, 120 — Vila Serena/SP"
            site.creci = site.creci or "00000-J"
            site.cnpj = site.cnpj or "11.222.333/0001-81"
            site.about = (
                site.about or "Imobiliária de exemplo: casas e apartamentos com fotos de verdade."
            )
        # Número fictício óbvio; substitui o antigo número de exemplo.
        if site.whatsapp in ("", "5511940001234"):
            site.whatsapp = "5511900000000"
        site.save()

        categories = {
            name: Category.objects.get_or_create(name=name, defaults={"order": i})[0]
            for i, name in enumerate(CATEGORIES, start=1)
        }
        features = [Feature.objects.get_or_create(name=n)[0] for n in FEATURES]
        neighborhoods = {}
        for (city_name, uf), names in CITIES.items():
            city, _ = City.objects.get_or_create(name=city_name, state=uf)
            for name in names:
                neighborhoods[name] = Neighborhood.objects.get_or_create(city=city, name=name)[0]

        created = 0
        for i, row in enumerate(PROPERTIES):
            (num, title, cat, _city, nb, purpose, sale, rent, beds, suites, baths, park, area,
             featured, status, photos, description) = row  # fmt: skip
            if Property.objects.filter(title=title).exists():
                continue
            prop = Property.objects.create(
                title=title,
                description=description,
                category=categories[cat],
                neighborhood=neighborhoods[nb],
                purpose=purpose,
                status=status,
                sale_price=Decimal(sale) if sale else None,
                rent_price=Decimal(rent) if rent else None,
                condo_fee=Decimal(650 + i * 40) if cat in ("Apartamento", "Cobertura") else None,
                bedrooms=beds,
                suites=suites,
                bathrooms=baths,
                parking_spaces=park,
                area_total=Decimal(area),
                is_featured=featured,
            )
            prop.features.set(features[i % 3 :: 2][:5])
            for order, pid in enumerate(photos):
                path = PHOTOS_DIR / f"p{pid}.jpg"
                if not path.exists():
                    self.stderr.write(f"Foto ausente: {path}")
                    continue
                PropertyPhoto.objects.create(
                    property=prop,
                    image=ContentFile(path.read_bytes(), name=f"demo-{num}-{pid}.jpg"),
                    order=order,
                    is_cover=order == 0,
                    caption=title if order == 0 else "",
                )
            created += 1
        self.stdout.write(self.style.SUCCESS(f"Pronto: {created} imóvel(is) criado(s)."))
