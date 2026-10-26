# 032 — API de escrita de imóveis

**Status:** Concluído

## Objetivo
Permitir que sistemas externos (ERP, planilhas, scripts) cadastrem e atualizem imóveis e fotos pela API, sem duplicar ao reenviar. Detalhes no plano `plans/2026-10-26-correcoes-admin.md`.

## Requisitos
1. Módulo `api` ligado por padrão (`FEATURES` / `features.ALL`); a API só responde com `Api-Key` e a escrita exige chave de permissão total (`FULL`).
2. `Property.external_ref` (único, opcional, só leitura no painel) para idempotência.
3. `apps/properties/services.py` (compartilhado com a importação, spec 033):
   - `upsert_property(data, instance=None, source)`: categoria por nome/prefixo (não cria), cidade/bairro/comodidades por nome (criam o que falta; cidade nova exige UF), `full_clean`, histórico (`source="API: <chave>"`) e aviso de duplicado (não bloqueia).
   - `add_photo` / `remove_photo`: só JPEG/PNG/WEBP/GIF, até 10 MB; URL só `http(s)`, IP público (recusa loopback/privado/link-local, revalidado a cada redirecionamento, máx. 3), timeout de 10 s.
4. Endpoints: `POST /api/v1/properties/` (201; 200 se o `external_ref` já existe), `PATCH /api/v1/properties/<code>/`, `POST /api/v1/properties/<code>/photos/` (multipart `file` ou JSON `url`), `DELETE /api/v1/properties/<code>/photos/<id>/`. Resposta inclui `created` e `possible_duplicates`.
5. A leitura (`GET`) continua só de imóveis publicados; a resposta de POST/PATCH devolve o imóvel gravado, qualquer que seja a situação.
6. Documentado no drf-spectacular.

## Fora de escopo
Importação em lote (033); criar categorias pela API; corretor/parceiro/proprietário do imóvel; excluir imóvel.

## Modelo de dados
Migration `properties/0018_external_ref`.

## Critérios de aceite
Ver "Verificação → 032" do plano.

## Testes
`apps/api/tests/test_spec032.py`: permissões, criação, validação, idempotência, duplicados, PATCH, upload/URL/SSRF/redirecionamentos, exclusão de foto, schema.

## Tarefas
- [x] `external_ref` e migration
- [x] `services.py` (upsert e fotos com limites)
- [x] Serializers, views e URLs
- [x] Módulo `api` ligado por padrão
- [x] Testes, README, CLAUDE.md
