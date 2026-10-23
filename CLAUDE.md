# imob-site — Site de imobiliária (venda e aluguel)

## Stack
Django 6.1 · Python 3.13 · uv · PostgreSQL (prod) / SQLite (dev) · Templates + HTMX · Tailwind (django-tailwind-cli; tokens em `frontend/source.css`) · django-unfold (admin) · pytest-django · ruff

## Fluxo de trabalho (Spec-driven)
- Toda feature nasce em `specs/NNN-nome.md` (copiar `specs/000-template.md`).
- Antes de codar: ler o spec, confirmar critérios de aceite. Ao terminar: marcar tarefas e `Status: Concluído`.
- Não implementar fora do escopo do spec ativo; ideias novas viram um novo spec.
- **No fim de cada feature:** atualizar o `README.md` (o que tem hoje, estrutura, roadmap) e este `CLAUDE.md` (stack, comandos, convenções novas) antes do commit.
- Branches: trabalho em `develop`; `main` só recebe features concluídas (merge a pedido do usuário).
- Deploy não é Heroku: `Dockerfile` genérico (sem Procfile).

## Comandos
- Instalar: `uv sync` (uv não instalado? `pip install uv`; se `uv` não estiver no PATH, use `.venv\Scripts\uv.exe`)
- Tailwind (prod): `uv run python manage.py tailwind build && uv run python manage.py collectstatic`
- Prod: `DJANGO_SETTINGS_MODULE=imob_site.settings.prod` (vars em `.env.example`)
- Rodar: `uv run python manage.py tailwind runserver`
- Migrations: `uv run python manage.py makemigrations && uv run python manage.py migrate`
- Testes: `uv run pytest`
- Dados de exemplo: `uv run python manage.py seed_demo` (`--reset` recria; fotos em `demo/photos/`)
- Lint/format: `uv run ruff check . --fix && uv run ruff format .`

## Convenções
- Código (models, campos, variáveis) em inglês; textos de UI, `verbose_name`, mensagens em pt-BR com `gettext_lazy`.
- Apps em `apps/` (core, properties, leads). Settings em `imob_site/settings/{base,dev,prod}.py`, segredos via `.env`.
- Choices com `models.TextChoices`. Preços em `DecimalField(max_digits=12, decimal_places=2)`.
- Público só vê imóveis `Property.objects.published()` (publicado + reservado; vendido/alugado só no painel).
- Código do imóvel é automático por categoria (`Category.code_prefix` + `CodeSequence`: CA001); nunca editar à mão.
- Campos com máscara no admin: `MaskedAdminMixin` (`apps/core/admin_masks.py`) + `static/core/admin/masks.js`. Módulos opcionais por site: `FEATURES` / `apps/core/features.py`.
- Favoritos do visitante: cookie `favs`, lido/gravado só por `apps/properties/favorites.py`; `favorite_codes`/`favorites_total` vêm do context processor (a view sobrescreve no contexto quando muda o cookie).
- Buscas do site: `apps/properties/searches.py` grava `SearchQuery` (chave normalizada, sem dado pessoal, ignora robôs) a partir de `property_list`; a home lê `popular()`.
- Views HTMX: detectar `request.htmx` e retornar partial de `templates/partials/`; a página deve funcionar sem JS.
- Categorias de imóvel são cadastro editável (`Category`), não TextChoices.
- CRUD é feito no Django Admin (django-unfold; sidebar em `UNFOLD["SIDEBAR"]`) — evoluir o admin antes de criar telas próprias.
- Testes para models, filtros e views em `apps/<app>/tests/`, usando factory-boy.
- Ícones: Bootstrap Icons, só os necessários, como SVG inline em `templates/partials/icons/` (sem importar a biblioteca).
- Não commitar `.env`, `db.sqlite3`, `media/`.
