# 028 — Deploy em VPS com Docker Compose

**Status:** Em andamento (imagem ainda não buildada: Docker Desktop estava desligado)

## Objetivo
Subir o site em uma VPS com um comando: Postgres, app (gunicorn) e Caddy com HTTPS automático.

## Requisitos
- `docker-compose.yml`: `db` (Postgres 17), `web` (Dockerfile) e `caddy`; volumes `pgdata`, `media`, `caddy_*`.
- `Dockerfile`: usuário sem privilégio, `deploy/entrypoint.sh` (migrate + gunicorn).
- Fotos enviadas no painel ficam no volume `media`, servido pelo Caddy em `/media/` (o Django em produção não serve mídia).
- Estáticos continuam no WhiteNoise.
- `GET /healthz/` (consulta o banco; isento do redirect HTTPS) usado no healthcheck do contêiner.
- `.env.production.example` com todas as variáveis; `.env` nunca vai para o git nem para a imagem.
- README: passo a passo (primeiro deploy, atualização, backup, superusuário).

## Fora de escopo
CI/CD, múltiplos servidores, S3 (já suportado por variáveis, só documentado).

## Critérios de aceite
`docker compose up -d --build` com `.env` preenchido sobe o site em HTTPS; `/admin/` abre e o upload de foto aparece em `/media/`.

## Testes
`apps/core/tests/test_spec028.py` (healthz). Build da imagem verificado com `docker build`.

## Tarefas
- [x] Compose, Caddyfile, entrypoint, Dockerfile
- [x] Healthcheck
- [ ] README/CLAUDE.md, commit
