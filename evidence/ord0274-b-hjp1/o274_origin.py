"""ORD-0274 two-generation surface (verifier instrument, not product code).

One origin, one browser-visible origin string, and a *swappable* disk root: the pointer
file `current_root.txt` is read on every request, so pointing the origin at the other
generation's dist is exactly what a real redeploy looks like to a returning client - no
restart, no new origin, no browser-side knowledge.

/api/* proxies to my own one-shot backend so the page is genuinely navigable.
Nothing here may unregister a worker or clear a cache: those moves are forbidden as pass
conditions by arbiter 5805553583, and I do not want my instrument to be able to do them
by accident - the only mutating knob this server has is which directory it reads.
"""
import json
import os
import posixpath
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LANE_DIR = os.path.abspath(sys.argv[1])
RUNDIR = os.path.abspath(sys.argv[2])
PORT = int(sys.argv[3])
BACKEND = int(sys.argv[4])

ROOT_POINTER = os.path.join(RUNDIR, "current_root.txt")
EVENTS = os.path.join(RUNDIR, "requests.jsonl")
_lock = threading.Lock()
STATIC = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
          ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml",
          ".webmanifest": "application/manifest+json", ".png": "image/png",
          ".json": "application/json", ".ico": "image/x-icon"}


def note(**kw):
    kw["t"] = round(time.time(), 3)
    kw["iso"] = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())
    with _lock:
        with open(EVENTS, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(kw, ensure_ascii=False) + "\n")


def current_root():
    with open(ROOT_POINTER, encoding="utf-8") as fh:
        return fh.read().strip()


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def _send(self, status, payload, ctype):
        self.send_response(status)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(payload)))
        self.send_header("cache-control", "no-store")        # the disk swap must be visible at once
        self.end_headers()
        self.wfile.write(payload)

    def _static(self, path):
        root = current_root()
        rel = posixpath.normpath(path.lstrip("/"))
        cand = os.path.join(root, rel.replace("/", os.sep))
        if rel and os.path.isfile(cand):
            return cand
        return os.path.join(root, "index.html")

    def _file(self, path):
        p = self._static(path)
        try:
            with open(p, "rb") as fh:
                data = fh.read()
        except OSError:
            return self._send(404, b"missing", "text/plain")
        self._send(200, data, STATIC.get(os.path.splitext(p)[1].lower(), "application/octet-stream"))

    def _proxy(self, method):
        n = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(n) if n else None
        hdrs = {k: v for k, v in self.headers.items()
                if k.lower() not in ("host", "connection", "accept-encoding")}
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (BACKEND, self.path),
                                     data=body, method=method, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                payload, status = r.read(), r.status
                ctype = r.headers.get("content-type", "application/octet-stream")
        except urllib.error.HTTPError as e:
            payload, status, ctype = e.read(), e.code, e.headers.get("content-type", "text/plain")
        except Exception as e:                                    # noqa: BLE001
            note(kind="upstream_error", method=method, path=self.path, error=str(e)[:140])
            return self._send(502, b'{"detail":"surface instrument"}', "application/json")
        note(kind="api", method=method, path=self.path.split("?")[0], status=status)
        self._send(status, payload, ctype)

    def do_GET(self):
        self._dispatch("GET")

    def do_HEAD(self):
        self._dispatch("HEAD")

    def _dispatch(self, method):
        if self.path.startswith("/api/"):
            return self._proxy(method)
        note(kind="static", path=self.path.split("?")[0], root=os.path.basename(current_root()))
        self._file(self.path)

    def do_POST(self):
        self._proxy("POST")

    def do_PUT(self):
        self._proxy("PUT")


if __name__ == "__main__":
    print("O274_ORIGIN_READY port=%d pointer=%s backend=%d" % (PORT, ROOT_POINTER, BACKEND), flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
