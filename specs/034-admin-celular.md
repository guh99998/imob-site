# 034 — Admin no celular

**Status:** Concluído

## Objetivo
Acompanhar métricas, cadastrar imóveis e ver clientes pelo celular. O painel quebrava em telas estreitas (página alargada, tabelas cortadas).

## Contexto
O Unfold já empilha formulários e filtros. O que quebrava era o que montamos por cima: painel inicial com colunas de largura mínima fixa, tabelas largas das listas e o kanban.

## Requisitos
1. Painel inicial: atalhos e números em grade que cabe em 390 px (`minmax(min(100%, X), 1fr)`).
2. Listas do admin: abaixo de 768 px cada linha vira um cartão "rótulo: valor"; células vazias ("-") somem (`mobile.css` + `mobile.js`).
3. Kanban: uma coluna por vez (rolagem com encaixe); a página não alarga (`contain: paint`); sem link "Ver em lista" duplicado.
4. Painéis nossos (duplicados, importação): botões com área de toque de 44 px e cards em uma coluna.
5. Carregado em todo o admin pelo `UNFOLD["STYLES"]`/`["SCRIPTS"]`.

## Fora de escopo
App nativo/PWA; reorganizar o formulário de imóvel (já é uma coluna no Unfold); modo offline.

## Modelo de dados / UI
Sem migrations. Arquivos: `apps/core/static/core/admin/mobile.{css,js}`, `templates/admin/index.html`, `templates/admin/crm/kanban.html`.

## Critérios de aceite
Em 390 px (Chromium com `is_mobile`), nenhuma tela principal tem rolagem lateral da página: painel, imóveis (lista, novo, editar), clientes, kanban, retornos, procuras, mensagens, importação.

## Testes
`apps/core/tests/test_spec034.py` (arquivos e ligação no Unfold, grades sem largura fixa); verificação visual feita no Playwright.

## Tarefas
- [x] Auditoria das telas em 390 px
- [x] Painel inicial e atalhos
- [x] Listas em cartões
- [x] Kanban
- [x] Testes, README, CLAUDE.md
