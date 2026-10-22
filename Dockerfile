FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=imob_site.settings.prod
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
ENV PATH="/app/.venv/bin:$PATH"
RUN SECRET_KEY=build ALLOWED_HOSTS=* python manage.py tailwind build && \
    SECRET_KEY=build ALLOWED_HOSTS=* python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["gunicorn", "imob_site.wsgi", "--bind", "0.0.0.0:8000", "--workers", "3"]
