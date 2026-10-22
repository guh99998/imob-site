import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("properties", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=60, unique=True, verbose_name="nome")),
                ("slug", models.SlugField(blank=True, unique=True)),
                ("order", models.PositiveSmallIntegerField(default=0, verbose_name="ordem")),
                ("icon", models.CharField(blank=True, max_length=50, verbose_name="ícone")),
            ],
            options={
                "verbose_name": "categoria",
                "verbose_name_plural": "categorias",
                "ordering": ["order", "name"],
            },
        ),
        migrations.AddField(
            model_name="property",
            name="category",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="properties",
                to="properties.category",
                verbose_name="categoria",
            ),
        ),
    ]
