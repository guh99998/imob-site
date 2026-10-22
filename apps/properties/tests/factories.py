import factory

from apps.properties.models import Category, City, Feature, Neighborhood, Property


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Categoria {n}")


class CityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = City

    name = factory.Sequence(lambda n: f"Cidade {n}")
    state = "SP"
    slug = factory.Sequence(lambda n: f"cidade-{n}")


class NeighborhoodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Neighborhood

    city = factory.SubFactory(CityFactory)
    name = factory.Sequence(lambda n: f"Bairro {n}")
    slug = factory.Sequence(lambda n: f"bairro-{n}")


class FeatureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Feature

    name = factory.Sequence(lambda n: f"Comodidade {n}")


class PropertyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Property

    code = factory.Sequence(lambda n: f"IM{n:04d}")
    title = factory.Sequence(lambda n: f"Imóvel {n}")
    slug = factory.Sequence(lambda n: f"imovel-{n}")
    category = factory.SubFactory(CategoryFactory)
    neighborhood = factory.SubFactory(NeighborhoodFactory)
    purpose = Property.Purpose.SALE
    sale_price = 500000
    status = Property.Status.PUBLISHED
    bedrooms = 2
