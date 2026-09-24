"""ORD-0274-SW measurement instrument: one origin, two generations, same port, same origin.

The claim I have to check before touching any code is a runtime one: when the worker is replaced, does
`main.tsx:1718-1720` bail out because it identifies a generation by `controller.scriptURL`, which is the
constant string `/v10-sw.js` in both generations?

A browser stores registrations per ORIGIN, so the only way to swap generations honestly is to keep the
port and change what answers on it. `--gen` picks the dist directory; nothing else differs.
"""
from __future__ import annotations

import json
import os
import pathlib
import socketserver
import sys
import time

GEN = sys.argv[sys.argv.index("--gen") + 1]
GEN2 = (sys.argv[sys.argv.index("--gen2") + 1] if "--gen2" in sys.argv else GEN)
PORT = int(sys.argv[sys.argv.index("--port") + 1])
LOG = pathlib.Path(sys.argv[sys.argv.index("--log") + 1])
DISTS = {
    "old": pathlib.Path(os.environ.get("CNX_GEN_OLD_DIR")
                        or r"D:\moodle\_qoder_b_ord0268_20260923\genB\frontend\dist_ord0268"),
    "new": pathlib.Path(os.environ.get("CNX_GEN_NEW_DIR")
                        or r"D:\moodle\_qoder_b_lane_20260923\frontend\dist_ord0267b"),
}
ACTIVE = {"gen": GEN}
CT = {".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
      ".html": "text/html; charset=utf-8", ".svg": "image/svg+xml", ".json": "application/json",
      ".webmanifest": "application/manifest+json", ".png": "image/png"}


class H(socketserver.StreamRequestHandler):
    def log_message(self, *a):
        pass

    def note(self, rec):
        rec["gen"] = ACTIVE["gen"]
        rec["at"] = time.strftime("%H:%M:%S")
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def handle(self):
        line = self.rfile.readline().decode("latin-1", "replace").strip()
        parts = line.split()
        if len(parts) < 2:
            return
        path = parts[1].split("?")[0]
        while True:
            if not self.rfile.readline().decode("latin-1", "replace").strip():
                break
        dist = DISTS[ACTIVE["gen"]]
        if path == "/__admin/swap":
            # one process, one port, one origin: the page that is ALREADY OPEN has to live through the
            # swap, because that is the only way to see whether it converges without a second navigation
            before = ACTIVE["gen"]
            ACTIVE["gen"] = GEN2
            body = json.dumps({"from": before, "to": ACTIVE["gen"]}).encode()
            self.send(200, "application/json", body, path)
            return
        if path.startswith("/api/"):
            self.send(200, "application/json", json.dumps({"status": "ok", "gen": ACTIVE["gen"]}).encode(), path)
            return
        rel = path.lstrip("/") or "index.html"
        f = (dist / rel)
        if f.is_file():
            self.send(200, CT.get(f.suffix.lower(), "application/octet-stream"), f.read_bytes(), path)
            return
        shell = (dist / "index.html").read_bytes()
        self.send(200, "text/html; charset=utf-8", shell, path)

    def send(self, code, ctype, body, path):
        self.wfile.write(f"HTTP/1.1 {code} X\r\nContent-Type: {ctype}\r\n"
                         f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode("latin-1"))
        self.wfile.write(body)
        self.note({"path": path, "code": code, "content_type": ctype, "bytes": len(body),
                   "asset": path.rsplit("/", 1)[-1]})


class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    for g in (GEN, GEN2):
        assert DISTS[g].is_dir(), f"no dist for gen={g}: {DISTS[g]}"
    print(f"origin on 127.0.0.1:{PORT} serving {GEN} from {DISTS[GEN]}, "
          f"swap target {GEN2} from {DISTS[GEN2]}", flush=True)
    with S(("127.0.0.1", PORT), H) as srv:
        srv.serve_forever(900)
