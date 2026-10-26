from datetime import timedelta

from django.db import migrations
from django.utils import timezone

DEFAULT_INTERVAL = 60


def populate(apps, schema_editor):
    Property = apps.get_model("properties", "Property")
    due = timezone.localdate() + timedelta(days=DEFAULT_INTERVAL)
    Property.objects.filter(status__in=["PUBLISHED", "RESERVED"], review_due__isnull=True).update(
        review_due=due
    )


class Migration(migrations.Migration):
    dependencies = [("properties", "0016_review_and_history")]

    operations = [migrations.RunPython(populate, migrations.RunPython.noop)]
