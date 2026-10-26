# 035 — Ajustes do painel (feedback de uso)

**Status:** Concluído

## Objetivo
Pedidos feitos ao revisar o painel pronto: página do imóvel só para leitura até editar, documento editável antes de imprimir, listas de caixas em colunas, usuário sem detalhes técnicos de senha e itens de implantação fora do alcance do cliente.

## Requisitos
1. **Página do imóvel em modo visualização:** campos travados e rodapé de salvar escondido até clicar em "Editar informações" (`?editar=1`); "Salvar e continuar editando" e erro de validação voltam em edição; abas continuam funcionando; sem JS fica editável; só aparece para quem pode alterar.
2. **Documento editável antes de imprimir:** na página de impressão, "Editar texto" libera o texto (ex.: valor do recibo), "Salvar alterações" grava e "Restaurar original" volta ao texto do modelo. O texto editado passa por `documents.to_html` (nada de HTML livre). Guarda `original_html` e `edited_at`; histórico mostra "Editado". Só quem pode gerar documentos; corretor só edita os próprios.
3. **Usuário:** o campo senha vira só o botão "Redefinir senha" (sem algoritmo/iterações).
4. **Checklists em colunas:** comodidades do imóvel, grupos e permissões do usuário viram caixas de seleção em várias colunas (`checklists.css`); permissões com rótulo curto em português ("Cliente: Ver").
5. **Fora do cliente:** "Importar imóveis" sai do menu (a importação é feita na implantação, por comando ou pela URL) e "Chaves de API" sai do menu e do Administrador (só superusuário gera chaves).

## Fora de escopo
Modo visualização para outros cadastros (clientes, proprietários…); edição visual rica (negrito, tabelas) do documento.

## Modelo de dados
Migration `crm/0004_document_editing` (`original_html`, `edited_at`). As permissões `api` saem do grupo Administrador no próximo `migrate`.

## Testes
`apps/crm/tests/test_spec035.py`, `apps/core/tests/test_spec034.py` (senha, checklists), `apps/api/tests/test_spec021.py` (chaves só do superusuário), `apps/properties/tests/test_spec033.py` (sem item de importação no menu) e verificação no Chromium (modo visualização, edição e restauração do documento).

## Tarefas
- [x] Modo visualização da página do imóvel
- [x] Edição, salvamento e restauração do documento
- [x] Botão de redefinir senha
- [x] Checklists em colunas (comodidades e permissões)
- [x] Importação e chaves de API fora do menu do cliente
- [x] Testes, README, CLAUDE.md
