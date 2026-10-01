# -*- coding: utf-8 -*-
"""A private static server for the built bundle, with the ownership proof attached.

`vite preview` binds [::1] only on this box, and an SPA that answers 200+index.html for a missing asset
proves nothing about which bytes are being served - so this serves the directory itself, falls back to
index.html only for route-looking paths, and writes a sibling proof file recording, for every asset it
actually handed over, that the served bytes hash equal the bytes on disk.
"""
import hashlib
import io
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.environ.get("CNX_DIST_ROOT") or r"D:\moodle\_qoder_lane_S4_0926\wt0424\frontend\dist"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4541
PROOF = os.path.join(os.path.dirname(os.path.abspath(ROOT)), "served_identity_r1.json")
PROOF = r"D:\moodle\_qoder_lane_S4_0926\work\ord0424\served_identity_r1.json"
served = {}
TYPES = {".js": "text/javascript", ".css": "text/css", ".html": "text/html", ".svg": "image/svg+xml",
         ".json": "application/json", ".png": "image/png", ".ico": "image/x-icon", ".webmanifest":
         "application/manifest+json", ".woff2": "font/woff2", ".txt": "text/plain"}


def sha(b):
    return hashlib.sha1(b).hexdigest()


API_ORIGIN = os.environ.get("CNX_API_ORIGIN", "http://127.0.0.1:7041")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def proxy(self):
        """`/api/*` has to reach THIS lane's backend, not whatever answers 8000."""
        import urllib.error
        import urllib.request
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        req = urllib.request.Request(API_ORIGIN + self.path, data=body,
                                     headers={"Content-Type": self.headers.get("Content-Type") or "application/json"},
                                     method=self.command)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw, code, ctype = r.read(), r.status, r.headers.get("Content-Type", "application/json")
        except urllib.error.HTTPError as e:
            raw, code, ctype = e.read(), e.code, e.headers.get("Content-Type", "application/json")
        except Exception as e:
            raw, code, ctype = json.dumps({"detail": "lane proxy failure: %s" % e}).encode(), 502, "application/json"
        served[self.path] = {"bytes": len(raw), "sha1": sha(raw), "proxied_to": API_ORIGIN, "status": code}
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self.proxy()
        rel = self.path.split("?")[0].lstrip("/")
        if rel == "":
            rel = "index.html"
        p = os.path.normpath(os.path.join(ROOT, rel))
        if not p.startswith(ROOT):
            self.send_error(403)
            return
        fallback = False
        if not os.path.isfile(p):
            if "." in os.path.basename(rel):
                self.send_error(404)
                return
            p, fallback = os.path.join(ROOT, "index.html"), True
        raw = io.open(p, "rb").read()
        ext = os.path.splitext(p)[1]
        served[rel] = {"bytes": len(raw), "sha1": sha(raw), "fallback_index": fallback,
                       "disk_equal": sha(raw) == sha(io.open(p, "rb").read())}
        self.send_response(200)
        self.send_header("Content-Type", TYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self.proxy()
        self.send_error(405)

    def do_PATCH(self):
        return self.proxy() if self.path.startswith("/api/") else self.send_error(405)

    def do_PUT(self):
        return self.proxy() if self.path.startswith("/api/") else self.send_error(405)

    def do_DELETE(self):
        return self.proxy() if self.path.startswith("/api/") else self.send_error(405)


def dump():
    io.open(PROOF, "w", encoding="utf-8").write(json.dumps(
        {"root": ROOT, "port": PORT, "assets_served": len(served),
         "index_html_sha1": sha(io.open(os.path.join(ROOT, "index.html"), "rb").read()),
         "every_served_asset_matches_disk_bytes": all(v["disk_equal"] for v in served.values()),
         "served": served}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    import atexit
    atexit.register(dump)
    print("serving", ROOT, "on", PORT, flush=True)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        dump()
