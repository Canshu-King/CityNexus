"""CMDR r1 - a static+API front for one built dist, so a generation can be walked on its own port.

Why this exists: `vite preview` needs the export to carry node_modules, and I refuse to junction a
lane's node_modules into my export (HARDLINK/JUNCTION hazard already paid for once).  This server does
exactly two things: serve files from <dist> with real MIME types, and forward /api/* to a backend port
without touching its body.  Nothing here writes: the backend leg is the caller's, and a POST that is
not asked for never happens.

Usage:
  python cmdr_static_api_proxy_r1.py --dist <dir> --port 4789 --api 8693 [--log <file>]
"""
import argparse
import json
import os
import socketserver
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler

MIME = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript;charset=UTF-8",
    ".mjs": "text/javascript;charset=UTF-8", ".css": "text/css;charset=UTF-8",
    ".json": "application/json", ".webmanifest": "application/manifest+json",
    ".png": "image/png", ".svg": "image/svg+xml", ".woff2": "font/woff2",
    ".wasm": "application/wasm", ".ico": "image/x-icon", ".map": "application/json",
}


class Handler(BaseHTTPRequestHandler):
    dist = None
    api_port = None
    log_fh = None
    protocol_version = "HTTP/1.1"

    def _log(self, rec):
        if self.log_fh:
            self.log_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self.log_fh.flush()

    def _send(self, status, body, ctype, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def handle_one(self):
        path = self.path.split("?")[0]
        if path.startswith("/api/") or path in ("/openapi.json", "/health"):
            url = "http://127.0.0.1:%d%s" % (self.api_port, self.path)
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else None
            req = urllib.request.Request(url, data=body, method=self.command)
            for h in ("Content-Type", "Idempotency-Key", "X-Demo-Reset-Token", "Authorization"):
                if self.headers.get(h):
                    req.add_header(h, self.headers[h])
            req.add_header("User-Agent", "cnx-cmdr-static-front")
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            t0 = time.time()
            try:
                with opener.open(req, timeout=120) as r:
                    data = r.read()
                    self._send(r.status, data, r.headers.get("Content-Type", "application/json"))
                    self._log({"k": "api", "path": self.path, "status": r.status,
                               "bytes": len(data), "ms": round((time.time() - t0) * 1000)})
            except urllib.error.HTTPError as e:
                data = e.read()
                self._send(e.code, data, e.headers.get("Content-Type", "application/json"))
                self._log({"k": "api", "path": self.path, "status": e.code, "bytes": len(data)})
            except Exception as e:
                msg = json.dumps({"error": {"code": "UPSTREAM_UNREACHABLE",
                                            "message": type(e).__name__}}).encode()
                self._send(502, msg, "application/json")
                self._log({"k": "api", "path": self.path, "status": 502,
                           "error": type(e).__name__})
            return
        rel = path.lstrip("/") or "index.html"
        target = os.path.normpath(os.path.join(self.dist, rel))
        if not target.startswith(os.path.normpath(self.dist)):
            self._send(403, b"path outside dist", "text/plain")
            return
        if os.path.isdir(target):
            target = os.path.join(target, "index.html")
        if not os.path.isfile(target):
            # a route (no dot, so not an asset) belongs to the SPA shell; an asset path stays a 404,
            # because a JS/CSS request answered with HTML is the failure this front must be able to show
            if "." not in os.path.basename(target) and not os.path.exists(target):
                shell = os.path.join(self.dist, "index.html")
                if os.path.isfile(shell) and (self.path.startswith("/v8/") or self.path == "/"):
                    with open(shell, "rb") as fh:
                        data = fh.read()
                    self._send(200, data, MIME[".html"])
                    self._log({"k": "spa_shell", "path": self.path, "status": 200,
                               "bytes": len(data)})
                    return
            self._send(404, b"not found: " + rel.encode("utf-8", "replace"), "text/plain")
            self._log({"k": "file", "path": rel, "status": 404})
            return
        ext = os.path.splitext(target)[1].lower()
        with open(target, "rb") as fh:
            data = fh.read()
        self._send(200, data, MIME.get(ext, "application/octet-stream"))
        self._log({"k": "file", "path": rel, "status": 200, "bytes": len(data),
                   "ctype": MIME.get(ext, "application/octet-stream")})

    do_GET = do_HEAD = do_POST = do_DELETE = do_PUT = do_PATCH = handle_one

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--api", type=int, required=True)
    ap.add_argument("--log", default="")
    a = ap.parse_args()
    Handler.dist = os.path.abspath(a.dist)
    Handler.api_port = a.api
    if a.log:
        Handler.log_fh = open(a.log, "a", encoding="utf-8")

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    with Server(("127.0.0.1", a.port), Handler) as srv:
        print(json.dumps({"serving": Handler.dist, "port": a.port, "api": a.api,
                          "pid": os.getpid()}), flush=True)
        srv.serve_forever()


if __name__ == "__main__":
    main()
