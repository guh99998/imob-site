import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

pytestmark = pytest.mark.django_db


def test_healthz_checks_database(client):
    with CaptureQueriesContext(connection) as queries:
        r = client.get("/healthz/")
    assert r.status_code == 200 and r.content == b"ok"
    assert any("SELECT 1" in q["sql"] for q in queries)


def test_prod_exempts_healthz_from_ssl_redirect(monkeypatch):
    for key, value in {"SECRET_KEY": "x", "ALLOWED_HOSTS": "example.com"}.items():
        monkeypatch.setenv(key, value)
    import importlib

    from imob_site.settings import prod

    prod = importlib.reload(prod)
    assert prod.SECURE_REDIRECT_EXEMPT == [r"^healthz/$"]
    assert prod.SECURE_SSL_REDIRECT is True
