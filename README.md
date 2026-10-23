# imob-site

Site de imobiliária (venda e aluguel) com painel de gestão. Django 6.1, Python 3.13, Templates + HTMX, Tailwind e django-unfold (admin).

## O que tem hoje
- **Site público:** home com busca completa, lista com filtros e paginação, detalhe do imóvel (galeria, ficha, comodidades), SEO (sitemap, JSON-LD, Open Graph).
- **Contato:** WhatsApp com mensagem pronta por imóvel (texto editável no painel), botão "Copiar link do imóvel", formulários de interesse, "Procuro um imóvel", "Anuncie seu imóvel" e Contato.
- **Favoritos:** coração nos cards e no detalhe, página `/favoritos/` e contador no header, sem login (cookie `favs`, funciona sem JS). O painel mostra quantas vezes cada imóvel foi favoritado.
- **Mais procurados:** a home mostra as buscas mais feitas nos últimos 30 dias (sem dado pessoal, sem robôs); o painel lista a demanda em "Contatos → Buscas no site".
- **CRM de clientes:** tudo o que entra pelo site (mensagem de imóvel, contato, anúncio, "Procuro um imóvel") vira um cliente sem duplicar (casa por WhatsApp ou email), com histórico, corretor responsável, etapa do funil, retornos agendados (no dashboard e na sidebar) e anonimização (LGPD). O Corretor vê só os próprios clientes.
- **API aberta (opcional):** `/api/v1/` com chave (`Authorization: Api-Key …`) criada no painel: enviar contatos (sem duplicar cliente), ler/atualizar clientes e histórico, ler imóveis publicados. Documentação em `/api/docs/`. Desligada por padrão: ligue com `FEATURES=…,api`.
- **Documentos:** termo de visita, proposta, contratos e recibo gerados a partir de modelos editáveis no painel (com valor por extenso), em página A4 para imprimir ou salvar em PDF, com histórico de quem gerou o quê. Modelos-base de exemplo: `manage.py seed_document_templates`.
- **Duplicados:** ao salvar um imóvel o painel avisa se ele repete outro (mesmo CEP, número e complemento, ou características parecidas); coluna e filtro na lista, ação "Marcar como não duplicado" e comando `find_duplicates` para varrer o estoque.
- **Painel (`/admin/`):** imóveis com código automático por categoria, fotos em lote, máscaras, pesquisa avançada, mensagem pronta para o cliente, leads e procuras, corretores/parceiros/proprietários com funções e auditoria.
- **Módulos opcionais por site:** variável `FEATURES` (`brokers`, `partners`, `owners`, `searches`, `crm`, `api`; a `api` vem desligada).

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
| Modelos de documentos | `uv run python manage.py seed_document_templates` |
| Varrer duplicados | `uv run python manage.py find_duplicates` |
| Tailwind (prod) | `uv run python manage.py tailwind build && uv run python manage.py collectstatic` |

## Estrutura
```
apps/core         configurações do site, home, painel (dashboard, máscaras, features)
apps/properties   imóveis, categorias, cidades/bairros, busca e filtros
apps/leads        contatos, anúncios e procuras de clientes
apps/crm          clientes, histórico, retornos e captação automática
apps/api          chaves de API e endpoints /api/v1/
apps/people       corretores, parceiros, proprietários, funções e auditoria
imob_site/settings  base, dev e prod
templates/  frontend/  static/
specs/      uma spec por feature (NNN-nome.md)
plans/      planejamentos
```

## Deploy
VPS com Docker Compose (spec 028). O **Caddy** (HTTPS automático) é uma stack à parte em `deploy/proxy/`, compartilhada com outros apps da mesma VPS; este compose tem só `db` (Postgres) e `web` (gunicorn). Layout na VPS: `/opt/proxy`, `/opt/imob-site`, `/opt/backups`.
1. Uma vez por VPS: `docker network create proxy && docker volume create imob_media`; copie `deploy/proxy/*` para `/opt/proxy`. O `Caddyfile` tem um bloco por domínio.
2. Em `/opt/imob-site`: clone o repositório e `cp .env.production.example .env` (preencha `POSTGRES_PASSWORD`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, e-mail; `chmod 600 .env`). Aponte o DNS (registro A, sem proxy da Cloudflare) para a VPS.
3. `docker compose up -d --build` (as migrations rodam no start do app), depois `docker compose up -d` em `/opt/proxy`.
4. Superusuário: `docker compose exec web python manage.py createsuperuser`.
5. Atualizar: o GitHub Actions (`.github/workflows/ci.yml`) testa cada push e, na `main`, publica `ghcr.io/guh99998/imob-site:latest`; na VPS: `git pull && docker compose pull web && docker compose up -d`. Sem imagem publicada: `docker compose up -d --build`.
6. Backup: `deploy/backup.sh` grava `db-*.sql.gz` e `media-*.tar.gz` em `/opt/backups` (14 dias); agende no cron (instale `cron`) e, para guardar fora da VPS, configure um remoto `rclone` criptografado (ex.: Cloudflare R2 com token restrito ao bucket) e use `BACKUP_REMOTE=r2crypt:` na linha do cron (30 dias no destino). Restaurar o banco: `gunzip -c db-X.sql.gz | docker compose exec -T db psql -U imob imob`. Com S3 (`AWS_STORAGE_BUCKET_NAME`) as fotos saem do volume.
- Healthcheck: `GET /healthz/`. Fotos em `/media/` são servidas pelo Caddy (volume `imob_media`); estáticos pelo WhiteNoise. Só o Caddy publica portas (80/443); o banco nunca.
- Sem Docker: qualquer host Python com `DJANGO_SETTINGS_MODULE=imob_site.settings.prod`, `migrate --noinput` a cada versão e `check --deploy` antes de publicar.

## Fluxo de trabalho
Spec-driven: toda feature nasce em `specs/NNN-nome.md` (copiar `specs/000-template.md`). Ao terminar, marcar as tarefas, `Status: Concluído`, e atualizar este README e o `CLAUDE.md`. Branch de trabalho: `develop`; `main` recebe só o que está concluído.

## Roadmap
Plano em `plans/plano-016-022-novas-funcoes.md`:
- [x] 016 — WhatsApp com mensagem pronta, copiar link, crédito do desenvolvedor
- [x] 017 — Favoritos (cookie, sem login)
- [x] 018 — Buscas populares na home
- [x] 019 — Detecção de imóveis duplicados
- [x] 020 — CRM de clientes
- [x] 021 — API aberta do CRM
- [x] 022 — Modelos de documentos (visita, contrato, recibo)
- [x] 023 — Ajustes do site/painel (link Retornos, `MAX_FEATURED` no .env, código no card, preço por seção)
- [x] 024 — Histórico do cliente em linha do tempo com "Registrar interação"
- [x] 025 — Kanban de clientes (arrastar e soltar, últimos 30 dias em Fechado/Perdido)
- [x] 026 — Qualificação das partes (cliente, proprietário, fiador), cônjuge e avisos nos contratos

Plano em `plans/plano-023-027-ajustes-kanban-contratos.md` (024 histórico, 025 Kanban, 026 partes do contrato).
