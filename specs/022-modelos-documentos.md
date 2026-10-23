# 022 — Modelos de documentos (visita, proposta, contrato, recibo)

**Status:** Concluído

## Objetivo
Tirar o retrabalho do corretor: gerar termo de visita, proposta, contratos e recibo já com os dados do cliente, do imóvel e da imobiliária, prontos para imprimir ou salvar em PDF.

## Contexto
Plano em `plans/plano-016-022-novas-funcoes.md` (bloco 022). Fica no app `apps/crm` (módulo `crm`).

## Requisitos
- **`DocumentTemplate`:** nome, tipo (termo de visita, proposta, contrato de locação, contrato de intermediação, recibo), descrição interna, **texto** do modelo e "ativo". Editado no painel.
- **O texto é texto simples** (não HTML) com variáveis do Django: `{{ cliente.nome }}`, `{{ imovel.codigo }}`, `{{ imovel.endereco }}`, `{{ imovel.valor }}`, `{{ imovel.valor_extenso }}`, `{{ imobiliaria.creci }}`, `{{ data }}`, `{{ data_extenso }}`, `{{ corretor.nome }}` e o filtro `valor_por_extenso`. Linha `# Título` vira título; linha em branco separa parágrafos.
- **Segurança:** o modelo é renderizado por um engine de templates **isolado** (só `{% load crm_docs %}` e as tags básicas; sem `include`, `extends` nem `debug`), com um contexto de **dicionários montados à mão** (nunca instâncias de model, para o texto editado no painel não alcançar atributos internos). Todo o resultado é escapado (nada de HTML/JS vindo do modelo ou dos dados). Modelo com erro de sintaxe ou tag proibida não salva.
- Filtro `valor_por_extenso` (`apps/crm/templatetags/crm_docs.py`): `1500` → "mil e quinhentos reais", `1000000` → "um milhão de reais", `12.45` → "doze reais e quarenta e cinco centavos".
- **`GeneratedDocument`:** guarda o texto final, o modelo usado, o cliente, o imóvel, quem gerou e quando (histórico; só leitura no painel).
- **Gerar:** botão "Gerar documento" na ficha e na lista do imóvel e do cliente (e em "Documentos gerados → Gerar"). Página com modelo + cliente + imóvel (o que veio do botão já vem escolhido). Gera e abre a **página de impressão A4** (logo, nome, CRECI e CNPJ de `SiteSettings`; botão "Imprimir / Salvar PDF" usa o navegador, sem WeasyPrint).
- Corretor: só escolhe os próprios clientes/imóveis e só vê os documentos que gerou.
- **Papéis:** Administrador e Gerente: tudo. Corretor e Atendente: ver modelos e gerar documentos.
- Achado nos testes: o `Context` do Django escapa por padrão; a renderização usa `autoescape=False` e escapa uma vez só em `to_html`. `__atributo` no modelo é recusado já ao salvar.
- Os 5 modelos-base vêm do comando `seed_document_templates` (e do `seed_demo`), idempotente, com o aviso "modelo de exemplo: revise com seu jurídico antes de usar".

## Fora de escopo
PDF no servidor (WeasyPrint), assinatura eletrônica, envio por email/WhatsApp, editor visual do modelo.

## Modelo de dados
`crm.DocumentTemplate`, `crm.GeneratedDocument`.

## UI / URLs
Só admin: `admin:crm_generateddocument_new` (gerar) e `admin:crm_generateddocument_print` (impressão), mais as listas.

## Critérios de aceite
- Gerar o recibo/termo de visita de um imóvel abre a página A4 com os dados preenchidos.
- `{% debug %}`, `{% include %}`, `{{ imovel.__class__ }}` e tags `<script>` no modelo não vazam nada nem executam.
- O histórico mostra quem gerou o quê.

## Testes
`apps/crm/tests/test_spec022.py`.

## Tarefas
- [x] `valor_por_extenso`
- [x] Models + migration
- [x] Renderização isolada + contexto de dicionários
- [x] Admin: modelos, histórico, gerar e imprimir; botões no imóvel e no cliente
- [x] Modelos-base + comando + seed
- [x] Sidebar e papéis
- [x] Testes
- [x] README / CLAUDE.md
