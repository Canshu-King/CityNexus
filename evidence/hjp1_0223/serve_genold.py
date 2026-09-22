#!/usr/bin/env python3
"""Throwaway static+API-proxy for HJ-P1 ORD-0207 (binds 127.0.0.1 only, reads a private dist copy).

Purpose: walk the real production build against MY OWN one-off database copy, so nothing I click
can touch the shared preview library or the user's live data.
"""
import http.client
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist5")
API_HOST, API_PORT = "127.0.0.1", 8761
HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te",
       "trailers", "transfer-encoding", "upgrade", "host", "content-length"}


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *a):
        sys.stderr.write("%s %s\n" % (self.command, fmt % a))

    def _proxy(self):
        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length) if length else None
        c = http.client.HTTPConnection(API_HOST, API_PORT, timeout=120)
        hdrs = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
        c.request(self.command, self.path, body=body, headers=hdrs)
        r = c.getresponse()
        data = r.read()
        self.send_response(r.status, r.reason)
        for k, v in r.getheaders():
            if k.lower() not in HOP:
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)
        c.close()

    def do_GET(self):
        if urlsplit(self.path).path.startswith("/api/"):
            return self._proxy()
        p = os.path.normpath(os.path.join(DIST, urlsplit(self.path).path.lstrip("/")))
        if not p.startswith(DIST):
            return self.send_error(403, "outside dist")
        if os.path.isdir(p):
            p = os.path.join(p, "index.html")
        if not os.path.exists(p):
            p = os.path.join(DIST, "index.html")
        with open(p, "rb") as f:
            data = f.read()
        ext = os.path.splitext(p)[1].lower()
        ctype = {".html": "text/html", ".js": "text/javascript", ".css": "text/css",
                 ".json": "application/json", ".webmanifest": "application/manifest+json",
                 ".png": "image/png", ".svg": "image/svg+xml", ".jpg": "image/jpeg"}.get(ext, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    do_HEAD = do_GET
    do_POST = _proxy
    do_PATCH = _proxy
    do_PUT = _proxy
    do_DELETE = _proxy
    do_OPTIONS = _proxy


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8762
    print(json.dumps({"serves_dist": DIST, "proxies_api_to": f"http://{API_HOST}:{API_PORT}", "listen": f"127.0.0.1:{port}"}, ensure_ascii=False))
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
