# 029 — Polimento do admin

**Status:** Concluído

## Objetivo
Corrigir os problemas de UX encontrados no uso real do painel: textos em inglês, menu sem item selecionado, kanban sem cabeçalho, cadastro de imóvel pouco guiado, nomes confusos de corretor/parceiro e ordenação não alfabética. Detalhes no plano `plans/2026-10-26-correcoes-admin.md`.

## Contexto
django-unfold 0.110 não traz pt-BR; links callable da sidebar viram `str(função)` na comparação de "ativo"; o script de "Copiar link" do detalhe do imóvel está fora do `{% endblock %}`.

## Requisitos
1. Traduções do Unfold em `locale/pt_BR` (`LOCALE_PATHS`), `.po` e `.mo` commitados; Dockerfile roda `compilemessages`.
2. Menu: `active=` explícito em Retornos, Dados da imobiliária, Clientes (exclui kanban) e Funil.
3. Kanban e "novo documento" estendem `admin/base_site.html`; alternância lista/kanban nos dois lados.
4. "Buscas no site" sai do admin; "Procuras de clientes" com lista simplificada e fieldsets.
5. Cadastro de imóvel: placeholders, widget de fotos, comodidades em checkboxes, renomear `source`/`broker`/`partner`, remover caixa "Mensagem para o cliente".
6. Ordem alfabética: remover `Category.order`; `ordering` de Feature, Broker, Partner, Owner, Guarantor, City, Neighborhood e usuários.
7. Site: "Copiar link" funcional; faixa de demonstração por `DEMO_MODE`.

## Fora de escopo
Título do admin dinâmico a partir de "Dados da imobiliária".

## Modelo de dados
Migrations apenas de `verbose_name`/choices e remoção de `Category.order`.

## UI / URLs
Sem URLs novas; partial `templates/admin/crm/client_view_toggle.html`; widget `templates/admin/properties/widgets/bulk_photos.html`.

## Critérios de aceite
Ver seção "Verificação → 029" do plano.

## Testes
`apps/<app>/tests/` com factory-boy: sidebar ativa, ordenação, `DEMO_MODE`, lista de procuras, remoção da caixa de mensagem.

## Tarefas
- [x] `LOCALE_PATHS` e helpers de menu ativo (`path_active`)
- [x] Arquivo `.po`/`.mo` + Dockerfile (`gettext`, `compilemessages`)
- [x] Label vazio "Selecione a categoria"
- [x] Kanban/documento estendendo `base_site.html` + alternância lista/kanban
- [x] Remover `SearchQueryAdmin`; simplificar `PropertySearchAdmin`
- [x] Placeholders, widget de fotos, comodidades em checkboxes
- [x] Renomear `source`/`broker`/`partner` (+ migration)
- [x] Remover "Mensagem para o cliente"
- [x] Remover `Category.order` e ordenar tudo alfabeticamente
- [x] "Copiar link" e faixa `DEMO_MODE`
- [x] `README.md`, `CLAUDE.md`, pytest, ruff
