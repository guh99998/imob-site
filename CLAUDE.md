# imob-site — Site de imobiliária (venda e aluguel)

## Stack
Django 6.1 · Python 3.13 · uv · PostgreSQL (prod) / SQLite (dev) · Templates + HTMX · Tailwind (django-tailwind-cli; tokens em `frontend/source.css`) · django-unfold (admin) · pytest-django · ruff

## Fluxo de trabalho (Spec-driven)
- Toda feature nasce em `specs/NNN-nome.md` (copiar `specs/000-template.md`).
- Antes de codar: ler o spec, confirmar critérios de aceite. Ao terminar: marcar tarefas e `Status: Concluído`.
- Não implementar fora do escopo do spec ativo; ideias novas viram um novo spec.
- **No fim de cada feature:** atualizar o `README.md` (o que tem hoje, estrutura, roadmap) e este `CLAUDE.md` (stack, comandos, convenções novas) antes do commit.
- Branches: trabalho em `develop`; `main` só recebe features concluídas (merge a pedido do usuário).
- Deploy não é Heroku: `Dockerfile` genérico (sem Procfile). Produção: VPS com Docker Compose (spec 028); Caddy compartilhado em `deploy/proxy/`, imagem publicada pelo GitHub Actions no GHCR a cada push na `main`, backup com `deploy/backup.sh` (rclone/R2) e, para o MoneyPilot (outra stack na mesma VPS, `/opt/moneypilot`), `deploy/backup-moneypilot.sh` (dump `-Fc` em `/opt/backups`, cron 03:45). Atualizar a VPS: `git pull && docker compose pull web && docker compose up -d`.

## Comandos
- Instalar: `uv sync` (uv não instalado? `pip install uv`; se `uv` não estiver no PATH, use `.venv\Scripts\uv.exe`)
- Tailwind (prod): `uv run python manage.py tailwind build && uv run python manage.py collectstatic`
- Prod: `DJANGO_SETTINGS_MODULE=imob_site.settings.prod` (vars em `.env.example`)
- Rodar: `uv run python manage.py tailwind runserver`
- Migrations: `uv run python manage.py makemigrations && uv run python manage.py migrate`
- Testes: `uv run pytest`
- Modelos-base de documentos: `uv run python manage.py seed_document_templates`
- Duplicados (varredura): `uv run python manage.py find_duplicates`
- Dados de exemplo: `uv run python manage.py seed_demo` (`--reset` recria; fotos em `demo/photos/`)
- Lint/format: `uv run ruff check . --fix && uv run ruff format .`

