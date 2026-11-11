import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from typing import Any

from backend import TaskStore, create_handler


class BackendApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "tasks.sqlite3"
        store = TaskStore(database_path)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(store))
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.start()
        self.connection = http.client.HTTPConnection(*self.server.server_address)

    def tearDown(self) -> None:
        self.connection.close()
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join()
        self.temp_dir.cleanup()

    def request_json(
        self,
        method: str,
        path: str,
        payload: Any = None,
        content_type: str = "application/json",
    ) -> tuple[int, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {}
        if body is not None:
            headers["Content-Type"] = content_type
            headers["Content-Length"] = str(len(body))
        self.connection.request(method, path, body=body, headers=headers)
        response = self.connection.getresponse()
        response_body = response.read()
        if not response_body:
            return response.status, None
        return response.status, json.loads(response_body)

    def test_create_list_and_delete_task(self) -> None:
        status, created = self.request_json(
            "POST",
            "/api/tasks",
            {"text": "  Comprar leite  "},
        )
        self.assertEqual(status, 201)
        self.assertEqual(created["text"], "Comprar leite")
        self.assertIn("id", created)
        self.assertIn("created_at", created)

        status, tasks = self.request_json("GET", "/api/tasks")
        self.assertEqual(status, 200)
        self.assertEqual(tasks, [created])

        status, body = self.request_json("DELETE", f"/api/tasks/{created['id']}")
        self.assertEqual(status, 204)
        self.assertIsNone(body)
        self.assertEqual(self.request_json("GET", "/api/tasks"), (200, []))

    def test_serves_frontend_from_same_origin_as_api(self) -> None:
        for path, expected_type, expected_content in (
            ("/", "text/html", b'<script src="app.js" defer></script>'),
            ("/app.js", "text/javascript", b'const API_URL = "/api/tasks";'),
            ("/styles.css", "text/css", b".task-panel"),
        ):
            with self.subTest(path=path):
                self.connection.request("GET", path)
                response = self.connection.getresponse()
                body = response.read()
                self.assertEqual(response.status, 200)
                self.assertTrue(response.getheader("Content-Type").startswith(expected_type))
                self.assertIn(expected_content, body)
                self.assertEqual(
                    response.getheader("Content-Security-Policy"),
                    "default-src 'self'; script-src 'self'; style-src 'self'; "
                    "connect-src 'self'; object-src 'none'; base-uri 'self'; "
                    "frame-ancestors 'none'",
                )

        self.request_json("POST", "/api/tasks", {"text": "No mesmo servidor"})
        status, tasks = self.request_json("GET", "/api/tasks")
        self.assertEqual(status, 200)
        self.assertEqual([task["text"] for task in tasks], ["No mesmo servidor"])

    def test_tasks_are_persisted_in_database(self) -> None:
        self.request_json("POST", "/api/tasks", {"text": "Persistir"})
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join()

        database_path = Path(self.temp_dir.name) / "tasks.sqlite3"
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            create_handler(TaskStore(database_path)),
        )
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.start()
        self.connection.close()
        self.connection = http.client.HTTPConnection(*self.server.server_address)
        status, tasks = self.request_json("GET", "/api/tasks")
        self.assertEqual(status, 200)
        self.assertEqual([task["text"] for task in tasks], ["Persistir"])

    def test_rejects_invalid_task_text(self) -> None:
        for text in ("   ", "x" * 501):
            with self.subTest(length=len(text)):
                status, body = self.request_json(
                    "POST",
                    "/api/tasks",
                    {"text": text},
                )
                self.assertEqual(status, 400)
                self.assertIn("error", body)

        status, tasks = self.request_json("GET", "/api/tasks")
        self.assertEqual((status, tasks), (200, []))

    def test_accepts_text_at_maximum_length(self) -> None:
        status, created = self.request_json(
            "POST",
            "/api/tasks",
            {"text": "x" * 500},
        )
        self.assertEqual(status, 201)
        self.assertEqual(len(created["text"]), 500)

    def test_rejects_invalid_json_and_content_type(self) -> None:
        self.connection.request(
            "POST",
            "/api/tasks",
            body=b"{invalid",
            headers={"Content-Type": "application/json", "Content-Length": "8"},
        )
        response = self.connection.getresponse()
        self.assertEqual(response.status, 400)
        self.assertIn("error", json.loads(response.read()))

        status, body = self.request_json(
            "POST",
            "/api/tasks",
            {"text": "Tarefa"},
            content_type="text/plain",
        )
        self.assertEqual(status, 415)
        self.assertIn("error", body)

    def test_delete_validates_identifier_and_reports_missing_tasks(self) -> None:
        for invalid_id in ("0", "-1", "01", "abc", "9" * 20):
            with self.subTest(task_id=invalid_id):
                status, body = self.request_json(
                    "DELETE",
                    f"/api/tasks/{invalid_id}",
                )
                self.assertEqual(status, 400)
                self.assertIn("error", body)

        status, body = self.request_json("DELETE", "/api/tasks/987654")
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    def test_unknown_route_returns_json_error(self) -> None:
        status, body = self.request_json("GET", "/not-found")
        self.assertEqual(status, 404)
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()
