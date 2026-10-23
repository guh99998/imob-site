# 017 — Favoritos (sem login, por cookie)

**Status:** Concluído

## Objetivo
Deixar o visitante guardar imóveis para ver depois, sem criar conta, e dar à imobiliária um sinal de quais imóveis atraem mais interesse.

## Contexto
Plano em `plans/plano-016-022-novas-funcoes.md` (bloco 017). Cookie, e não localStorage, para a página funcionar sem JS: o servidor lê o cookie e renderiza.

## Requisitos
- Cookie `favs` com os códigos separados por vírgula (ex.: `CA001,AP003`), no máximo 50, 1 ano, `SameSite=Lax`, `HttpOnly`. Código fora do formato (`[A-Za-z0-9-]{1,20}`) é descartado ao ler.
- `POST /imoveis/<slug>/favoritar/` alterna o favorito (só imóveis `published()`; senão 404).
  - Com `request.htmx`: devolve `partials/favorite_button.html` + o contador do header em `hx-swap-oob`.
  - Sem JS: redireciona para `next` (só URL do próprio site), senão para o detalhe.
- `GET /favoritos/`: lista os favoritos com `Property.objects.published().filter(code__in=...)`, do mais recente para o mais antigo, com `partials/property_card.html`. Vendido/alugado/rascunho some sozinho e o cookie é regravado só com os que ficaram. `noindex`.
- Coração no `property_card.html` (canto superior direito da foto; o selo "Reservado" passa para o lado do selo de finalidade) e no detalhe (botão "Salvar nos favoritos" / "Salvo nos favoritos").
- Header (desktop e mobile): link "Favoritos" com o total. O total vem do context processor (`favorite_codes`, `favorites_total`), contando os códigos do cookie.
- `Property.favorites_count`: sobe com `F()` ao favoritar (não desce ao desfavoritar), sem mexer em `updated_at`/auditoria. Coluna ordenável "favoritos" no admin, só leitura.
- Ícones Bootstrap `heart` e `heart-fill` em `templates/partials/icons/`.

## Fora de escopo
Favoritos ligados a conta/CRM (020), comparar imóveis, enviar a lista por WhatsApp.

## Modelo de dados
`Property.favorites_count` (`PositiveIntegerField`, default 0, não editável).

## UI / URLs
- `properties:favorite` — `POST /imoveis/<slug>/favoritar/`
- `core:favorites` — `GET /favoritos/`

## Critérios de aceite
- Favoritar e desfavoritar funcionam com o JS desligado (form POST + redirect) e com HTMX (troca só o botão e o contador).
- Imóvel vendido some de `/favoritos/` e do total no header depois de abrir a página.
- Cookie com lixo não quebra nenhuma página.
- `favorites_count` aparece e ordena na lista do admin.

## Testes
`apps/properties/tests/test_spec017.py`.

## Tarefas
- [x] Campo `favorites_count` + migration
- [x] `apps/properties/favorites.py` (ler/gravar cookie)
- [x] Views `favorite` (toggle) e `favorite_list` (lista) + URLs
- [x] Partial do botão, coração no card e no detalhe, link no header
- [x] Context processor
- [x] Admin: coluna e ordenação
- [x] Testes
- [x] README / CLAUDE.md
