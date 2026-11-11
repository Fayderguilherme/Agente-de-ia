# To-do simples

Aplicação leve para anotar tarefas e lembretes. A interface em HTML, CSS e JavaScript comunica com uma API HTTP em Python, que valida as solicitações e salva os dados em SQLite.

## Recursos

- Listar tarefas salvas ao abrir a página.
- Criar tarefas com texto obrigatório de até 500 caracteres.
- Excluir tarefas com confirmação.
- Manter as tarefas no banco SQLite depois de fechar ou recarregar a página.
- Exibir estados de carregamento, lista vazia e erros de comunicação.

O texto das tarefas é exibido como texto, não como HTML. A aplicação não tem contas, notificações ou serviços externos.

## Requisitos

- Windows.
- Python 3 instalado, ou o ambiente virtual `.venv` na pasta raiz do projeto.
- Nenhum pacote Python adicional é necessário; o servidor usa a biblioteca padrão.

## Iniciar no Windows

1. Abra a pasta `SRC`.
2. Execute `start.bat` (por exemplo, com dois cliques no Explorador de Arquivos).
3. Aguarde o navegador abrir em <http://127.0.0.1:8000/>.
4. Mantenha a janela do terminal aberta enquanto usa a aplicação. Feche-a ou pressione `Ctrl+C` para parar o servidor.

Não abra `index.html` diretamente como arquivo: a página precisa ser servida pelo back-end para que as chamadas à API funcionem na mesma origem.

Se a porta `8000` já estiver ocupada, encerre o outro servidor ou configure outra porta antes de iniciar. Também é possível iniciar manualmente a partir da pasta raiz:

```powershell
.\.venv\Scripts\python.exe .\SRC\backend.py
```

Se não houver `.venv`, use `python .\SRC\backend.py`, desde que Python esteja no `PATH`.

## Persistência e configuração

Por padrão, o banco de dados é criado em `SRC/tasks.sqlite3`. O arquivo é gerado na primeira inicialização e deve ser mantido para preservar as tarefas.

O servidor aceita estas variáveis de ambiente opcionais:

| Variável | Padrão | Descrição |
|---|---|---|
| `TODO_HOST` | `127.0.0.1` | Endereço de rede do servidor. |
| `TODO_PORT` | `8000` | Porta HTTP. |
| `TODO_DB_PATH` | `SRC/tasks.sqlite3` | Caminho do arquivo SQLite. |

Por padrão, o servidor atende apenas conexões locais neste computador.

## API

Todas as rotas são servidas pelo mesmo endereço da interface e usam JSON quando há corpo ou resposta:

| Método | Rota | Resultado |
|---|---|---|
| `GET` | `/api/tasks` | `200` e uma lista de tarefas. |
| `POST` | `/api/tasks` | Recebe `{"text":"Minha tarefa"}` e responde `201` com a tarefa criada. |
| `DELETE` | `/api/tasks/:id` | Responde `204` sem conteúdo; `404` se a tarefa não existir. |

Cada tarefa contém `id`, `text` e `created_at`. O back-end remove espaços excedentes, recusa texto vazio ou acima de 500 caracteres e valida o identificador antes de excluir.

Exemplo de criação:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/tasks `
  -ContentType "application/json" `
  -Body '{"text":"Revisar o projeto"}'
```

## Testes

Com Python disponível, execute a partir da pasta raiz do projeto:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s SRC -p "test_backend.py" -v
```

Os testes verificam as rotas, a validação, a persistência e o serviço da interface na mesma origem da API.

## Arquivos principais

- `index.html` — estrutura da página.
- `styles.css` — estilos responsivos.
- `app.js` — interação da interface e chamadas à API.
- `backend.py` — servidor HTTP, API e persistência SQLite.
- `start.bat` — inicializador para Windows.
- `test_backend.py` — testes automatizados do back-end e da integração HTTP.
- `Spec.md` — especificação funcional do projeto.
