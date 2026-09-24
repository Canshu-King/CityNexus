"""ORD-0271-B reading collector: the screen text reaches my file without passing through my fingers.

Every earlier round of this order had the same weak link: the browser returns a reading, and then *I* write it
into a file. One retyped character and the receipt describes a screen nobody saw. So the page posts its own
payload here, this instrument writes it byte-for-byte, hashes what landed, and answers with the hash - which
lets the ruler compare "sha the page computed over its payload" with "sha of the bytes on disk" as two
independent readings of the same object.

Loopback, my own port (:4499), nothing but appends to one JSONL, and a per-line record of what the browser
claimed. CORS is `*` because the faces live on other loopback ports.
"""
from __future__ import annotations

import hashlib
import http.server
import json
import socketserver
import sys
import time
from pathlib import Path

PORT = 4499
OUT = Path(r"D:\moodle\_qoder_harness_ord0254\ord0271b_readings.jsonl")
CEILING = 7200
STATE = {"posted": 0, "bytes": 0, "labels": []}


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):  # noqa: N802
        body = json.dumps({"kind": "state", **STATE, "out": str(OUT),
                           "out_exists": OUT.is_file(),
                           "out_lines": len(OUT.read_text(encoding="utf-8").splitlines())
                           if OUT.is_file() else 0,
                           "at": time.strftime("%H:%M:%S", time.localtime())},
                          ensure_ascii=False).encode()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n)
        label = (self.path.split("?", 1)[1] if "?" in self.path else "").replace("pass=", "") or "unlabelled"
        line = json.dumps({"kind": "reading", "label": label,
                           "received_at": time.strftime("%H:%M:%S", time.localtime()),
                           "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                           "payload": raw.decode("utf-8", "replace")},
                          ensure_ascii=False)
        with open(OUT, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        STATE["posted"] += 1
        STATE["bytes"] += len(raw)
        STATE["labels"].append(label)
        ack = json.dumps({"written": True, "label": label, "bytes_on_disk": len(raw),
                          "sha256_of_bytes_written": hashlib.sha256(raw).hexdigest(),
                          "file": str(OUT)}, ensure_ascii=False).encode()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(ack)))
        self.end_headers()
        self.wfile.write(ack)

    def log_message(self, *a):
        pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    with Server(("127.0.0.1", PORT), Handler) as srv:
        t = __import__("threading").Thread(target=srv.serve_forever, daemon=True)
        t.start()
        print(f"collector on :{PORT} -> {OUT}", flush=True)
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
