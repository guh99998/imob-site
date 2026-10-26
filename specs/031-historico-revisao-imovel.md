# 031 — Histórico do imóvel + data de revisão

**Status:** Concluído

## Objetivo
Saber quem mudou o quê em cada imóvel e não deixar anúncio publicado desatualizado: prazo de revisão com avisos. Detalhes no plano `plans/2026-10-26-correcoes-admin.md`.

## Requisitos
**Histórico (sem dependência nova)**
1. `PropertyChange(property, user, source, created_at, changes JSON [{field, label, old, new}])`.
2. `apps/properties/history.py`: `snapshot`, `diff`, `record_changes`, `record_created`, `append_changes`; valores legíveis (FK pelo nome, choices pelo rótulo, preço em BRL, Sim/Não).
3. Gravado no `save_model`/`save_related` do painel (inclui comodidades e nº de fotos, numa só linha) e nas ações em lote (`source="Ação em lote"`). API e importação (specs 032/033) usam `record_changes`.
4. Seção "Histórico de alterações" no fim do formulário do imóvel (últimas 50).

**Revisão**
5. `Property.review_due` (editável), `last_reviewed_at`, `last_reviewed_by`; `SiteSettings.review_interval_days` (60; 0 desliga).
6. `Property.save()` define o prazo ao publicar (não sobrescreve data futura escolhida); "Marcar como revisado" (linha e lote) = hoje + intervalo. Só publicado/reservado conta. Data migration preenche os publicados atuais.
7. Avisos: item "Revisões pendentes" na sidebar com badge (corretor vê só os seus), número e atalho no painel, filtro "Revisão" (vencida / vence em 7 dias / em dia) e coluna na lista.

## Fora de escopo
Notificação por email das revisões; histórico de outros modelos.

## Modelo de dados
Migrations `properties/0016` (campos + `PropertyChange`), `properties/0017` (dados), `core/0007` (`review_interval_days`).

## Critérios de aceite
Ver "Verificação → 031" do plano.

## Testes
`apps/properties/tests/test_spec031.py`.

## Tarefas
- [x] Modelos e migrations
- [x] `history.py` e gravação no painel e nas ações em lote
- [x] Seção de histórico no formulário
- [x] `reviews.py`, ações "Marcar como revisado", filtro e coluna
- [x] Sidebar, painel e configuração do intervalo
- [x] Testes, README, CLAUDE.md
