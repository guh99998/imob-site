import pytest
from django.core.management import call_command

from apps.core.models import SiteSettings
from apps.properties.models import Property

pytestmark = pytest.mark.django_db


def test_seed_demo_is_idempotent(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    call_command("seed_demo")
    first = Property.objects.count()
    assert first == 36
    assert Property.objects.filter(status=Property.Status.SOLD).count() == 1
    assert SiteSettings.load().name == "DevLopesMóveis"
    assert SiteSettings.load().logo
    call_command("seed_demo")
    assert Property.objects.count() == first
    call_command("seed_demo", "--reset")
    assert Property.objects.count() == first
