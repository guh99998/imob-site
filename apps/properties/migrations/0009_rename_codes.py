import re

from django.db import migrations

PREFIXES = {
    "Casa": "CA",
    "Terreno": "LO",
    "Apartamento": "AP",
    "Cobertura": "CO",
    "Comercial": "SC",
    "Sobrado": "SO",
    "Studio/Kitnet": "ST",
    "Casa de condomínio": "CC",
    "Chácara/Sítio": "CH",
    "Fazenda": "FA",
    "Flat": "FL",
    "Sala comercial": "SA",
    "Loja": "LJ",
    "Galpão": "GA",
    "Terreno em condomínio": "TC",
}


def _suggest(name, taken):
    letters = [c for c in re.sub(r"[^A-Za-z]", "", name).upper()] or ["X"]
    for second in letters[1:] + list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        if letters[0] + second not in taken:
            return letters[0] + second
    return letters[0] + "X"


def forwards(apps, schema_editor):
    Category = apps.get_model("properties", "Category")
    Property = apps.get_model("properties", "Property")
    Sequence = apps.get_model("properties", "CodeSequence")

    taken = {c.code_prefix for c in Category.objects.exclude(code_prefix__isnull=True)}
    for cat in Category.objects.filter(code_prefix__isnull=True).order_by("order", "id"):
        wanted = PREFIXES.get(cat.name)
        prefix = wanted if wanted and wanted not in taken else _suggest(cat.name, taken)
        taken.add(prefix)
        cat.code_prefix = prefix
        cat.save(update_fields=["code_prefix"])

    # Renomeia códigos antigos (DLM-xxxx, DEMO-xx). O slug continua o mesmo.
    legacy = re.compile(r"^[A-Z]{2}\d{3,}$")
    counters = {}
    for cat in Category.objects.all():
        nums = [
            int(c[2:])
            for c in Property.objects.filter(category=cat, code__startswith=cat.code_prefix)
            .values_list("code", flat=True)
            if legacy.match(c)
        ]
        counters[cat.code_prefix] = max(nums, default=0)
    for prop in Property.objects.select_related("category").order_by("id"):
        if legacy.match(prop.code):
            continue
        prefix = prop.category.code_prefix
        counters[prefix] += 1
        # evita colidir com um código antigo parecido
        prop.code = f"{prefix}{counters[prefix]:03d}"
        prop.save(update_fields=["code"])
    for prefix, last in counters.items():
        if last:
            Sequence.objects.update_or_create(prefix=prefix, defaults={"last": last})


class Migration(migrations.Migration):
    dependencies = [("properties", "0008_category_code_prefix")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
