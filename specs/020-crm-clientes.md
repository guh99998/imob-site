# 020 — CRM de clientes

**Status:** Concluído

## Objetivo
Tudo o que chega pelo site (mensagem de imóvel, contato, "Anuncie", "Procuro um imóvel") vira um **cliente** com histórico, corretor responsável, etapa do funil e retornos agendados.

## Contexto
Plano em `plans/plano-016-022-novas-funcoes.md` (bloco 020). Novo app `apps/crm`, módulo opcional `FEATURES=crm` (ligado por padrão). A regra de casamento fica em `apps/crm/services.py` (e não em `apps/leads/services.py`, como o plano previa) para a API (021) reaproveitar sem ciclo de imports.

## Requisitos
- **`Client`:** nome, WhatsApp, email, origem (site, procuro, anuncie, indicação, portal, API, outro), corretor responsável (`people.Broker`), etapa do funil (novo → em atendimento → visita agendada → proposta → fechado | perdido), interesse (finalidade e faixa de preço), etiquetas (texto separado por vírgula), observações, consentimento LGPD (com data), `anonymized_at`, auditoria (criado/alterado por).
- `phone_key`: telefone normalizado (só dígitos, sem o 55), calculado ao salvar, **único** quando preenchido. WhatsApp repetido no painel dá erro de validação no campo.
- **`Interaction`** (linha do tempo, inline no cliente): tipo (ligação, WhatsApp, email, visita, anotação), data, imóvel opcional, texto, autor (preenchido com o usuário logado).
- **`FollowUp`** (retorno): data, observação, corretor, "feito" (+ data). Inline no cliente e lista própria no painel, com filtros e a ação "Marcar como feito".
- **Captação automática** (`get_or_create_client`): casa por WhatsApp normalizado e, se não achar, por email (sem diferenciar caixa). Se achou, só completa o que faltava; se não, cria. Cliente anonimizado não casa. Cada mensagem/procura vira uma "anotação" na linha do tempo do cliente. O corretor do imóvel (se houver) vira o responsável de um cliente novo. Falha no CRM nunca perde o contato do site (o erro é logado).
- `Lead` e `PropertySearch` ganham `client` (FK, não editável); a lista do painel mostra o cliente.
- **Escopo por corretor:** o Corretor vê só clientes e retornos dos seus (responsável ou criador), com `ScopedByRoleMixin`. Novo cliente criado por ele já fica no nome dele.
- **Papéis:** Administrador e Gerente: tudo. Corretor e Atendente: ver/criar/editar cliente, interação e retorno (sem excluir cliente).
- **Painel:** sidebar "Clientes" (Clientes, Retornos com selo de atrasados); filtros por etapa, corretor, origem, finalidade e data; ações em massa para mudar a etapa e "Atribuir a mim"; botão "Ver imóveis compatíveis" (mesma ideia de `PropertySearch.matching_query`) na lista e na página do cliente.
- **Dashboard:** números "Retornos hoje" e "Retornos atrasados" e um quadro com os próximos retornos.
- **LGPD:** ação "Anonimizar cliente" (exige permissão de excluir): apaga nome, contatos, etiquetas, observações e texto das interações do cliente e os dados pessoais dos contatos e procuras ligados a ele.
- `seed_demo` cria 3 clientes de exemplo com histórico e retornos.

## Fora de escopo
Importar planilha de clientes, funil visual (kanban), e-mail/WhatsApp automático, API (021), documentos (022).

## Modelo de dados
`crm.Client`, `crm.Interaction`, `crm.FollowUp`; `leads.Lead.client` e `leads.PropertySearch.client`.

## UI / URLs
Só admin: `admin:crm_client_*`, `admin:crm_followup_*`. Sem URLs públicas novas.

## Critérios de aceite
- Enviar o formulário de um imóvel cria o cliente; enviar de novo com o mesmo WhatsApp (formatado diferente) ou o mesmo email reaproveita o cliente.
- Corretor só vê os próprios clientes.
- Retorno vencido aparece no dashboard e no selo da sidebar.
- Anonimizar remove todos os dados pessoais do cliente e dos contatos ligados.

## Testes
`apps/crm/tests/test_spec020.py`.

## Tarefas
- [x] App `crm`: models + migrations (e FKs em leads)
- [x] `services.py` (normalização, casamento, captação, anonimização)
- [x] Ligar nas views públicas de leads
- [x] Admin de clientes e retornos (inlines, filtros, ações)
- [x] Sidebar, papéis e dashboard
- [x] seed_demo
- [x] Testes
- [x] README / CLAUDE.md
