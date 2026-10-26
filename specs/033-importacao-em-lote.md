# 033 — Importação em lote

**Status:** Concluído

## Objetivo
Subir todo o estoque de um cliente de uma vez (dados + fotos) por planilha + ZIP ou por XML de portal, com prévia e sem depender de worker. Detalhes no plano `plans/2026-10-26-correcoes-admin.md`.

## Requisitos
1. Tela "Importar imóveis" (Imóveis; Administrador e Gerente) com `ImportJob` (arquivo, origem, situação, contadores, erros por linha).
2. **Planilha + ZIP:** modelo XLSX para baixar; também lê CSV. ZIP com uma pasta por `ref_externa` ou os nomes/URLs citados na coluna `fotos`. O ZIP é lido em memória (nada é extraído em disco).
3. **XML VivaReal/ZAP (VRSync):** arquivo ou URL do feed (download seguro: IP público, até 50 MB); fotos baixadas das URLs; tabela tipo do portal → categoria (sugestões automáticas; o que faltar é pedido; "ignorar" pula esses imóveis). `defusedxml` bloqueia entidades.
4. Fluxo: enviar → (mapear tipos) → prévia (novos / atualizados / com erro) → confirmar → processamento em lotes (20 linhas ou 20 s) por HTMX ("Importando 40/200…"), sem worker; botão "Continuar" funciona sem JS.
5. Linhas com erro são ignoradas e listadas; foto ausente ou inválida é só aviso. Reimportar a mesma `ref_externa` atualiza; as fotos só entram quando o imóvel ainda não tem nenhuma.
6. `manage.py import_properties <arquivo> [--zip f.zip] [--map TIPO=CATEGORIA] [--dry-run]` para cargas grandes.
7. Reusa `services.upsert_property`/`add_photo` (spec 032) e o histórico (`source="Importação #N"`, uma linha de fotos por imóvel).

## Fora de escopo
Importar corretor/proprietário/parceiro; outros formatos de portal; processamento em background (fila).

## Modelo de dados
Migration `properties/0019_importjob`. Dependências: `openpyxl`, `defusedxml`.

## Critérios de aceite
Ver "Verificação → 033" do plano.

## Testes
`apps/properties/tests/test_spec033.py`: leitura (planilha, CSV, XML, ZIP), prévia, importação, reimportação, lotes, avisos de foto, segurança (XML/URL), painel (fluxo, permissões, modelo) e comando.

## Tarefas
- [x] Dependências e `ImportJob`
- [x] Parsers (planilha/CSV, XML VRSync, ZIP) e validação
- [x] Orquestração em lotes
- [x] Painel (upload, mapeamento, prévia, progresso) e sidebar
- [x] Comando `import_properties`
- [x] Testes, README, CLAUDE.md
