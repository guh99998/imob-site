# 018 — Buscas populares na home

**Status:** Concluído

## Objetivo
Ajudar o visitante a navegar pelo que os outros mais procuram ("Mais procurados" na home) e dar à imobiliária um dado de demanda no painel.

## Contexto
Plano em `plans/plano-016-022-novas-funcoes.md` (bloco 018).

## Requisitos
- Model `SearchQuery` (`apps/properties`): `key` (querystring normalizada e ordenada, única), `label` (texto legível), `count`, `results` (nº de imóveis na última vez), `last_searched_at`.
- Registro em `property_list` (também nas landings), só quando: o formulário é válido, há ao menos um filtro conhecido (ordenação e `page` não contam), é a página 1 e o user-agent não é de robô. A busca por código (`?code=`) não conta. Nada pessoal é guardado (sem IP, sem user-agent).
- A chave usa só os filtros conhecidos de `PropertyFilter`, com valores normalizados (preço `R$ 1.000` e `1000` viram a mesma chave; categoria por slug; cidade e bairro por id).
- O rótulo é montado a partir da busca: "Casa à venda em Vila Nova · 3+ quartos · até R$ 500.000".
- Contagem com `F("count") + 1` (sem corrida entre requisições).
- Home: seção "Mais procurados" entre categorias e "Onde estamos", com até 6 chips que levam à busca. Entram buscas dos últimos 30 dias, com `count >= 3` e `results > 0`, por `count`. Sem dados, a seção não aparece.
- `seed_demo` cria 4 buscas de exemplo para a seção aparecer na demo.
- Painel: lista só leitura (sem adicionar/editar; excluir só para quem tem a permissão) em "Contatos → Buscas no site", ordenada por `count`, com busca por rótulo.

## Fora de escopo
Sugestões de busca ao digitar, analytics por período, gráfico no dashboard.

## Modelo de dados
`SearchQuery(key CharField(300, unique), label CharField(200), count PositiveIntegerField, results PositiveIntegerField, last_searched_at DateTimeField)`.

## UI / URLs
Sem URLs novas. Os chips usam `properties:list` + a chave.

## Critérios de aceite
- Buscar com filtros 3 vezes faz o chip aparecer na home; a mesma busca com a ordem dos parâmetros trocada soma na mesma linha.
- Robôs, páginas 2+, buscas só com ordenação e busca por código não são registrados.
- Busca sem resultados não vira chip.

## Testes
`apps/properties/tests/test_spec018.py`.

## Tarefas
- [x] Model + migration
- [x] `apps/properties/searches.py` (chave, rótulo, robôs, registro)
- [x] Hook em `property_list`
- [x] Home: seção "Mais procurados"
- [x] Admin só leitura + sidebar
- [x] Testes
- [x] README / CLAUDE.md
