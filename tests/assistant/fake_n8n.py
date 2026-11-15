"""A fake n8n over real HTTP: the adapter talks to a real server, without mocks."""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class FakeN8n:
    def __init__(
        self,
        *,
        status: int = 200,
        body: Any = None,
        raw: bytes | None = None,
        delay_s: float = 0.0,
    ) -> None:
        self.status = status
        self.body = {"text": "respuesta"} if body is None else body
        self.raw = raw
        self.delay_s = delay_s
        self.requests: list[dict[str, Any]] = []
        self._server: ThreadingHTTPServer | None = None

    @property
    def url(self) -> str:
        assert self._server is not None
        return f"http://127.0.0.1:{self._server.server_address[1]}/webhook/space-apps-assistant"

    def __enter__(self) -> FakeN8n:
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                payload = self.rfile.read(length)
                outer.requests.append(
                    {
                        "path": self.path,
                        "content_type": self.headers.get("Content-Type"),
                        "json": json.loads(payload) if payload else None,
                    }
                )
                time.sleep(outer.delay_s)
                data = outer.raw if outer.raw is not None else json.dumps(outer.body).encode()
                try:
                    self.send_response(outer.status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass  # the client already gave up on time

            def log_message(self, *args: object) -> None:
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc: object) -> None:
        assert self._server is not None
        self._server.shutdown()
        self._server.server_close()
