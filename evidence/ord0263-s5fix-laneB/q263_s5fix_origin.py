"""ORD-0263 fifth-state candidate: one origin that can play every role the five cells need.

Six modes, one process each so no reading inherits another's state:

  html     200 text/html      on the journey read      (fifth state, shape 1)
  empty    200 with zero bytes                          (fifth state, shape 2)
  nonjson  200 text/plain                               (fifth state, shape 3)
  five_hundred  500 text/plain on the read AND on health (cell S2: origin answered badly)
  silent        accepts the read and never writes        (cell S3: nobody answered)
  mixed         read hangs while /api/v1/health answers 500 (cell S4: the probe speaks)

In html/empty/nonjson `/api/v1/health` answers 200 JSON on purpose: that is the case the old code could
not overwrite, because `boot()` only re-classifies when `!fact.ok`.  Every reply is logged so the receipt
can show what the origin really sent, including the bytes.
"""
from __future__ import annotations

import json
import pathlib
import socketserver
import sys
import threading
import time

MODE = sys.argv[sys.argv.index("--mode") + 1]
PORT = int(sys.argv[sys.argv.index("--port") + 1])
LOG = pathlib.Path(sys.argv[sys.argv.index("--log") + 1])
DIST = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923\frontend\dist_s5")
HEALTH = json.dumps({"status": "ok", "version": "ord0263-s5fix-mine"}).encode()
PLAIN = b"origin says: plan service is warming up\n"
BODY = {"html": (DIST / "index.html").read_bytes(), "empty": b"", "nonjson": PLAIN}[MODE] if MODE in (
    "html", "empty", "nonjson") else b""
CT = {"html": "text/html; charset=utf-8", "empty": "application/json",
      "nonjson": "text/plain; charset=utf-8"}.get(MODE)


class H(socketserver.StreamRequestHandler):
    def log(self, rec):
        rec["at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def handle(self):
        line = self.rfile.readline().decode("latin-1", "replace").strip()
        parts = line.split()
        if len(parts) < 2:
            return
        method, path = parts[0], parts[1]
        while True:
            if not self.rfile.readline().decode("latin-1", "replace").strip():
                break
        is_health = path.startswith("/api/v1/health")
        is_read = "/experience" in path
        if MODE == "silent" and (is_read or not path.startswith("/api/")):
            self.log({"kind": "hung", "mode": MODE, "path": path, "method": method,
                      "status": None, "content_type": None, "body_bytes": 0, "body_head": ""})
            threading.Event().wait()
            return
        if MODE == "mixed" and is_read:
            self.log({"kind": "hung", "mode": MODE, "path": path, "method": method,
                      "status": None, "content_type": None, "body_bytes": 0, "body_head": ""})
            threading.Event().wait()
            return
        if MODE == "five_hundred":
            self._send(500, "text/plain", b"Internal Server Error", path, method,
                       "health_500" if is_health else "answered_500")
            return
        if MODE == "mixed" and is_health:
            self._send(500, "text/plain", b"Internal Server Error", path, method, "health_500")
            return
        if is_health:
            self._send(200, "application/json", HEALTH, path, method, "health_answered_200")
            return
        if path.startswith("/api/"):
            self._send(200, CT, BODY, path, method, "answered")
            return
        self._send(200, "text/html; charset=utf-8", (DIST / "index.html").read_bytes(),
                   path, method, "shell")

    def _send(self, status, ctype, body, path, method, kind):
        self.wfile.write(f"HTTP/1.1 {status} X\r\nContent-Type: {ctype}\r\n"
                         f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode("latin-1"))
        self.wfile.write(body)
        self.log({"kind": kind, "mode": MODE, "path": path, "method": method, "status": status,
                  "content_type": ctype, "body_bytes": len(body),
                  "body_head": body[:48].decode("utf-8", "replace")})


class Srv(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


LOG.unlink(missing_ok=True)
print(f"my multi-mode origin mode={MODE} on 127.0.0.1:{PORT}", flush=True)
with Srv(("127.0.0.1", PORT), H) as srv:
    srv.serve_forever(900)
