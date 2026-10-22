# 016 — Ganhos rápidos no imóvel e no rodapé

**Status:** Concluído

## Objetivo
Reduzir o atrito até o contato e facilitar a divulgação: WhatsApp com mensagem pronta, botão compartilhar, texto pronto para o corretor e crédito do desenvolvedor no rodapé.

## Contexto
Plano em `plans/plano-016-022-novas-funcoes.md` (bloco 016).

## Requisitos
- `SiteSettings.whatsapp_message`: modelo editável com `{codigo}`, `{titulo}`, `{bairro}`, `{preco}`, `{link}`. Placeholder desconhecido não quebra (fica como está).
- `Property.whatsapp_text(request)` monta o texto; o link usa `?utm_source=whatsapp`.
- Detalhe: botão WhatsApp com o texto pronto; link "Copiar link do imóvel" (URL limpa da página; com JS copia via `clipboard` e avisa "Link copiado"; sem JS é só o link da página).
- Painel (change page do imóvel): caixa "Mensagem para o cliente" com botão "Copiar".
- Ícones: Bootstrap Icons (só whatsapp, instagram, github, share), SVG inline em `templates/partials/icons/`.
- Rodapé: "Desenvolvido por Gustavo Lopes" com Instagram e GitHub (`DEVELOPER_CREDIT` no settings; `None` desliga).

## Fora de escopo
Favoritos (017), buscas populares (018).

## Modelo de dados
`SiteSettings.whatsapp_message` (TextField, com default).

## UI / URLs
Sem URLs novas.

## Critérios de aceite
- O link do WhatsApp no detalhe abre com o texto completo, codificado.
- Compartilhar funciona com e sem JS.
- Crédito aparece no rodapé e some com `DEVELOPER_CREDIT = None`.

## Testes
`apps/properties/tests/test_spec016.py`.

## Tarefas
- [x] Model + migration
- [x] Helper `whatsapp_text` / `share_url`
- [x] Detalhe: WhatsApp + compartilhar
- [x] Painel: mensagem para o cliente
- [x] Rodapé: crédito
- [x] Testes
