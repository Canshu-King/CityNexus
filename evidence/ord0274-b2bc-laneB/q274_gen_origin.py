"""ORD-0274-SW measurement instrument: one origin, two generations, same port, same origin.

Two things this has to be able to do that a plain static server cannot:

1. swap the generation UNDERNEATH an already-open document (`/__admin/swap`) while keeping the same port
   and origin, because a browser stores registrations per origin and a restarted server would hand every
   navigation a fresh document - which measures nothing about convergence;
2. hold a NON-IDEMPOTENT request open (`POST_DELAY_S`) and say out loud how many are open
   (`/__admin/inflight`), because B2c is exactly the shape "a write is in flight when the new worker takes
   over".  A write that answers immediately can never be in flight, so the arm would be vacuous, and the
   probe has to be able to time its swap against a real outstanding count rather than a guessed sleep.

Nothing here changes a product byte: the generations are two build directories, and the only mutation is
which directory answers.
"""
from __future__ import annotations

import json
import os
import pathlib
import socketserver
import sys
import threading
import time

GEN = sys.argv[sys.argv.index("--gen") + 1]
GEN2 = (sys.argv[sys.argv.index("--gen2") + 1] if "--gen2" in sys.argv else GEN)
PORT = int(sys.argv[sys.argv.index("--port") + 1])
LOG = pathlib.Path(sys.argv[sys.argv.index("--log") + 1])
DISTS = {
    "old": pathlib.Path(os.environ.get("CNX_GEN_OLD_DIR")
                        or r"D:\moodle\_qoder_b_lane_20260923\frontend\dist_0274sw"),
    "new": pathlib.Path(os.environ.get("CNX_GEN_NEW_DIR")
                        or r"D:\moodle\_qoder_b_lane_20260923\frontend\dist_0274gen2b"),
}
ACTIVE = {"gen": GEN}
# a write that answers immediately can never be observed "in flight" during a swap, and that is the whole
# shape B2c is about, so the delay lives on the server side where the page cannot shortcut it.
POST_DELAY_S = float(os.environ.get("CNX_POST_DELAY_S") or 0)
CT = {".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
      ".html": "text/html; charset=utf-8", ".svg": "image/svg+xml", ".json": "application/json",
      ".webmanifest": "application/manifest+json", ".png": "image/png"}

# the open writes, keyed by a per-request id: B2c's verdict must be provable from the origin's own record,
# not from the page's memory, because a reload wipes the page.
OPEN = {}
OPEN_LOCK = threading.Lock()
SEQ = {"n": 0}


class H(socketserver.StreamRequestHandler):
    def log_message(self, *a):
        pass

    def note(self, rec):
        rec["gen"] = ACTIVE["gen"]
        rec["at"] = round(time.time(), 3)
        rec["clock"] = time.strftime("%H:%M:%S")
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def handle(self):
        line = self.rfile.readline().decode("latin-1", "replace").strip()
        parts = line.split()
        if len(parts) < 2:
            return
        method, path = parts[0].upper(), parts[1].split("?")[0]
        headers = {}
        while True:
            raw = self.rfile.readline().decode("latin-1", "replace")
            if not raw or raw in ("\r\n", "\n"):
                break
            k, _, v = raw.partition(":")
            headers[k.strip().lower()] = v.strip()
        try:
            body = self.rfile.read(int(headers.get("content-length") or 0)) if headers.get("content-length") else b""
        except Exception:  # noqa: BLE001 - a truncated request body is the client's problem, not mine
            body = b""
        dist = DISTS[ACTIVE["gen"]]

        if path == "/__admin/swap":
            before = ACTIVE["gen"]
            ACTIVE["gen"] = GEN2
            self.note({"event": "swap", "from": before, "to": ACTIVE["gen"], "path": path,
                       "code": 200, "content_type": "application/json",
                       "bytes": len(json.dumps({"from": before, "to": ACTIVE["gen"]})),
                       "writes_open_at_swap": self.open_count()})
            payload = json.dumps({"from": before, "to": ACTIVE["gen"],
                                  "writes_open": self.open_count()}).encode()
            self.send(200, "application/json", payload, path, method)
            return
        if path == "/__admin/inflight":
            payload = json.dumps(self.inflight()).encode()
            self.send(200, "application/json", payload, path, method)
            return
        if path.startswith("/api/"):
            wid = None
            if method not in ("GET", "HEAD"):
                with OPEN_LOCK:
                    SEQ["n"] += 1
                    wid = SEQ["n"]
                OPEN[wid] = {"id": wid, "path": path, "method": method,
                             "started_at": round(time.time(), 3), "req_bytes": len(body)}
                self.note({"event": "write_started", "path": path, "method": method,
                           "code": None, "content_type": None, "bytes": len(body), "write_id": wid})
                # hold it open long enough that the swap genuinely lands mid-request
                time.sleep(POST_DELAY_S)
            payload = json.dumps({"status": "ok", "gen": ACTIVE["gen"],
                                  "id": "cnx-0274sw-write-ack",
                                  "journey_id": "cnx-0274sw-journey",
                                  "plan_id": "cnx-0274sw-plan"}).encode()
            rc = self.send(200, "application/json", payload, path, method)
            if wid is not None:
                # `delivered` is the whole answer to "did the reload cut the write in half": the request was
                # still open when the handover happened, and this says whether its answer ever arrived.
                finished = {"event": "write_finished", "path": path, "method": method,
                             "code": 200 if rc == "sent" else None, "content_type": "application/json",
                             "bytes": len(payload), "write_id": wid, "delivered": rc == "sent"}
                with OPEN_LOCK:
                    OPEN.pop(wid, None)
                self.note(finished)
            return

        rel = path.lstrip("/") or "index.html"
        f = (dist / rel)
        if f.is_file():
            self.send(200, CT.get(f.suffix.lower(), "application/octet-stream"),
                      f.read_bytes(), path, method)
            return
        self.send(200, "text/html; charset=utf-8", (dist / "index.html").read_bytes(), path, method)

    def open_count(self):
        with OPEN_LOCK:
            return len(OPEN)

    def inflight(self):
        with OPEN_LOCK:
            return {"gen": ACTIVE["gen"], "writes_open": len(OPEN),
                    "open": [dict(v, held_s=round(time.time() - v["started_at"], 2))
                             for v in OPEN.values()]}

    def send(self, code, ctype, body, path, method="GET"):
        try:
            self.wfile.write(f"HTTP/1.1 {code} X\r\nContent-Type: {ctype}\r\n"
                             f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode("latin-1"))
            self.wfile.write(body)
            rc = "sent"
        except Exception as exc:  # noqa: BLE001 - a dead socket is itself the reading B2c needs
            rc = f"failed:{type(exc).__name__}"
        self.note({"path": path, "code": code, "content_type": ctype, "bytes": len(body),
                   "asset": path.rsplit("/", 1)[-1], "method": method, "delivery": rc})
        return rc


class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    for g in (GEN, GEN2):
        assert DISTS[g].is_dir(), f"no dist for gen={g}: {DISTS[g]}"
    print(f"origin on 127.0.0.1:{PORT} serving {GEN} from {DISTS[GEN]}, "
          f"swap target {GEN2} from {DISTS[GEN2]}, POST_DELAY_S={POST_DELAY_S}", flush=True)
    with S(("127.0.0.1", PORT), H) as srv:
        srv.serve_forever(900)
