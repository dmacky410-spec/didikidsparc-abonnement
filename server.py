#!/usr/bin/env python3
"""Didikids Parc — Serveur de gestion d'abonnements.

Lancement :  python3 server.py  (puis ouvrir http://localhost:8730)
Aucune dépendance externe — bibliothèque standard Python uniquement.
"""
import json
import os
import queue
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from park import db, api
from park.auth import get_user_by_token

PORT = int(os.environ.get("PORT", "8730"))
PUBLIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml",
    ".ico": "image/x-icon", ".woff2": "font/woff2",
}

# ------------------------------------------------------------- flux SSE
# Le pont RFID envoie les UID scannés ; le navigateur les reçoit en direct.
_sse_clients = []
_sse_lock = threading.Lock()


def sse_broadcast(event):
    data = json.dumps(event)
    with _sse_lock:
        for q in list(_sse_clients):
            try:
                q.put_nowait(data)
            except Exception:
                pass


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass  # journal silencieux

    # ----- helpers
    def send_json(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def get_token(self):
        cookies = self.headers.get("Cookie", "")
        for part in cookies.split(";"):
            k, _, v = part.strip().partition("=")
            if k == "didikids_session":
                return v
        return None

    def read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    # ----- routes
    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def do_PUT(self):
        self.route("PUT")

    def route(self, method):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}

        if path == "/api/events":
            return self.handle_sse()
        if path == "/api/scan" and method == "POST":
            return self.handle_scan()
        if path.startswith("/api/"):
            return self.handle_api(method, path, query)
        if method == "GET":
            return self.serve_static(path)
        self.send_json(404, {"error": "Introuvable"})

    def handle_api(self, method, path, query):
        body = self.read_body() if method in ("POST", "PUT") else {}
        conn = db.connect()
        try:
            token = self.get_token()
            user = get_user_by_token(conn, token)

            if path == "/api/login" and method == "POST":
                result = api.handle(method, path, query, body, None, conn)
                conn.commit()
                token = result.pop("token")
                payload = json.dumps(result, ensure_ascii=False).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Set-Cookie",
                                 f"didikids_session={token}; HttpOnly; Path=/; SameSite=Strict; Max-Age=50400")
                self.end_headers()
                self.wfile.write(payload)
                return

            if path == "/api/logout":
                body["_token"] = token or ""

            result = api.handle(method, path, query, body, user, conn)
            conn.commit()
            self.send_json(200, result)
        except api.ApiError as e:
            conn.rollback()
            self.send_json(e.status, {"error": e.message})
        except Exception as e:
            conn.rollback()
            self.send_json(500, {"error": f"Erreur interne : {e}"})
        finally:
            conn.close()

    def handle_scan(self):
        """Reçoit un UID du pont RFID (ACR122U) et le diffuse aux écrans connectés."""
        body = self.read_body()
        uid = (body.get("uid") or "").strip()
        token = body.get("token") or self.headers.get("X-Scan-Token", "")
        conn = db.connect()
        try:
            expected = db.get_setting(conn, "scan_token", "")
        finally:
            conn.close()
        is_local = self.client_address[0] in ("127.0.0.1", "::1")
        if not uid:
            return self.send_json(400, {"error": "uid manquant"})
        if not is_local and token != expected:
            return self.send_json(403, {"error": "jeton de scan invalide"})
        sse_broadcast({"type": "scan", "uid": api.normalize_uid(uid)})
        self.send_json(200, {"ok": True})

    def handle_sse(self):
        conn = db.connect()
        try:
            user = get_user_by_token(conn, self.get_token())
        finally:
            conn.close()
        if not user:
            return self.send_json(401, {"error": "Non connecté"})

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        q = queue.Queue()
        with _sse_lock:
            _sse_clients.append(q)
        try:
            self.wfile.write(b": connecte\n\n")
            self.wfile.flush()
            while True:
                try:
                    data = q.get(timeout=20)
                    self.wfile.write(f"data: {data}\n\n".encode())
                except queue.Empty:
                    self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with _sse_lock:
                if q in _sse_clients:
                    _sse_clients.remove(q)

    def serve_static(self, path):
        if path in ("/", ""):
            path = "/index.html"
        safe = os.path.normpath(path).lstrip("/\\")
        full = os.path.join(PUBLIC_DIR, safe)
        if not full.startswith(PUBLIC_DIR) or not os.path.isfile(full):
            full = os.path.join(PUBLIC_DIR, "index.html")  # SPA fallback
        ext = os.path.splitext(full)[1].lower()
        with open(full, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(content)))
        if ext in (".png", ".jpg", ".svg", ".woff2", ".ico"):
            self.send_header("Cache-Control", "max-age=86400")
        else:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)


def main():
    db.init()
    conn = db.connect()
    scan_token = db.get_setting(conn, "scan_token")
    conn.close()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("=" * 56)
    print("  Didikids Parc — Gestion des abonnements")
    print(f"  Interface : http://localhost:{PORT}")
    print(f"  Jeton pont RFID (bridge/acr122u_bridge.py) : {scan_token}")
    print("  Compte initial : admin / admin123  (a changer !)")
    print("=" * 56)
    if os.environ.get("NO_BROWSER") != "1":
        threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")


if __name__ == "__main__":
    main()
