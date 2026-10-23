# imob-site

Site de imobiliária (venda e aluguel) com painel de gestão. Django 6.1, Python 3.13, Templates + HTMX, Tailwind e django-unfold (admin).

## O que tem hoje
- **Site público:** home com busca completa, lista com filtros e paginação, detalhe do imóvel (galeria, ficha, comodidades), SEO (sitemap, JSON-LD, Open Graph).
- **Contato:** WhatsApp com mensagem pronta por imóvel (texto editável no painel), botão "Copiar link do imóvel", formulários de interesse, "Procuro um imóvel", "Anuncie seu imóvel" e Contato.
- **Favoritos:** coração nos cards e no detalhe, página `/favoritos/` e contador no header, sem login (cookie `favs`, funciona sem JS). O painel mostra quantas vezes cada imóvel foi favoritado.
- **Painel (`/admin/`):** imóveis com código automático por categoria, fotos em lote, máscaras, pesquisa avançada, mensagem pronta para o cliente, leads e procuras, corretores/parceiros/proprietários com funções e auditoria.
- **Módulos opcionais por site:** variável `FEATURES` (`brokers`, `partners`, `owners`, `searches`).

## Como rodar (desenvolvimento)
```bash
pip install uv            # se ainda não tiver
uv sync
cp .env.example .env
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py seed_demo        # dados de exemplo (--reset recria)
uv run python manage.py tailwind runserver
```
Site em http://localhost:8000 e painel em http://localhost:8000/admin/.

## Comandos úteis
| O quê | Comando |
|---|---|
| Testes | `uv run pytest` |
| Lint e formato | `uv run ruff check . --fix && uv run ruff format .` |
| Migrations | `uv run python manage.py makemigrations && uv run python manage.py migrate` |
| Tailwind (prod) | `uv run python manage.py tailwind build && uv run python manage.py collectstatic` |

## Estrutura
```
apps/core         configurações do site, home, painel (dashboard, máscaras, features)
apps/properties   imóveis, categorias, cidades/bairros, busca e filtros
apps/leads        contatos, anúncios e procuras de clientes
apps/people       corretores, parceiros, proprietários, funções e auditoria
imob_site/settings  base, dev e prod
templates/  frontend/  static/
specs/      uma spec por feature (NNN-nome.md)
plans/      planejamentos
```

## Deploy
Qualquer host que rode contêiner ou Python (não depende de uma plataforma específica).
- `Dockerfile` pronto: compila o Tailwind, roda `collectstatic` e sobe o `gunicorn` na porta 8000.
- Use `DJANGO_SETTINGS_MODULE=imob_site.settings.prod` e as variáveis de `.env.example` (`SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL` do PostgreSQL, e-mail).
- Rode `python manage.py migrate --noinput` a cada versão nova, antes de subir o app.
- Mídia (fotos) em disco ou em storage S3 compatível (`AWS_STORAGE_BUCKET_NAME` etc.).
- Antes de publicar: `python manage.py check --deploy`.

## Fluxo de trabalho
Spec-driven: toda feature nasce em `specs/NNN-nome.md` (copiar `specs/000-template.md`). Ao terminar, marcar as tarefas, `Status: Concluído`, e atualizar este README e o `CLAUDE.md`. Branch de trabalho: `develop`; `main` recebe só o que está concluído.

## Roadmap
Plano em `plans/plano-016-022-novas-funcoes.md`:
- [x] 016 — WhatsApp com mensagem pronta, copiar link, crédito do desenvolvedor
- [x] 017 — Favoritos (cookie, sem login)
- [ ] 018 — Buscas populares na home
- [ ] 019 — Detecção de imóveis duplicados
- [ ] 020 — CRM de clientes
- [ ] 021 — API aberta do CRM
- [ ] 022 — Modelos de documentos (visita, contrato, recibo)
