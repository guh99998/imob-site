from django.db import migrations

# (valor antigo de property_type, nome, ordem)
DEFAULTS = [
    ("APARTMENT", "Apartamento", 1),
    ("HOUSE", "Casa", 2),
    ("PENTHOUSE", "Cobertura", 3),
    ("LAND", "Terreno", 4),
    ("COMMERCIAL", "Comercial", 5),
]


def forwards(apps, schema_editor):
    Category = apps.get_model("properties", "Category")
    Property = apps.get_model("properties", "Property")
    for old, name, order in DEFAULTS:
        cat, _ = Category.objects.get_or_create(
            slug=name.lower(), defaults={"name": name, "order": order}
        )
        Property.objects.filter(property_type=old).update(category=cat)


def backwards(apps, schema_editor):
    Category = apps.get_model("properties", "Category")
    Property = apps.get_model("properties", "Property")
    for old, name, _order in DEFAULTS:
        Property.objects.filter(category__slug=name.lower()).update(property_type=old)


class Migration(migrations.Migration):
    dependencies = [("properties", "0002_category")]

    operations = [migrations.RunPython(forwards, backwards)]
