# 010 — Redesign do site + painel admin simplificado (DevLopesMóveis)

**Status:** Concluído

## Objetivo
Dar identidade própria ao site público (editorial, guiado por fotos, vídeo no hero) e transformar o
Django Admin em um painel organizado por seções com django-unfold e Categorias editáveis.
Detalhes completos em `plans/plano-010-redesign-admin.md`.

## Contexto
MVP (specs 001–009) funciona, mas o visual é genérico e o admin é técnico demais.
Decisões: tema Unfold · categoria vira cadastro editável · marca "DevLopesMóveis".

## Requisitos
- A: `Category` editável substitui `Property.Type`; `code`/slug gerados automaticamente (Property, City, Neighborhood).
- B: Admin com django-unfold, sidebar por seções, dashboard, PropertyAdmin em abas, fotos ordenáveis.
- C: Site público redesenhado (tokens, ficha técnica, hero com vídeo, listagem com drawer de filtros, detalhe com lightbox e semelhantes).
- D: Conteúdo de exemplo (Pexels) e comando `seed_demo`.

## Fora de escopo
Novas funcionalidades além das descritas no plano.

## Modelo de dados
`Category(name, slug, order, icon)`; `Property.category` FK PROTECT (migration em 3 passos).

## UI / URLs
Sem novas URLs públicas; home e listagem ganham categorias/cidades com contagem.

## Critérios de aceite
- `uv run pytest` verde e `uv run ruff check .` limpo.
- `seed_demo` popula o site; `check --deploy` (settings prod) sem avisos.

## Testes
Category, geração de código/slug, migração de dados, dashboard, sidebar sem Groups, home com categorias, semelhantes.

## Tarefas
- [x] A — Modelo Category + migrations + filtros/factories/testes
- [x] B — Unfold: settings, sidebar, dashboard, admins
- [x] C — Tokens Tailwind, base, home, listagem, detalhe, ficha, leads
- [x] D — Mídia de exemplo + seed_demo
- [x] Verificação final (pytest, ruff, check --deploy)
