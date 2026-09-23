"""ORD-0263 fifth state: an origin that ANSWERS 200 and hands back junk as the body.

The four states my ruler already judges are "answered well", "answered badly", "never answered" and
"answered badly on health while the read hangs". A1 is the fifth, and it is the one the deadline work cannot
see: the server answers 2xx - so nothing times out and nothing throws at the transport layer - and the body is
not JSON at all. `v8Request` does `response.json().catch(() => null)`, so a 200 returns `null`, the caller then
raises a `TypeError` on `null.options`, and `classifyReadFailure()` files that TypeError under
`NETWORK_UNAVAILABLE / TRANSPORT` with `http_status: null`. The traveller is told "nothing came back" by a client
that actually got a 200.

Three shapes, because the arbiter's wording names three (`HTML / empty / not-JSON`); they are run as three
separate readings so one passing shape cannot carry the other two:

  html     200 text/html      - the bytes of the served index.html, i.e. exactly what a SPA fallback returns
  empty    200 (Content-Length: 0)
  nonjson  200 text/plain     - a short non-JSON sentence

`/api/v1/health` answers 200 too, which is what makes this the case the current code cannot overwrite: the boot
probe only re-classifies when `!fact.ok`. Loopback, my own port, hard ceiling, and every answer is logged so the
receipt can show the origin really did respond with a status.
"""
from __future__ import annotations

import http.server
import json
import socketserver
import threading
import sys
import time

PORT = 8411
MODE = (sys.argv[1] if len(sys.argv) > 1 else "html")
ROOT = r"D:\moodle\_qoder_preview_20260920\dist"
LOG = rf"D:\moodle\_qoder_harness_ord0254\ord0263_junk_{MODE}.log"
CEILING = 900

STATE = {"answered": 0, "health_answered_200": 0, "served_bytes": 0}


def index_bytes() -> bytes:
    with open(ROOT + r"\index.html", "rb") as fh:
        return fh.read()


def body_for(path: str) -> tuple[int, str, bytes]:
    if MODE == "html":
        return 200, "text/html; charset=utf-8", index_bytes()
    if MODE == "empty":
        return 200, "application/json", b""
    return 200, "text/plain; charset=utf-8", b"this sentence is not JSON at all\n"


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):  # noqa: N802
        code, ct, body = body_for(self.path)
        if self.path.startswith("/api/v1/health"):
            STATE["health_answered_200"] += 1
        STATE["answered"] += 1
        STATE["served_bytes"] += len(body)
        self.send_response(code)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if body:
            self.wfile.write(body)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": time.strftime("%H:%M:%S", time.localtime()),
                                 "kind": "answered", "path": self.path, "status": code,
                                 "content_type": ct, "body_bytes": len(body),
                                 "body_head": body[:36].decode("utf-8", "replace")},
                                ensure_ascii=False) + "\n")

    def log_message(self, *a):
        pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"kind": "instrument_start", "mode": MODE, "port": PORT,
                             "every_api_path_answers": 200}, ensure_ascii=False) + "\n")
    with Server(("127.0.0.1", PORT), Handler) as srv:
        # without serve_forever the backlog accepts and nothing ever answers - which is indistinguishable
        # from the very failure this instrument is supposed to contrast against
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        print(f"junk-200 origin mode={MODE} on :{PORT}; log {LOG}", flush=True)
        t0 = time.time()
        try:
            while time.time() - t0 < CEILING:
                time.sleep(2)
        except KeyboardInterrupt:
            pass
        srv.shutdown()
    print("final", STATE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