## Convenções
- Código (models, campos, variáveis) em inglês; textos de UI, `verbose_name`, mensagens em pt-BR com `gettext_lazy`.
- Apps em `apps/` (core, properties, leads, people, crm, api). Settings em `imob_site/settings/{base,dev,prod}.py`, segredos via `.env`.
- Choices com `models.TextChoices`. Preços em `DecimalField(max_digits=12, decimal_places=2)`.
- Público só vê imóveis `Property.objects.published()` (publicado + reservado; vendido/alugado só no painel).
- Código do imóvel é automático por categoria (`Category.code_prefix` + `CodeSequence`: CA001); nunca editar à mão.
- Campos com máscara no admin: `MaskedAdminMixin` (`apps/core/admin_masks.py`) + `static/core/admin/masks.js`. Módulos opcionais por site: `FEATURES` / `apps/core/features.py`. Limite de destaques: `MAX_FEATURED` no `.env` (padrão 3). Links dinâmicos da sidebar do Unfold: passar o callable importado (string só vale em `badge`/`permission`). Card de imóvel recebe `price_mode` (SALE/RENT/vazio); imóvel BOTH sem seção mostra os dois preços (`Property.price_for`).
- Favoritos do visitante: cookie `favs`, lido/gravado só por `apps/properties/favorites.py`; `favorite_codes`/`favorites_total` vêm do context processor (a view sobrescreve no contexto quando muda o cookie).
- Buscas do site: `apps/properties/searches.py` grava `SearchQuery` (chave normalizada, sem dado pessoal, ignora robôs) a partir de `property_list`; a home lê `popular()`.
- Duplicados: `apps/properties/duplicates.py` (`find_duplicates`, `refresh_hints`, `dismiss`); `Property.duplicate_hint` é só cache para a lista do painel, recalculado ao salvar no admin e por `manage.py find_duplicates`. Vendido/alugado não entram na comparação.
- CRM (`apps/crm`, feature `crm`): todo contato do site passa por `apps/crm/services.py` (`register_lead`/`register_search` → `get_or_create_client`, casa por `Client.phone_key` e email); telefone sempre normalizado por `normalize_phone`. Dado pessoal novo em Lead/PropertySearch/Client deve entrar em `services.anonymize`. Interações do cliente: linha do tempo em `templates/admin/crm/client_timeline.html` (via `change_form_after_template`) + view `crm_client_add_interaction`; `InteractionAdmin` existe só para editar/excluir e fica fora do menu. Qualificação das partes (spec 026): mixin `people.models.QualifiedPerson` (CPF validado, estado civil, endereço, cônjuge) em `Client`, `Owner` e `Guarantor` (Pessoas → Fiadores; corretor só vê os que criou); dado pessoal novo da qualificação entra em `services.PERSONAL_QUALIFICATION_FIELDS`. Documentos ganham `cliente/proprietario/fiador.*` (+ `.conjuge.*` e `.qualificacao`) só como dicionários; avisos de cônjuge em `documents.spouse_warnings` (não bloqueiam). `ensure_base_templates` só atualiza modelo-base cujo texto ainda é o original (`LEGACY_HASHES`). Mudança de etapa do cliente sempre por `services.move_stage` (grava a interação); Kanban em `ClientAdmin.kanban` com drag-and-drop nativo (sem dependência).
- API (`apps/api`, feature `api`, ligada por padrão mas só responde com `Api-Key`): chave `Api-Key` guardada só como hash SHA-256 (`ApiKey.create_with_key`), 404 em tudo com o módulo desligado, throttle por chave (`API_THROTTLE_RATE`). Todo endpoint novo usa `permission_classes` de `apps/api/permissions.py` e reaproveita `apps/crm/services.py`; documentação via drf-spectacular. Escrita de imóveis (spec 032): só chave `FULL`; toda gravação passa por `apps/properties/services.py` (`upsert_property`, `add_photo`: limites de tipo/tamanho, URL só http(s) com IP público) e registra histórico com `source="API: <chave>"`; a importação em lote (033) reaproveita os mesmos serviços.
- Documentos (`apps/crm/documents.py`): o texto do modelo é editado por funcionários, então roda no engine isolado de `documents.py` com contexto **só de dicionários** (`build_context`, nunca instância de model), sem `include`/`extends`/`debug`, e sai escapado por `to_html`. Variável nova para os modelos = nova chave em `build_context`.
- Views HTMX: detectar `request.htmx` e retornar partial de `templates/partials/`; a página deve funcionar sem JS.
- Categorias de imóvel são cadastro editável (`Category`), não TextChoices.
- CRUD é feito no Django Admin (django-unfold; sidebar em `UNFOLD["SIDEBAR"]`) — evoluir o admin antes de criar telas próprias.
- Testes para models, filtros e views em `apps/<app>/tests/`, usando factory-boy.
- Ícones: Bootstrap Icons, só os necessários, como SVG inline em `templates/partials/icons/` (sem importar a biblioteca).
- Traduções: `LOCALE_PATHS = locale/`; `locale/pt_BR/LC_MESSAGES/django.po` traz os textos do Unfold que o Django não cobre; `.mo` é commitado (sem `msgfmt` local, gere com um script Python) e o Dockerfile roda `compilemessages`. Texto novo do Unfold em inglês = nova entrada no `.po` + recompilar.
- Menu do Unfold: link callable não marca "ativo"; use `"active": "apps.core.admin_navigation.<x>"` com `path_active(...)`. Faixa de demonstração do site: `DEMO_MODE` no `.env`. Categorias e demais cadastros em ordem alfabética (`Meta.ordering`); sem campo de ordem manual (só fotos têm).
- Duplicado no cadastro (spec 030): `PropertyAdminForm.clean()` bloqueia cadastro novo parecido até `not_duplicate` vir (ids do JS ou caixa "on" sem JS); a checagem ao vivo é `PropertyAdmin.check_duplicates` + `static/properties/admin/duplicates.js`; corretor com escopo nunca vê dados dos outros imóveis nem bloqueia.
- Histórico do imóvel (spec 031): toda mudança passa por `apps/properties/history.py` (`record_changes(prop, before, after, user, source)`; API/importação usam `source="API: <chave>"`). Mudança em massa de imóvel usa `PropertyAdmin._apply` (passa pelo `save()`, não `queryset.update`). Prazo de revisão em `apps/properties/reviews.py`; `Property.save()` agenda ao publicar, `mark_reviewed` ao revisar.
- Não commitar `.env`, `db.sqlite3`, `media/`.
