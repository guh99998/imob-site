# 011 — Ajustes do site público

**Status:** Concluído

## Objetivo
Levar o site público a um estado entregável: responsivo de verdade, legível, sem imóveis vendidos/alugados, com SEO e performance básicos.

## Contexto
Revisão da spec 010 (`plans/plano-011-014-ajustes-mvp.md`). Primeira de quatro specs (011–014).

## Requisitos
- `ref.md` sai do repositório e vai para o `.gitignore`.
- `Property.objects.published()` = `PUBLISHED` + `RESERVED` (vendido/alugado somem do site, continuam no painel).
- Limite de destaques: `SiteSettings.max_featured` (padrão 6), validado em `Property.clean()` e na ação "Destacar".
- Header com menu hambúrguer (`<details>` sem JS), itens Comprar · Alugar · Anuncie seu imóvel · Contato e CTA WhatsApp com ícone.
- Hero: vídeo sem botão de pausar; `prefers-reduced-motion` mostra só o poster (CSS).
- Cards de mesma altura (flex, título com 2 linhas, ficha no rodapé).
- Fonte única legível: Inter (variável, self-host), números tabulares.
- `SiteSettings`: `logo`, `creci`, `cnpj`, `about`, `meta_description`; logo + CRECI no header/footer.
- WhatsApp de exemplo fictício (`5511900000000`).
- Novas categorias (data migration) e filtro agrupado por `optgroup`.
- Galeria: carrossel com snap + contador + setas no mobile; lightbox com setas, teclado e swipe.
- Footer em colunas alimentado por context processor.
- SEO: landings `/comprar/<categoria>/`, `/alugar/<categoria>/`, `/comprar/<categoria>/<cidade>/`; canonical; noindex em filtros/paginação; og:image com fallback; Twitter cards; JSON-LD; sitemap ampliado; robots.txt; política de privacidade.
- Performance: htmx e fonte self-host, miniaturas WebP com `srcset`, `width`/`height`/`loading`/`decoding`.

## Fora de escopo
Páginas Anuncie/Contato com formulário (spec 014; aqui os links apontam para âncoras/páginas simples), Playwright/Lighthouse automatizados em CI.

## Modelo de dados
- `core.SiteSettings`: `logo`, `creci`, `cnpj`, `about`, `meta_description`, `max_featured`.
- `properties.PropertyPhoto`: `thumb_sm`, `thumb_lg` (ImageField, WebP).
- Migration de dados `properties.0006` (categorias).

## UI / URLs
`/comprar/<cat>/`, `/alugar/<cat>/`, `/comprar/<cat>/<cidade>/`, `/politica-de-privacidade/`, `/robots.txt`, `/sitemap.xml`.

## Critérios de aceite
- Vendido/alugado ausentes de lista, home, sitemap; detalhe 404.
- Sem scroll horizontal em 360/390/768/1280 (home, lista, detalhe).
- Cards com mesma altura numa mesma linha.
- Mais destaques que o limite → erro claro no admin.

## Testes
Models (`published`, limite de destaques), views (404 vendido, landings, noindex), sitemap, JSON-LD sem dados internos, seed.

## Tarefas
- [x] Higiene, regras de negócio, SiteSettings, categorias
- [x] Header/menu/hero/cards/fonte
- [x] Galeria e lightbox
- [x] Footer, SEO, landings
- [x] Performance (thumbs, self-host)
- [x] Testes, seed, lint
