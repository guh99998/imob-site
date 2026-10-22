from django.db import migrations

NEW = [
    ("Studio/Kitnet", "studio-kitnet"),
    ("Sobrado", "sobrado"),
    ("Casa de condomínio", "casa-de-condominio"),
    ("Chácara/Sítio", "chacara-sitio"),
    ("Fazenda", "fazenda"),
    ("Flat", "flat"),
    ("Sala comercial", "sala-comercial"),
    ("Loja", "loja"),
    ("Galpão", "galpao"),
    ("Terreno em condomínio", "terreno-em-condominio"),
]


def forwards(apps, schema_editor):
    Category = apps.get_model("properties", "Category")
    start = Category.objects.count() + 1
    for i, (name, slug) in enumerate(NEW):
        if Category.objects.filter(name=name).exists():
            continue
        Category.objects.create(name=name, slug=slug, order=start + i)


class Migration(migrations.Migration):
    dependencies = [("properties", "0006_site_identity")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
