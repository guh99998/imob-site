# 028 — Deploy em VPS com Docker Compose

**Status:** Em andamento (no ar em HTTPS na VPS; falta testar restauração de backup e CI/CD)

## Objetivo
Subir o site em uma VPS: Postgres e app (gunicorn) neste compose; Caddy com HTTPS automático em stack compartilhada (`deploy/proxy/`), para hospedar outros apps na mesma VPS.

## Requisitos
- `docker-compose.yml`: `db` (Postgres 17) e `web` (Dockerfile) com `mem_limit`; rede externa `proxy` e volume externo `imob_media`, criados à mão uma vez.
- `deploy/proxy/`: Caddy (portas 80/443), um bloco por domínio no `Caddyfile`.
- `deploy/backup.sh`: dump do Postgres + fotos, retenção de 14 dias.
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
- [x] Deploy real na VPS (Debian, Hostinger) com HTTPS
- [x] Script de backup; README
- [ ] Testar restauração do backup; agendar no cron
- [ ] CI/CD (GitHub Actions + GHCR)
