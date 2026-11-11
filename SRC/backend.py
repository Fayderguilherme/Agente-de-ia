import json
import logging
import os
import re
import sqlite3
import webbrowser
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


LOGGER = logging.getLogger(__name__)
MAX_TASK_LENGTH = 500
MAX_REQUEST_BODY = 4096
TASKS_PATH = "/api/tasks"


class TaskStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.initialize()

    def initialize(self) -> None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        text TEXT NOT NULL,
                        created_at TEXT NOT NULL
                            DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
                    )
                    """
                )

    def list_tasks(self) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT id, text, created_at FROM tasks ORDER BY id"
            ).fetchall()
        return [dict(row) for row in rows]

    def create_task(self, text: str) -> dict[str, Any]:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            with connection:
                cursor = connection.execute(
                    "INSERT INTO tasks (text) VALUES (?)",
                    (text,),
                )
                if cursor.lastrowid is None:
                    raise sqlite3.DatabaseError("Não foi possível criar a tarefa.")
                row = connection.execute(
                    "SELECT id, text, created_at FROM tasks WHERE id = ?",
                    (cursor.lastrowid,),
                ).fetchone()
        if row is None:
            raise sqlite3.DatabaseError("Não foi possível recuperar a tarefa criada.")
        return dict(row)

    def delete_task(self, task_id: int) -> bool:
        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                cursor = connection.execute(
                    "DELETE FROM tasks WHERE id = ?",
                    (task_id,),
                )
                return cursor.rowcount > 0


def create_handler(store: TaskStore) -> type[BaseHTTPRequestHandler]:
    frontend_files = {
        "/": ("index.html", "text/html; charset=utf-8"),
        "/index.html": ("index.html", "text/html; charset=utf-8"),
        "/app.js": ("app.js", "text/javascript; charset=utf-8"),
        "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    }
    frontend_directory = Path(__file__).resolve().parent

    class TaskRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path in frontend_files:
                filename, content_type = frontend_files[path]
                try:
                    body = (frontend_directory / filename).read_bytes()
                except OSError:
                    LOGGER.exception("Falha ao carregar recurso da interface.")
                    self._send_json(500, {"error": "Erro interno do servidor."})
                    return
                self._send_bytes(200, body, content_type)
                return

            if path != TASKS_PATH:
                self._send_json(404, {"error": "Rota não encontrada."})
                return

            try:
                self._send_json(200, store.list_tasks())
            except sqlite3.Error:
                LOGGER.exception("Falha ao listar tarefas.")
                self._send_json(500, {"error": "Erro interno do servidor."})

        def do_POST(self) -> None:
            if urlsplit(self.path).path != TASKS_PATH:
                self._send_json(404, {"error": "Rota não encontrada."})
                return

            content_type = self.headers.get("Content-Type", "")
            if content_type.split(";", 1)[0].strip().lower() != "application/json":
                self._send_json(415, {"error": "O conteúdo deve ser enviado como JSON."})
                return

            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                self._send_json(411, {"error": "Informe o tamanho do conteúdo enviado."})
                return
            try:
                body_length = int(raw_length)
            except ValueError:
                self._send_json(400, {"error": "Tamanho do conteúdo inválido."})
                return
            if body_length < 0:
                self._send_json(400, {"error": "Tamanho do conteúdo inválido."})
                return
            if body_length > MAX_REQUEST_BODY:
                self._send_json(413, {"error": "Conteúdo enviado muito grande."})
                return

            body = self.rfile.read(body_length)
            if len(body) != body_length:
                self._send_json(400, {"error": "Conteúdo enviado incompleto."})
                return
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(400, {"error": "JSON inválido."})
                return
            if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
                self._send_json(400, {"error": "Informe o texto da tarefa."})
                return

            text = payload["text"].strip()
            if not text:
                self._send_json(400, {"error": "O texto da tarefa não pode ficar vazio."})
                return
            if len(text) > MAX_TASK_LENGTH:
                self._send_json(
                    400,
                    {"error": f"O texto deve ter no máximo {MAX_TASK_LENGTH} caracteres."},
                )
                return

            try:
                self._send_json(201, store.create_task(text))
            except sqlite3.Error:
                LOGGER.exception("Falha ao criar tarefa.")
                self._send_json(500, {"error": "Erro interno do servidor."})

        def do_DELETE(self) -> None:
            path = urlsplit(self.path).path
            if not path.startswith(f"{TASKS_PATH}/"):
                self._send_json(404, {"error": "Rota não encontrada."})
                return

            task_id_text = path[len(TASKS_PATH) + 1 :]
            if (
                re.fullmatch(r"[1-9][0-9]*", task_id_text) is None
                or len(task_id_text) > 19
            ):
                self._send_json(400, {"error": "Identificador da tarefa inválido."})
                return

            task_id = int(task_id_text)
            if task_id > 2**63 - 1:
                self._send_json(400, {"error": "Identificador da tarefa inválido."})
                return

            try:
                deleted = store.delete_task(task_id)
            except sqlite3.Error:
                LOGGER.exception("Falha ao excluir tarefa.")
                self._send_json(500, {"error": "Erro interno do servidor."})
                return

            if not deleted:
                self._send_json(404, {"error": "Tarefa não encontrada."})
                return
            self._send_empty(204)

        def send_error(
            self,
            code: int,
            message: str | None = None,
            explain: str | None = None,
        ) -> None:
            del message, explain
            self._send_json(code, {"error": "Método HTTP não suportado."})

        def _send_json(self, status: int, payload: Any) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send_bytes(status, body, "application/json; charset=utf-8")

        def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "connect-src 'self'; object-src 'none'; base-uri 'self'; "
                "frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

        def _send_empty(self, status: int) -> None:
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "connect-src 'self'; object-src 'none'; base-uri 'self'; "
                "frame-ancestors 'none'",
            )
            self.end_headers()

    return TaskRequestHandler


def create_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    database_path: str | Path | None = None,
) -> ThreadingHTTPServer:
    if database_path is None:
        database_path = Path(__file__).with_name("tasks.sqlite3")
    store = TaskStore(database_path)
    return ThreadingHTTPServer((host, port), create_handler(store))


def main() -> None:
    host = os.environ.get("TODO_HOST", "127.0.0.1")
    port = int(os.environ.get("TODO_PORT", "8000"))
    database_path = os.environ.get(
        "TODO_DB_PATH",
        str(Path(__file__).with_name("tasks.sqlite3")),
    )
    server = create_server(host, port, database_path)
    browser_host = "127.0.0.1" if host in ("", "0.0.0.0") else host
    app_url = f"http://{browser_host}:{server.server_port}/"
    LOGGER.info("Aplicação disponível em %s", app_url)
    webbrowser.open(app_url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Servidor encerrado.")
    finally:
        server.server_close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
