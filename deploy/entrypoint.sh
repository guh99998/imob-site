#!/bin/sh
# Aplica as migrations (idempotente) e sobe o gunicorn. Roda a cada start do contêiner.
set -e
python manage.py migrate --noinput
exec gunicorn imob_site.wsgi --bind 0.0.0.0:8000 --workers "${WEB_CONCURRENCY:-3}" --access-logfile -
