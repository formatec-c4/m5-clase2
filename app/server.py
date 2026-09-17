import json
import os
import socket
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path("/app")
CONFIG = ROOT / "config"


def read_config(name):
    return (CONFIG / name).read_text(encoding="utf-8").strip()


class Handler(BaseHTTPRequestHandler):
    server_version = "BancoChocoFrontend/1.0"

    def send_bytes(self, status, content_type, data):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, status, payload):
        self.send_bytes(status, "application/json; charset=utf-8", json.dumps(payload).encode())

    def proxy(self, method, path, body=None):
        core_url = read_config("core_url").rstrip("/")
        token = read_config("api_token")
        request_id = self.headers.get("X-Request-ID", str(uuid.uuid4()))
        headers = {
            "Accept": "application/json",
            "X-Lab-Token": token,
            "X-Request-ID": request_id,
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
            headers["Idempotency-Key"] = self.headers.get("Idempotency-Key", str(uuid.uuid4()))
        request = urllib.request.Request(core_url + path, data=body, headers=headers, method=method)
        print(json.dumps({
            "event": "call_core",
            "request_id": request_id,
            "method": method,
            "path": path,
            "destination": core_url,
        }), flush=True)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                print(json.dumps({
                    "event": "core_response",
                    "request_id": request_id,
                    "status": response.status,
                }), flush=True)
                return response.status, response.headers.get("Content-Type", "application/json"), response.read()
        except urllib.error.HTTPError as exc:
            print(json.dumps({
                "event": "core_response",
                "request_id": request_id,
                "status": exc.code,
            }), flush=True)
            return exc.code, "application/json", exc.read()
        except Exception as exc:
            print(json.dumps({
                "event": "core_unavailable",
                "request_id": request_id,
                "error": type(exc).__name__,
            }), flush=True)
            payload = {
                "error": "core_unavailable",
                "message": "El canal digital esta disponible, pero no puede comunicarse con el core bancario.",
                "detail": type(exc).__name__,
            }
            return 503, "application/json", json.dumps(payload).encode()

    def do_GET(self):
        if self.path == "/":
            self.send_bytes(200, "text/html; charset=utf-8", (ROOT / "index.html").read_bytes())
            return
        if self.path == "/health":
            self.send_json(200, {"status": "ok", "frontend": socket.gethostname(), "environment": "aws-ec2"})
            return
        if self.path == "/api/status":
            status, content_type, data = self.proxy("GET", "/api/meta")
            if status == 200:
                payload = json.loads(data)
                payload["frontend"] = socket.gethostname()
                payload["frontend_environment"] = "aws-ec2"
                self.send_json(200, payload)
            else:
                self.send_bytes(status, content_type, data)
            return
        if self.path == "/api/accounts":
            status, content_type, data = self.proxy("GET", self.path)
            self.send_bytes(status, content_type, data)
            return
        self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/api/transfers":
            self.send_json(404, {"error": "not_found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        status, content_type, data = self.proxy("POST", self.path, body)
        self.send_bytes(status, content_type, data)

    def log_message(self, fmt, *args):
        print(json.dumps({"client": self.client_address[0], "request": fmt % args}), flush=True)


ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
