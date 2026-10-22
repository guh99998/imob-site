# 013 — Pessoas, funções e auditoria

**Status:** Concluído

## Objetivo
Cadastro de corretores, parceiros e proprietários (só no painel), funções prontas por usuário e registro de quem cadastrou/editou cada imóvel.

## Contexto
Terceira spec do plano `plans/plano-011-014-ajustes-mvp.md`. Depende dos módulos ligáveis (`FEATURES`) da 012.

## Requisitos
- Novo app `apps/people`: `Broker`, `Partner`, `Owner`. `Property` ganha `broker`, `partner`, `owner`, `source`, `created_by`, `updated_by`.
- Grupos prontos criados no `post_migrate`: **Administrador**, **Gerente**, **Corretor**, **Atendente**.
- Campo único "Função" no cadastro de usuário (aplica grupo + `is_staff`); permissões cruas só para superusuário; Equipe só para Administrador.
- `ScopedByRoleMixin`: Corretor só vê/edita imóveis em que é o responsável ou criador; sem excluir; vê só as mensagens dos próprios imóveis.
- Auditoria só no painel: aba "Registro", histórico Django ligado, "Atividade recente" no dashboard.
- Nada disso aparece no site público (HTML, JSON-LD, sitemap).

## Fora de escopo
Detecção de imóveis duplicados (backlog; `zip_code`/`number` indexados).

## Modelo de dados
`people.Broker/Partner/Owner`; `properties.Property` novos campos; índice `(zip_code, number)`.

## UI / URLs
Seção "Pessoas" na sidebar (respeita `FEATURES`).

## Critérios de aceite
- Cada função vê/edita só o que deve.
- "Cadastrado por" aparece no painel e nunca no site.

## Testes
Grupos/permissões, escopo do Corretor, formulário de usuário, auditoria, vazamento no site público, feature flags.

## Tarefas
- [x] App people + migrations
- [x] Funções (grupos) e formulário de usuário
- [x] Escopo por função
- [x] Auditoria e dashboard
- [x] Testes, seed, lint
