# 025 — Kanban de clientes

**Status:** Concluído

## Objetivo
Funil visual dos clientes por etapa, com arrastar e soltar.

## Requisitos
- Página `admin:crm_client_kanban` (`crm/client/kanban/`), item "Funil (Kanban)" na sidebar e atalho no dashboard.
- Colunas = `Client.Stage`; cards com nome, WhatsApp, corretor, próximo retorno (atrasado em vermelho) e link da ficha.
- Fechado/Perdido: só os últimos 30 dias + "ver todos" (lista filtrada por etapa).
- Corretor vê só os seus; anonimizados escondidos; filtro por corretor (não-corretores).
- Arrastar e soltar (HTML5 nativo, sem dependência) → `POST crm/client/<id>/etapa/`; sem JS, seletor "Mover para…" em cada card.
- Mudar a etapa (Kanban ou ação em massa) grava interação "Etapa: A → B" (`services.move_stage`).

## Fora de escopo
Ordenação manual dentro da coluna.

## UI / URLs
`templates/admin/crm/kanban.html`; `crm_client_kanban`, `crm_client_stage`.

## Critérios de aceite
Arrastar um card muda a etapa e aparece a interação na linha do tempo.

## Testes
`apps/crm/tests/test_spec025.py`.

## Tarefas
- [x] View, URLs e template
- [x] Drag and drop + seletor sem JS
- [x] Interação automática
- [x] Sidebar/dashboard, testes, README/CLAUDE.md, commit
