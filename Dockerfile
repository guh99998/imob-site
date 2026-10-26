FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=imob_site.settings.prod
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
ENV PATH="/app/.venv/bin:$PATH"
RUN apt-get update && apt-get install -y --no-install-recommends gettext && \
    rm -rf /var/lib/apt/lists/* && \
    SECRET_KEY=build ALLOWED_HOSTS=* python manage.py compilemessages -l pt_BR
RUN SECRET_KEY=build ALLOWED_HOSTS=* python manage.py tailwind build && \
    SECRET_KEY=build ALLOWED_HOSTS=* python manage.py collectstatic --noinput
RUN useradd --system --create-home app && \
    mkdir -p /app/media && chown app /app/media && chmod +x deploy/entrypoint.sh
USER app
EXPOSE 8000
CMD ["deploy/entrypoint.sh"]
