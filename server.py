#!/usr/bin/env python3
"""Serve the invitation pages and persist the latest meeting time."""

from __future__ import annotations

import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "time.json"
VALID_TIMES = {"15:00", "15:30", "16:00", "16:30"}


def read_time() -> str | None:
    try:
        value = json.loads(DATA_FILE.read_text(encoding="utf-8")).get("time")
    except (FileNotFoundError, json.JSONDecodeError, OSError, AttributeError):
        return None
    return value if value in VALID_TIMES else None


def write_time(value: str) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = DATA_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"time": value}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(DATA_FILE)


class InvitationHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        if urlparse(self.path).path == "/api/time":
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            return
        self.send_error(404)

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/api/time":
            self.send_json(200, {"time": read_time()})
            return
        super().do_GET()

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/time":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            value = payload.get("time")
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            self.send_json(400, {"error": "请求格式不正确"})
            return
        if value not in VALID_TIMES:
            self.send_json(400, {"error": "无效的时间选项"})
            return
        write_time(value)
        self.send_json(200, {"time": value})


if __name__ == "__main__":
    os.chdir(ROOT)
    server = ThreadingHTTPServer((HOST, PORT), InvitationHandler)
    print(f"Invitation server: http://{HOST}:{PORT}/index.html")
    print(f"Result page:      http://{HOST}:{PORT}/time.html")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
    finally:
        server.server_close()
