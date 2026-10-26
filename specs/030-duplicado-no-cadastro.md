# 030 — Duplicado avisado no cadastro

**Status:** Concluído

## Objetivo
Avisar de um possível duplicado **antes** de salvar o imóvel novo, com opções claras (atualizar o existente ou confirmar que não é duplicado). Hoje o aviso só aparece depois de salvar. Detalhes no plano `plans/2026-10-26-correcoes-admin.md`.

## Contexto
Spec 019 criou a detecção (`apps/properties/duplicates.py`), o selo "Possível" e a dispensa de pares (`DuplicateDismissal`).

## Requisitos
1. `find_duplicates` aceita imóvel não salvo (`unsaved_from`).
2. Endpoint admin `property/check-duplicates/` (POST, campos-chave) devolve o painel de cards (foto, código, título, preço, endereço, situação) ou 204; JS com debounce na página de cadastro.
3. Cada card: "Quero atualizar esse imóvel" (abre o existente). Botão "Não é duplicado" guarda os ids no campo `not_duplicate`.
4. Sem JS: `PropertyAdminForm.clean()` mostra o mesmo painel como erro e troca `not_duplicate` por uma caixa de confirmação (fotos precisam ser escolhidas de novo).
5. Ao salvar com confirmação: `DuplicateDismissal` por par, sem selo "Possível".
6. Corretor com escopo próprio: só o aviso genérico, sem dados dos outros imóveis, não bloqueia nem dispensa.

## Fora de escopo
Checagem na edição de imóvel já salvo (continua o aviso pós-save do spec 019).

## Modelo de dados
Nenhuma migration.

## UI / URLs
`admin:properties_property_check_duplicates`; `templates/admin/properties/duplicates_{slot,panel}.html`; `apps/properties/static/properties/admin/duplicates.js`.

## Critérios de aceite
Ver "Verificação → 030" do plano.

## Testes
`apps/properties/tests/test_spec030.py`: instância não salva, endpoint (painel, 204, só POST, escopo), `clean` com/sem confirmação, dismissal criado, painel sem JS, corretor não bloqueado.

## Tarefas
- [x] `duplicates.py`: instância não salva e `dismiss_pair_ids`
- [x] Endpoint, painel e JS
- [x] `clean()` com fallback sem JS
- [x] Dismissal ao salvar; regra do corretor
- [x] Testes, README, CLAUDE.md
