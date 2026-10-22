# 015 — Ajustes da revisão: paleta, busca, captação e painel

**Status:** Concluído

## Objetivo
Aplicar a revisão das specs 011–014: identidade visual do desenvolvedorgustavolopes.com.br, busca mais completa na home e atalhos no painel.

## Requisitos
- Paleta do site principal (fundo `#fafafa`, superfície `#fff`, linha `#e4e4e7`, texto `#18181b`, secundário `#71717a`, destaque `#6d28d9`, destaque claro `#f5f3ff`) no site e no painel (Unfold `primary` roxo). Tokens semânticos em `frontend/source.css` (bg, surface, fg, muted, accent, accent-soft, line, danger).
- Header branco com "Procuro um imóvel" no menu.
- Home: faixa "Quer vender ou alugar" clara com o formulário de anúncio (Lead `LISTING`), separada do rodapé escuro.
- Hero: tipo, cidade, bairro, quartos, preço mín./máx. (aceita `R$ 1.234,56`) e busca por código (existe e está no site → abre o imóvel; senão aviso na lista).
- "Procuro um imóvel" enxuto: nome, WhatsApp, comprar/alugar, tipo, cidade, valor até, mensagem, LGPD.
- Destaques: limite 3 (padrão, validação e data migration); 3 cards iguais na home.
- Admin: fotos em lote no imóvel (aba "Enviar fotos"); "Ver imóveis" em corretores/parceiros/proprietários (lista do painel filtrada).

### Revisão 2
- Admin: filtros em "Pesquisa avançada" (grade abaixo da busca, abre sozinha com filtro ativo, "Limpar filtros"); sem o botão/gaveta "Filters". `AdvancedSearchMixin` em `apps/core/admin_filters.py` (Unfold `contrib.filters`, horizontais).
- Logo de exemplo (`demo/logo.png`) carregado pelo `seed_demo`; no rodapé escuro fica sobre fundo branco.
- `seed_demo` cria 36 imóveis (24 gerados) → 3 páginas de 12; paginação numerada (`get_elided_page_range`); `select_related("category")` remove N+1 na lista/home.
- "Procuro um imóvel": coluna lateral (foto + nº de imóveis, como funciona, contato).
- `suggest_prefix` nunca esgota (cai para qualquer par AA–ZZ livre).

## Critérios de aceite
- Sem scroll horizontal em 390/1024/1440 (home, procuro, lista).
- Código existente redireciona; vendido/alugado não.
- Upload de várias fotos cria as fotos em ordem, a primeira vira capa se não houver.

## Tarefas
- [x] Paleta (site + painel) e header
- [x] Home: hero, destaques, faixa de anúncio
- [x] Formulário "Procuro um imóvel" enxuto
- [x] Fotos em lote e "Ver imóveis"
- [x] Testes, seed, lint
- [x] Revisão 2: pesquisa avançada no admin, logo, paginação, página Procuro
