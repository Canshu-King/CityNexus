"""ORD-0269-4 one-origin server (verifier instrument, not product code).

Serves the published generation's static shell and proxies /api to my own one-shot
backend on a named port, with one extra knob: a mode file that decides what happens to
the trip-writing POST.  Three modes so the *only* variable between arms is whether the
server got to answer:

  answer            forward everything, reply normally            (control: stack is live)
  never             do NOT forward POST /api/v1/journeys, stay silent
                    -> the server holds nothing; the screen's "not created" is true
  swallow_journeys  forward POST /api/v1/journeys, read the server's full answer,
                    then never reply to the browser
                    -> the trip is committed on the server while the client is blind

Every intercepted decision is appended to events.jsonl so the receipt can prove arrival
from the origin side, independent of what the browser believed.
"""
import json
import os
import posixpath
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.abspath(sys.argv[1])            # dist dir (static shell)
PORT = int(sys.argv[2])                         # my named origin port
BACKEND = int(sys.argv[3])                      # my named backend port
RUNDIR = os.path.abspath(sys.argv[4])           # my one-shot run dir
HANG_LIMIT_S = float(os.getenv("CNX_HANG_LIMIT", "900"))

MODE_FILE = os.path.join(RUNDIR, "mode.txt")
EVENTS = os.path.join(RUNDIR, "events.jsonl")
API = "http://127.0.0.1:%d" % BACKEND
TRIP_WRITE = re.compile(r"^/api/v1/journeys$")

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


def mode():
    try:
        with open(MODE_FILE, encoding="utf-8") as fh:
            return fh.read().strip() or "answer"
    except OSError:
        return "answer"


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    # ---------- helpers ----------
    def _body(self):
        n = int(self.headers.get("content-length") or 0)
        return self.rfile.read(n) if n else b""

    def _static(self, path):
        rel = posixpath.normpath(path.lstrip("/"))
        cand = os.path.join(ROOT, rel.replace("/", os.sep))
        if rel and os.path.isfile(cand):
            return cand
        return os.path.join(ROOT, "index.html")        # SPA fallback, as the real host does

    def _send(self, status, payload, ctype, extra=None):
        self.send_response(status)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(payload)))
        for k, v in (extra or []):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload)

    def _file(self, path):
        p = self._static(path)
        try:
            with open(p, "rb") as fh:
                data = fh.read()
        except OSError:
            return self._send(404, b"missing", "text/plain")
        self._send(200, data, STATIC.get(os.path.splitext(p)[1].lower(), "application/octet-stream"))

    def _proxy(self, method):
        m = mode()
        target = self.path
        is_trip_write = method == "POST" and TRIP_WRITE.match(target.split("?")[0])
        body = self._body()
        if is_trip_write and m == "never":
            note(kind="hold", mode=m, method=method, path=target, forwarded=False,
                 why="mode=never: request never reaches the backend")
            return self._hold(m, method, target)
        hdrs = {k: v for k, v in self.headers.items()
                if k.lower() not in ("host", "connection", "accept-encoding")}
        req = urllib.request.Request(API + target, data=body or None, method=method, headers=hdrs)
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                payload = r.read()
                status = r.status
                ctype = r.headers.get("content-type", "application/octet-stream")
        except urllib.error.HTTPError as e:
            payload, status, ctype = e.read(), e.code, e.headers.get("content-type", "text/plain")
        except Exception as e:                                   # noqa: BLE001
            note(kind="upstream_error", method=method, path=target, error=str(e)[:160])
            return self._send(502, b'{"detail":"origin instrument"}', "application/json")
        up_ms = round((time.time() - t0) * 1000, 1)
        if is_trip_write and m == "swallow_journeys":
            note(kind="swallow", mode=m, method=method, path=target, forwarded=True,
                 upstream_status=status, upstream_bytes=len(payload), upstream_ms=up_ms,
                 why="backend answered; the answer is withheld from the traveller")
            return self._hold(m, method, target, upstream_status=status, upstream_bytes=len(payload))
        note(kind="pass", method=method, path=target, upstream_status=status, upstream_ms=up_ms)
        self._send(status, payload, ctype)

    def _hold(self, m, method, target, **kw):
        """Never answer: the traveller's fetch stays open, exactly like a silent port."""
        t0 = time.time()
        while time.time() - t0 < HANG_LIMIT_S:
            time.sleep(0.5)
        note(kind="hold_released", mode=m, method=method, path=target,
             held_s=round(time.time() - t0, 1), **kw)
        self.close_connection = True

    # ---------- verbs ----------
    def do_GET(self):
        (self._proxy("GET") if self.path.startswith("/api/") else self._file(self.path))

    def do_HEAD(self):
        self._proxy("HEAD") if self.path.startswith("/api/") else self._file(self.path)

    def do_POST(self):
        self._proxy("POST")

    def do_PUT(self):
        self._proxy("PUT")

    def do_PATCH(self):
        self._proxy("PATCH")

    def do_DELETE(self):
        self._proxy("DELETE")


if __name__ == "__main__":
    print("ORIGIN_READY port=%d root=%s backend=%d" % (PORT, ROOT, BACKEND), flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
