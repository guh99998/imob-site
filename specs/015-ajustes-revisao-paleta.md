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
