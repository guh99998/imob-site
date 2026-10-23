# 019 — Detecção de imóveis duplicados

**Status:** Concluído

## Objetivo
Manter o estoque limpo: avisar o corretor quando um imóvel cadastrado parece repetir outro e permitir varrer o estoque antigo.

## Contexto
Plano em `plans/plano-016-022-novas-funcoes.md` (bloco 019).

## Requisitos
- `apps/properties/duplicates.py` com `find_duplicates(prop)` que devolve `[(imóvel, nível)]`, com dois níveis:
  1. **Forte:** mesmo CEP (com ou sem hífen) + mesmo número + mesmo complemento, normalizados (sem acento, caixa ou pontuação; "Apto", "Ap." e "Apartamento" valem o mesmo). Exige CEP e número preenchidos.
  2. **Provável:** mesmo bairro e categoria, mesmos quartos, `area_total` com diferença de até 5% e preço com diferença de até 10% (compara venda com venda e aluguel com aluguel; sem preço ou sem área não casa).
- Um par que bate nos dois níveis aparece só como forte.
- Candidatos são imóveis que ainda estão no estoque (rascunho, publicado ou reservado). Vendido e alugado ficam de fora: reanunciar um imóvel já negociado é normal.
- Pares marcados como "não duplicado" (`DuplicateDismissal`) nunca mais aparecem.
- `Property.duplicate_hint` (booleano, só leitura) guarda se há duplicado possível, para a lista do painel não ficar lenta. É recalculado ao salvar no painel (nos dois imóveis do par), pela ação e pelo comando.
- **Painel:**
  - Ao salvar, aviso (`messages.warning`) com os links dos possíveis duplicados e o nível. Não bloqueia. Para o Corretor (que só vê os próprios imóveis) o aviso não mostra dados de imóveis de outros: só diz que pode haver um imóvel parecido já cadastrado.
  - Coluna com ícone e filtro "Possível duplicado" na pesquisa avançada.
  - Ação "Marcar como não duplicado" (exige permissão de editar imóvel): dispensa os pares atuais dos selecionados e recalcula.
- `manage.py find_duplicates`: recalcula todo o estoque e lista os pares (forte primeiro). `--quiet` só mostra o total.

## Fora de escopo
Mesclar dois imóveis, bloquear o salvamento, comparar fotos.

## Modelo de dados
- `Property.duplicate_hint` (`BooleanField`, default False, não editável).
- `DuplicateDismissal(property_a, property_b, created_by, created_at)`: par ordenado por id (`a < b`), único.

## UI / URLs
Sem URLs novas.

## Critérios de aceite
- Cadastrar um imóvel com o mesmo CEP e número de outro mostra o aviso com o link.
- "Apto 12" e "apto. 12", e CEP com e sem hífen, contam como iguais.
- Depois de "Marcar como não duplicado", o aviso e o ícone somem para o par.

## Testes
`apps/properties/tests/test_spec019.py`.

## Tarefas
- [x] Models + migration
- [x] `duplicates.py` (normalização, `find_duplicates`, `refresh_hints`, dispensar)
- [x] Admin: aviso, coluna, filtro e ação
- [x] Comando `find_duplicates`
- [x] Testes
- [x] README / CLAUDE.md
