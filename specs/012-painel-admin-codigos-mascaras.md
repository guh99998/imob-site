# 012 — Painel admin (tema, códigos, formatação)

**Status:** Concluído

## Objetivo
Painel mais simples e previsível: só tema claro, sidebar correta, código automático por categoria, campos formatados e módulos ligáveis por site.

## Contexto
Segunda spec do plano `plans/plano-011-014-ajustes-mvp.md`.

## Requisitos
- Só tema claro (`UNFOLD["THEME"] = "light"`; remover bloco dark do dashboard).
- Sidebar: "Todos os imóveis" ativo na lista/edição; "Cadastrar imóvel" só em `/add/` (callback `active`).
- `Category.code_prefix` (2 letras, único; sugerido pelo nome) + `CodeSequence` com `select_for_update`; códigos `CA001`, `LO001`. `code` só leitura; aba "Avançado" removida. Data migration renomeia códigos antigos; `slug` não muda.
- Máscaras (JS puro) e parse server-side: moeda, área (m²), CEP, telefone/WhatsApp, UF, CPF/CNPJ, CRECI. Validadores de CPF/CNPJ.
- Feature flags: `SITE_FEATURES` (env `FEATURES`), `apps/core/features.py: enabled()`, respeitado na sidebar e em `FeatureGatedAdminMixin`.

## Fora de escopo
Modelos de pessoas (spec 013) e captação (014).

## Modelo de dados
`properties.Category.code_prefix`, `properties.CodeSequence(prefix, last)`.

## UI / URLs
Admin apenas.

## Critérios de aceite
- Criar imóvel pelo admin gera `CA001`; segundo da mesma categoria `CA002`.
- `1.234,56` e `R$ 1.234,56` são aceitos nos campos de valor.
- Só um item ativo na sidebar.

## Testes
Parse de moeda, código sequencial por prefixo, migração de códigos, sidebar ativa, tema, CPF/CNPJ, features.

## Tarefas
- [x] Tema e sidebar
- [x] Código por categoria + migrations
- [x] Máscaras, widgets e validadores
- [x] Feature flags
- [x] Testes, seed, lint
