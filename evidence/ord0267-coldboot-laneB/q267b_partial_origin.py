"""ORD-0267 step 2: does a FIRST visit with a partially failing origin leave a half generation behind?

The original 0267 symptom (installed client, site down, chrome-error page) is closed on the current
generation -- measured: three offline navigations all answered 200 from `workbox-precache-v2` with 8
entries including /index.html. What is left for a cold client is the case where the first visit is
online but incomplete: the shell and worker arrive, one precached asset does not.

That is the only version of "cold bootstrap" the product can be responsible for, because it is the only
one where bytes were reachable. So I measure it:

  mode partial   /index.html, /v10-sw.js, manifest and most assets 200; ONE asset (the css) -> 500
  mode clean     everything 200 (the control: the same install without the failure)

Readings per mode, all from the browser: precache cache name + entry count + which URLs are actually in
it (compared against the worker's own manifest), registrations, controller, unhandled rejections from the
worker scope, and then -- after killing the site -- what an ordinary navigation renders and which
sub-resource requests fail.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
import time
import socketserver

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0267_20260923")
OUT = WORK / "genB_baseline"
DIST = LANE / "frontend" / "dist_ord0267b"
PORT = int(os.environ.get("CNX_PARTIAL_PORT", "8446"))
BROKEN = os.environ.get("CNX_BROKEN_HINT", "css")   # css | sw | none | nonmember


def precached_urls() -> set:
    """The worker's own list, so 'member' is its definition and not mine."""
    sw = (DIST / "v10-sw.js").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"precacheAndRoute\(([\s\S]*?)\)", sw)
    seg = m.group(1) if m else ""
    return set(re.findall(r"""url:\s*["']([^"']+)["']""", seg))


def _posix(f: pathlib.Path) -> str:
    return "/" + f.relative_to(DIST).as_posix()


PRECACHED = precached_urls()
if BROKEN == "nonmember" and not PRECACHED:
    raise SystemExit("ABORT: the worker's precache list parsed empty; without it 'non-member' is a guess")
# the worker's own list is `assets/x.js` with no leading slash; _posix() adds one
NONMEMBER = next((_posix(f) for f in sorted((DIST / "assets").iterdir())
                  if f.suffix.lower() in (".js", ".css")
                  and _posix(f).lstrip("/") not in PRECACHED), None)
LOG = OUT / f"partial_origin_{BROKEN}.log"
STATE = {"hits": 0, "failed": 0}


def serve():
    class H(socketserver.StreamRequestHandler):
        def log_message(self, *a):
            pass

        def handle(self):
            line = self.rfile.readline().decode("latin-1", "replace").strip()
            parts = line.split()
            if len(parts) < 2:
                return
            path = parts[1].split("?")[0]
            while True:
                if not self.rfile.readline().decode("latin-1", "replace").strip():
                    break
            rel = path.lstrip("/") or "index.html"
            f = DIST / rel
            if path.startswith("/api/"):
                body = b'{"status":"ok"}'
                ctype, code = "application/json", 200
            elif f.exists() and f.is_file():
                body = f.read_bytes()
                suffix = f.suffix.lower()
                ctype = {".js": "text/javascript", ".css": "text/css", ".html": "text/html; charset=utf-8",
                         ".svg": "image/svg+xml", ".webmanifest": "application/manifest+json",
                         ".png": "image/png"}.get(suffix, "application/octet-stream")
                broken = ((suffix == ".css" and BROKEN == "css") or (suffix == ".js" and BROKEN == "js")
                          or (rel == "v10-sw.js" and BROKEN == "sw")
                          or (BROKEN == "nonmember" and NONMEMBER
                              and path.lstrip("/") == NONMEMBER.lstrip("/")))
                if broken:
                    body, code, ctype = b"origin exploded", 500, "text/plain"
                    STATE["failed"] += 1
                else:
                    code = 200
            else:
                if not f.suffix:
                    # an instrument without a navigation fallback invents its own defect: a deep link
                    # must reach the shell the way vite preview / the real host delivers it
                    body = (DIST / "index.html").read_bytes()
                    code, ctype = 200, "text/html; charset=utf-8"
                else:
                    body, code, ctype = b"not here", 404, "text/plain"
            STATE["hits"] += 1
            self.wfile.write(f"HTTP/1.1 {code} X\r\nContent-Type: {ctype}\r\n"
                             f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode("latin-1"))
            self.wfile.write(body)
            with LOG.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"path": path, "code": code, "bytes": len(body),
                                     "at": time.strftime("%H:%M:%S")}) + "\n")

    class S(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    with S(("127.0.0.1", PORT), H) as srv:
        print(f"partial origin on 127.0.0.1:{PORT} failing={BROKEN}", flush=True)
        print(f"members per the worker ({len(PRECACHED)}): {sorted(PRECACHED)}", flush=True)
        print(f"non-member used by the fourth arm: {NONMEMBER}", flush=True)
        srv.serve_forever(600)


if __name__ == "__main__":
    LOG.unlink(missing_ok=True)
    serve()
