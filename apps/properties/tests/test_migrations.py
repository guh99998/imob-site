import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_property_type_is_mapped_to_category():
    executor = MigrationExecutor(connection)
    executor.migrate([("properties", "0001_initial")])
    old = executor.loader.project_state([("properties", "0001_initial")]).apps
    City, Neighborhood, Property = (old.get_model("properties", m) for m in (
        "City", "Neighborhood", "Property"))  # fmt: skip
    city = City.objects.create(name="X", state="SP", slug="x")
    nb = Neighborhood.objects.create(city=city, name="Y", slug="y")
    Property.objects.create(code="A", title="a", slug="a", neighborhood=nb, property_type="HOUSE")
    Property.objects.create(code="B", title="b", slug="b", neighborhood=nb, property_type="LAND")

    executor = MigrationExecutor(connection)
    executor.migrate([("properties", "0004_remove_property_type")])
    new = executor.loader.project_state([("properties", "0004_remove_property_type")]).apps
    props = {p.code: p.category.name for p in new.get_model("properties", "Property").objects.all()}
    assert props == {"A": "Casa", "B": "Terreno"}

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())
