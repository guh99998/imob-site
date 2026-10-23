# 026 — Qualificação das partes, fiador e cônjuge nos contratos

**Status:** Concluído

## Objetivo
Contratos com a qualificação completa das partes (cliente, proprietário, fiador) e aviso quando falta o cônjuge.

## Requisitos
- Mixin `QualifiedPerson`: CPF validado, nacionalidade, estado civil, profissão, endereço em campos e cônjuge (nome, CPF, nacionalidade, profissão). Sem RG.
- Aplicado em `crm.Client`, `people.Owner` (CPF antigo de `document` copiado para `cpf` na migração; `document` continua para CNPJ) e novo `people.Guarantor` (Pessoas → Fiadores, feature `owners`; corretor só vê os que criou).
- Documentos: `cliente`, `proprietario` e `fiador` (+ `.conjuge`, `.qualificacao`) em `build_context`, só dicionários; formulário de gerar ganha "Fiador".
- Modelos-base de locação, intermediação e proposta usam a qualificação; só são atualizados se o texto ainda for o original (`LEGACY_HASHES`).
- Aviso (não bloqueia; "Gerar mesmo assim"): fiador casado sem cônjuge em locação; proprietário casado sem cônjuge em intermediação. Comprador/locatário sem exigência. Aviso também nas fichas.
- LGPD: campos novos do cliente entram na anonimização.

## Fora de escopo
RG; contrato de compra e venda (não existe modelo); campos novos na API.

## Testes
`apps/crm/tests/test_spec026.py`.

## Tarefas
- [x] Mixin, Guarantor e migrações
- [x] Admin (qualificação, cônjuge, máscaras, fiadores, sidebar, roles)
- [x] Contexto, avisos e modelos-base
- [x] Anonimização, testes, README/CLAUDE.md, commit
