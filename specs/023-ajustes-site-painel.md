# 023 — Correções e ajustes do site/painel

**Status:** Concluído

## Objetivo
Corrigir o link "Retornos" do menu e fazer cinco ajustes de site/painel pedidos na revisão das specs 017–022.

## Requisitos
1. **Bug "Retornos"**: o `link` da sidebar é o callable `followups_link` (importado), não string.
2. **Máximo de destaques** vira `MAX_FEATURED` no `.env` (padrão 3) e some do painel (`SiteSettings.max_featured` removido).
3. **Sem ícones editáveis** em `Category` e `Feature`.
4. **Código no card**: selo "Cód. CA001" no canto inferior esquerdo da foto.
5. **Preço por seção** (`purpose=BOTH`): `Property.price_for(purpose)`; na lista com filtro/landing de venda ou aluguel mostra o preço da seção; sem seção (home, lista sem filtro, semelhantes, favoritos) mostra os dois.
6. **Destaques da home** no estilo antigo: um grande + dois empilhados.

## Fora de escopo
Ícones fixos do painel (sidebar, dashboard).

## Modelo de dados
Migrations: remove `SiteSettings.max_featured`, `Category.icon`, `Feature.icon`.

## UI / URLs
`property_card.html` (selo + preços), `core/home.html` (destaques).

## Critérios de aceite
- Menu "Retornos" abre `/admin/crm/followup/?done__exact=0`.
- Limite de destaques segue `MAX_FEATURED`.
- Card mostra o código; imóvel venda+aluguel mostra o preço certo por seção.

## Testes
`apps/properties/tests/test_spec023.py`.

## Tarefas
- [x] Link Retornos
- [x] MAX_FEATURED
- [x] Remover ícones
- [x] Selo de código
- [x] Preço por seção
- [x] Destaques da home
- [x] README/CLAUDE.md, commit
