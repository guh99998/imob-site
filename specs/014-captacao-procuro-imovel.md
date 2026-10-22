# 014 — Captação ("Procuro um imóvel", Anuncie, Contato)

**Status:** Concluído

## Objetivo
Captar leads além do formulário do imóvel: visitantes que procuram um imóvel, donos que querem anunciar e contato geral.

## Contexto
Quarta spec do plano `plans/plano-011-014-ajustes-mvp.md`. Reaproveita a infra de `apps/leads` (honeypot, rate limit, e-mail).

## Requisitos
- `/quero-um-imovel/`: formulário (nome, WhatsApp, e-mail, finalidade, categorias, cidade/bairros, faixa de preço, quartos/vagas mínimos, observações, aceite LGPD). Novo modelo `PropertySearch`. HTMX com fallback sem JS.
- Helpers de anti-spam/notificação extraídos para `apps/leads/services.py`.
- `/anuncie/` e `/contato/`: formulário usando `Lead.kind` (PROPERTY/CONTACT/LISTING).
- Admin: "Procuras de clientes" (status, badge, "Ver imóveis compatíveis", "Marcar como contatado"). Dashboard com "Procuras novas".
- Módulo ligável por `FEATURES=searches`.

## Fora de escopo
Alertas automáticos de novos imóveis compatíveis.

## Modelo de dados
`leads.Lead.kind`; `leads.PropertySearch`.

## UI / URLs
`/quero-um-imovel/`, `/anuncie/`, `/contato/`.

## Critérios de aceite
- Envio com e sem JS cria o registro e dispara e-mail; excesso de envios é bloqueado.
- Compatíveis abre a lista do painel já filtrada.

## Testes
Formulários, anti-spam, rate limit, kinds, admin (ações e filtros), feature flag.

## Tarefas
- [x] Models, services e forms
- [x] Views e templates
- [x] Admin, dashboard, sidebar
- [x] Testes, seed, lint
