"""ORD-0274 B2 origin: switchable generation root + a knob on the trip-writing POST.

Same shape as my ORD-0274 B-arm surface (one origin, root pointer swapped per request so a
redeploy is invisible to the browser), plus the write-leg control I built for ORD-0269-4,
because B2c is exactly the case where a non-idempotent write must still be in flight:

  answer                       forward everything, reply normally
  hold_journeys                forward POST /api/v1/journeys, read the server's answer,
                               then hold the reply - the traveller's write stays unsettled
  release_journeys_after_<ms>  same, but the reply is delivered after <ms> so the write
                               reaches its terminal state at a time I choose

Nothing here unregisters a worker or clears a cache (arbiter 5805553583 Q19 forbids it as a
pass condition), and every decision is appended to requests.jsonl so the receipt can prove
what the server did independently of what the page believed.
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

RUNDIR = os.path.abspath(sys.argv[1])
PORT = int(sys.argv[2])
BACKEND = int(sys.argv[3])
ROOT_POINTER = os.path.join(RUNDIR, "current_root.txt")
MODE_POINTER = os.path.join(RUNDIR, "mode.txt")
ASSET_POINTER = os.path.join(RUNDIR, "asset_root.txt")
EVENTS = os.path.join(RUNDIR, "requests.jsonl")
_lock = threading.Lock()
STATIC = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
          ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml",
          ".webmanifest": "application/manifest+json", ".png": "image/png",
          ".json": "application/json", ".ico": "image/x-icon"}
TRIP_WRITE = re.compile("^/api/v1/journeys$")


def note(**kw):
    kw["t"] = round(time.time(), 3)
    kw["iso"] = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())
    with _lock:
        with open(EVENTS, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(kw, ensure_ascii=False) + "\n")


def read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def _send(self, status, payload, ctype):
        self.send_response(status)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(payload)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _static(self, path):
        """Shell from current_root.txt, assets from asset_root.txt when it is set.

        Two pointers is the entire point of this file: a deploy that replaces index.html without
        keeping the previous generation's assets produces exactly this split, and what the client
        then sees is a 200 whose body is HTML at a .js URL.
        """
        shell = read(ROOT_POINTER)
        rel = posixpath.normpath(path.lstrip("/"))
        if rel.startswith("assets/"):
            asset_root = read(ASSET_POINTER) or shell
            cand = os.path.join(asset_root, rel.replace("/", os.sep))
            return cand if os.path.isfile(cand) else os.path.join(asset_root, "index.html")
        cand = os.path.join(shell, rel.replace("/", os.sep))
        if rel and os.path.isfile(cand):
            return cand
        return os.path.join(shell, "index.html")

    def _file(self, path):
        p = self._static(path)
        try:
            data = open(p, "rb").read()  # noqa: E501
        except OSError:
            return self._send(404, b"missing", "text/plain")
        self._send(200, data, STATIC.get(os.path.splitext(p)[1].lower(), "application/octet-stream"))

    def _upstream(self, method, body):
        hdrs = {k: v for k, v in self.headers.items()
                if k.lower() not in ("host", "connection", "accept-encoding")}
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (BACKEND, self.path),
                                     data=body, method=method, headers=hdrs)
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, r.read(), r.headers.get("content-type", "application/octet-stream"), \
                    round((time.time() - t0) * 1000, 1)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers.get("content-type", "text/plain"), \
                round((time.time() - t0) * 1000, 1)

    def _proxy(self, method):
        n = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(n) if n else None
        target = self.path.split("?")[0]
        mode = read(MODE_POINTER) or "answer"
        is_trip_write = method == "POST" and TRIP_WRITE.match(target)
        if method == "GET":
            hdrs = {k: v for k, v in self.headers.items()
                    if k.lower() not in ("host", "connection", "accept-encoding")}
            req = urllib.request.Request("http://127.0.0.1:%d%s" % (BACKEND, self.path), headers=hdrs)
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    payload, status, ctype = r.read(), r.status, r.headers.get("content-type", "application/json")
            except urllib.error.HTTPError as e:
                payload, status, ctype = e.read(), e.code, "application/json"
            except Exception as e:                                # noqa: BLE001
                note(kind="upstream_error", method="GET", path=target, error=str(e)[:140])
                return self._send(502, b'{"detail":"surface instrument"}', "application/json")
            note(kind="api", method="GET", path=target, status=status)
            return self._send(status, payload, ctype)
        status, payload, ctype, ms = self._upstream(method, body)
        if is_trip_write and mode.startswith(("hold_journeys", "release_journeys_after_")):
            hold_ms = None if mode == "hold_journeys" else re.search(r"(\d+)$", mode)
            hold_ms = None if hold_ms is None else int(hold_ms.group(1))
            note(kind="write_held", mode=mode, method=method, path=target, forwarded=True,
                 upstream_status=status, upstream_bytes=len(payload), upstream_ms=ms,
                 hold_ms=hold_ms,
                 why="server committed; the traveller is left with an unsettled write")
            if hold_ms is None:
                time.sleep(1800)
            else:
                time.sleep(hold_ms / 1000.0)
                note(kind="write_released", mode=mode, path=target, hold_ms=hold_ms,
                     delivered_status=status, at_release=True)
        note(kind="api", method=method, path=target, status=status, ms=ms)
        self._send(status, payload, ctype)

    def do_GET(self):
        self._dispatch("GET")

    def do_HEAD(self):
        self._dispatch("HEAD")

    def _dispatch(self, m):
        if self.path.startswith("/api/"):
            return self._proxy(m)
        target = self.path.split("?")[0]
        served = self._static(target)
        note(kind="static", path=target, shell_root=read(ROOT_POINTER),
             asset_root=read(ASSET_POINTER) or read(ROOT_POINTER),
             served=os.path.basename(served),
             html_at_js_url=bool(target.endswith(".js") and served.endswith("index.html")))
        self._file(target)

    def do_POST(self):
        self._proxy("POST")

    def do_PUT(self):
        self._proxy("PUT")


if __name__ == "__main__":
    print("O274B2_ORIGIN_READY port=%d rundir=%s backend=%d" % (PORT, RUNDIR, BACKEND), flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
