import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("properties", "0003_populate_categories")]

    operations = [
        migrations.RemoveField(model_name="property", name="property_type"),
        migrations.AlterField(
            model_name="property",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="properties",
                to="properties.category",
                verbose_name="categoria",
            ),
        ),
    ]
