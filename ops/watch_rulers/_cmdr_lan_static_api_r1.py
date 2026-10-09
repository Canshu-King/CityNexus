"""CMDR LAN static+API host for the phone chain (binds 0.0.0.0 on purpose).

Why a second file instead of a flag on cmdr_static_api_proxy_r1.py: that instrument is already cited in
published receipts and its bind address is part of those readings, so it must keep behaving exactly as it
did.  This one is the LAN variant the commander asked for: the phone loads the frontend from this port and
every /api request is forwarded to the backend port, which stays on loopback.

usage: python _cmdr_lan_static_api_r1.py --dist <dist-dir> --port 4783 --api 4781 [--log <file>]
"""
import argparse
import http.server
import json
import os
import socketserver
import sys
import time
import urllib.error
import urllib.request

LOG = {"requests": 0, "api": 0, "static": 0, "spa_fallbacks": 0, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}


class Handler(http.server.SimpleHTTPRequestHandler):
    dist = ""
    api_port = 0

    def log_message(self, fmt, *args):  # keep the console quiet; the counter below is the record
        pass

    def _record(self, kind, status, path):
        LOG["requests"] += 1
        LOG[kind] += 1
        LOG.setdefault("last", []).append({"kind": kind, "http_status": status, "path": path})
        LOG["last"] = LOG["last"][-50:]

    def _proxy(self, method):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        url = "http://127.0.0.1:%d%s" % (self.api_port, self.path)
        req = urllib.request.Request(url, data=body, method=method)
        for h in ("Content-Type", "Accept", "Authorization", "Idempotency-Key"):
            if self.headers.get(h):
                req.add_header(h, self.headers[h])
        try:
            r = urllib.request.urlopen(req, timeout=60)
            payload, status, ctype = r.read(), r.status, r.headers.get("Content-Type", "application/json")
        except urllib.error.HTTPError as e:
            payload, status, ctype = e.read(), e.code, e.headers.get("Content-Type", "application/json")
        except Exception as e:  # the backend is down: say so instead of answering a fake 200
            payload = json.dumps({"error": {"code": "UPSTREAM_UNREACHABLE", "detail": type(e).__name__}}).encode()
            status, ctype = 502, "application/json"
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
        self._record("api", status, self.path)

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self._proxy("GET")
        return self._static()

    def do_POST(self):
        return self._proxy("POST")

    def do_PUT(self):
        return self._proxy("PUT")

    def do_PATCH(self):
        return self._proxy("PATCH")

    def do_DELETE(self):
        return self._proxy("DELETE")

    def _static(self):
        path = self.path.split("?")[0]
        candidate = os.path.join(self.dist, path.lstrip("/") or "index.html")
        if os.path.isdir(candidate):
            candidate = os.path.join(candidate, "index.html")
        if not os.path.isfile(candidate):
            # SPA fallback: a state-routed app answers every unknown path with the shell
            candidate = os.path.join(self.dist, "index.html")
            LOG["spa_fallbacks"] += 1
        with open(candidate, "rb") as fh:
            data = fh.read()
        ext = os.path.splitext(candidate)[1].lower()
        ctype = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css",
                 ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png",
                 ".woff2": "font/woff2"}.get(ext, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        self._record("static", 200, path)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--api", type=int, required=True)
    ap.add_argument("--log", default="")
    a = ap.parse_args()
    Handler.dist = os.path.abspath(a.dist)
    Handler.api_port = a.api
    print(json.dumps({"bind": "0.0.0.0:%d" % a.port, "dist": Handler.dist, "api": a.api}), flush=True)
    with Server(("0.0.0.0", a.port), Handler) as srv:
        try:
            srv.serve_forever()
        finally:
            if a.log:
                with open(a.log, "w", encoding="utf-8") as fh:
                    json.dump(LOG, fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
