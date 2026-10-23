# 021 — API aberta do CRM

**Status:** Concluído

## Objetivo
Deixar portais, landing pages, Zapier/Make e outros sistemas conversarem com o site: enviar contatos, consultar e atualizar clientes e ler os imóveis publicados.

## Contexto
Plano em `plans/plano-016-022-novas-funcoes.md` (bloco 021). Novo app `apps/api`, módulo opcional `FEATURES=api` (**desligado por padrão**: é uma superfície nova exposta à internet). Reaproveita a captação do CRM (`apps/crm/services.py`).

## Requisitos
- Dependências: `djangorestframework` e `drf-spectacular` (documentação OpenAPI).
- **`ApiKey`** (painel, só Administrador): nome da integração, permissão (`LEADS`: só enviar contatos; `FULL`: contatos, clientes e imóveis), origem dos clientes que ela cria, ativa, último uso. A chave (`imob_…`) aparece **uma única vez**, na criação; no banco fica só o hash (SHA-256) e o prefixo (12 caracteres) para identificar. Desativar a chave bloqueia na hora.
- **Autenticação:** header `Authorization: Api-Key <chave>`. Sem chave ou chave inválida/inativa: 401. Chave `LEADS` em rota de clientes: 403. Módulo desligado: 404 em tudo (inclusive a documentação).
- **Throttling por chave** (`API_THROTTLE_RATE`, padrão `120/min`); excedeu: 429.
- Só JSON (ou formulário) na entrada; paginação de 25 por página (`page_size` até 100).
- **Endpoints em `/api/v1/`:**
  - `POST /leads/` (qualquer chave): `name`, `message`, `email` e/ou `phone` (um dos dois), `property` (código, opcional), `kind` (`PROPERTY`, `CONTACT`, `LISTING`). Cria o contato (caixa de entrada do painel, com aviso por email) e passa pelo mesmo `get_or_create_client` do site: sem duplicar cliente. Resposta 201 com `id` e `client`.
  - `GET /clients/` (filtros `stage`, `source`, `q`), `GET/PATCH /clients/{id}/`: só `FULL`. Cliente anonimizado não aparece. WhatsApp repetido é rejeitado sem revelar de quem é.
  - `GET/POST /clients/{id}/interactions/`: só `FULL`.
  - `GET /properties/` e `GET /properties/{codigo}/` (qualquer chave): só `published()`, com os mesmos filtros da busca do site; respeita "mostrar endereço".
- Efeito colateral aceito: com `rest_framework` instalado, a tradução do DRF vale para o site todo (ex.: o erro de email do formulário público passou a ser "Insira um endereço de email válido").
- `/api/docs/` (Swagger) e `/api/schema/` (OpenAPI) descrevem tudo, incluindo o esquema da chave.

## Fora de escopo
Webhooks de saída, OAuth, escopo por corretor na API, escrita de imóveis, upload de fotos.

## Modelo de dados
`api.ApiKey(name, prefix único, key_hash, permission, source, is_active, last_used_at, created_by, created_at)`.

## UI / URLs
`/api/v1/…`, `/api/docs/`, `/api/schema/`; painel em "Configurações → Chaves de API".

## Critérios de aceite
- `curl -X POST /api/v1/leads/ -H "Authorization: Api-Key …"` cria o contato e o cliente; repetir com o mesmo telefone reaproveita o cliente.
- Chave inválida ou desativada recebe 401; `/api/docs/` abre.
- A chave completa não é recuperável depois da criação.

## Testes
`apps/api/tests/test_spec021.py`.

## Tarefas
- [x] Dependências + settings (DRF, spectacular, throttle)
- [x] `ApiKey` + autenticação + permissões + throttle
- [x] Endpoints (leads, clients, interactions, properties) + docs
- [x] Admin das chaves + sidebar + papéis
- [x] Testes
- [x] README / CLAUDE.md / `.env.example`
