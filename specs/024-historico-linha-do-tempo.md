# 024 — Histórico do cliente em linha do tempo

**Status:** Concluído

## Objetivo
Trocar o inline tabular de interações por uma linha do tempo legível, com formulário "Registrar interação".

## Requisitos
- Cartões do mais recente ao mais antigo: ícone por tipo, data, autor, imóvel e texto (com quebras de linha, escapado).
- Formulário (tipo, quando, imóvel opcional, texto) posta em `crm_client_add_interaction`; autor = usuário logado.
- Editar/excluir por link em cada cartão (`InteractionAdmin` fora do menu), conforme permissão; escopo do corretor mantido.
- Cliente anonimizado: sem formulário e POST recusado (403).
- Retornos continuam inline.

## Fora de escopo
Etapa automática no histórico (025).

## UI / URLs
`templates/admin/crm/client_timeline.html` via `change_form_after_template`; `POST /admin/crm/client/<id>/interacao/`.

## Critérios de aceite
Registrar interação na ficha mostra o cartão no topo da lista.

## Testes
`apps/crm/tests/test_spec024.py`.

## Tarefas
- [x] Linha do tempo + formulário
- [x] InteractionAdmin oculto (editar/excluir)
- [x] Testes, README/CLAUDE.md, commit
