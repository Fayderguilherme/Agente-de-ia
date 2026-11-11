# Especificação — To-do simples

## 1. Objetivo

Criar uma aplicação leve para anotar tarefas e lembretes, visualizar a lista e excluir itens concluídos ou que não sejam mais necessários.

## 2. Escopo

- Interface simples em HTML e CSS, adaptável a telas pequenas.
- Um campo para escrever uma tarefa ou lembrete e um botão para adicioná-lo.
- Lista dos itens salvos, cada um com opção de exclusão.
- Back-end com rotas para listar, adicionar e excluir itens.
- Persistência leve em SQLite.
- Sem contas de usuário, notificações automáticas ou recursos em tempo real nesta versão.

## 3. Arquitetura

O navegador apresenta a interface e usa JavaScript simples (`fetch`) para chamar a API. O back-end valida as solicitações, acessa o banco SQLite e devolve respostas em JSON. O front-end atualiza a lista com os dados recebidos.

```text
HTML, CSS e JavaScript → API HTTP → SQLite
```

## 4. Funcionalidades

1. Ao abrir a página, carregar e exibir as tarefas salvas.
2. Permitir adicionar uma tarefa ou lembrete com texto obrigatório.
3. Atualizar a lista após uma adição bem-sucedida.
4. Permitir excluir cada item individualmente, pedindo confirmação antes da exclusão.
5. Exibir mensagens claras quando uma ação falhar ou a lista estiver vazia.

Os lembretes desta versão são anotações em texto; não enviam alertas nem notificações.

## 5. API do back-end

Todas as rotas usam o prefixo `/api/tasks` e trocam dados em JSON.

| Método e rota | Ação | Resposta esperada |
|---|---|---|
| `GET /api/tasks` | Lista os itens salvos. | `200` e uma lista JSON. |
| `POST /api/tasks` | Adiciona um item. Recebe `{"text":"..."}`. | `201` e o item criado. |
| `DELETE /api/tasks/:id` | Exclui o item identificado. | `204` sem conteúdo; `404` se não existir. |

Cada item contém `id`, `text` e `created_at`. Erros devem retornar um status HTTP apropriado e uma mensagem JSON simples, sem expor detalhes internos do servidor.

## 6. Interface

- Usar HTML semântico e CSS próprio, sem frameworks ou bibliotecas pesadas.
- Manter uma página única com título, campo de texto, botão “Adicionar” e lista.
- Mostrar o texto da tarefa e um botão “Excluir” em cada item.
- Desabilitar o envio quando o campo estiver vazio e apresentar estados de carregamento e erro de forma simples.
- Usar JavaScript apenas para validar o formulário, chamar a API e atualizar a lista.

## 7. Regras de validação e segurança

- Remover espaços excedentes e rejeitar texto vazio.
- Definir um limite de tamanho para o texto (por exemplo, 500 caracteres) no front-end e validar novamente no back-end.
- Tratar o texto como conteúdo, nunca como HTML: inserir na página com APIs seguras do DOM, como `textContent`.
- Usar consultas parametrizadas no SQLite.
- Validar o formato do identificador recebido pela rota de exclusão.
- Em produção, usar HTTPS; não incluir senhas, chaves ou outros segredos no código.
- Restringir CORS à origem do front-end quando front-end e API estiverem em origens diferentes; não liberar qualquer origem sem necessidade.
- Não confiar em validações feitas somente pelo navegador: o back-end é responsável pela validação final.

## 8. Comunicação e erros

- O front-end envia e recebe JSON com `Content-Type: application/json` nas solicitações com corpo.
- Após adicionar ou excluir, atualizar a lista somente quando a API confirmar o sucesso.
- Se a API estiver indisponível, manter a página utilizável, informar o problema e permitir tentar novamente.
- Não exibir mensagens de sucesso quando a operação falhar.

## 9. Critérios de aceite

- É possível criar uma tarefa com texto válido e vê-la na lista.
- Itens continuam disponíveis após recarregar a página.
- É possível excluir um item, e ele deixa de aparecer na lista.
- Texto vazio ou acima do limite é recusado pelo back-end.
- Conteúdo digitado é exibido como texto, sem executar marcação ou scripts.
- A interface informa falhas de comunicação sem apresentar detalhes internos.