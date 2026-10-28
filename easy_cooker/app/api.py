"""Small JSON HTTP adapter implemented with the Python standard library."""
import json
import logging
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from .schemas import DomainError

MAX_BODY_BYTES = 65536
logger = logging.getLogger(__name__)


def make_server(service, host="127.0.0.1", port=8000):
    class Handler(BaseHTTPRequestHandler):
        def _body(self):
            if self.headers.get("Transfer-Encoding"):
                raise DomainError("Transfer-Encoding is unsupported")
            raw_length = self.headers.get("Content-Length")
            try:
                length = int(raw_length) if raw_length is not None else 0
            except ValueError:
                raise DomainError("Invalid Content-Length")
            if length <= 0 or length > MAX_BODY_BYTES:
                raise DomainError("JSON body required; maximum size is 65536 bytes", 413)
            try:
                return json.loads(self.rfile.read(length))
            except (ValueError, UnicodeDecodeError):
                raise DomainError("Invalid JSON")

        def _route(self):
            path = urlsplit(self.path).path
            if self.command == "GET":
                if path == "/health":
                    return {"status": "ok"}
                if path == "/menu":
                    return service.get_menu()
                if path == "/state":
                    return service.snapshot()
                match = re.fullmatch(r"/chefs/([0-9]+)/task", path)
                if match:
                    return service.get_chef(int(match[1]))
                match = re.fullmatch(r"/sessions/([^/]+)", path)
                if match:
                    return service.get_session(match[1])
            elif self.command == "POST":
                if path == "/orders":
                    return service.submit_order(self._body())
                match = re.fullmatch(r"/chefs/([0-9]+)/tasks/([^/]+)/complete", path)
                if match:
                    return service.complete_task(int(match[1]), match[2])
                match = re.fullmatch(r"/sessions/([^/]+)/close", path)
                if match:
                    return service.close_session(match[1])
            raise DomainError("Endpoint not found", 404)

        def _handle(self):
            self.connection.settimeout(10)
            try:
                result, status = self._route(), 200
            except DomainError as exc:
                result, status = {"error": str(exc)}, exc.status
            except Exception:
                logger.exception("Unhandled API error")
                result, status = {"error": "Internal server error"}, 500
            data = json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            self.wfile.write(data)

        do_GET = _handle
        do_POST = _handle

    return ThreadingHTTPServer((host, port), Handler)
