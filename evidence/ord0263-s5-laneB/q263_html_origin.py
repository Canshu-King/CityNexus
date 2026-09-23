"""A 200-with-an-HTML-body origin, plus a write leg that never settles.

Not a browser mock: a real HTTP server on my own port, answering real bytes, so the fact under test
("the origin answered 2xx and what came back was a document, not this screen's data") is produced the
way production produces it -- a deployment layer serving index.html where the API should have been.

  GET  /api/v1/health        -> 200 application/json (a healthy-looking probe, the case that keeps the lie)
  GET  /api/v1/anything-else -> 200 text/html, a real shell document
  POST /api/v1/anything      -> accept, never respond (an in-flight write that hangs)
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[sys.argv.index("--port") + 1])
SHELL = ("<!doctype html><html><head><meta charset=\"utf-8\"><title>CityNexus</title></head>"
         "<body><div id=\"root\"></div><script src=\"/assets/index-Cpy_jhEg.js\"></script></body></html>")
counts = {"health_json": 0, "html_for_api_get": 0, "post_hanging": 0}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, ctype, body):
        b = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/api/"):
            if self.path.rstrip("/").endswith("/health"):
                counts["health_json"] += 1
                self._send(200, "application/json", json.dumps({"status": "ok", "version": "ord0263-s5"}))
            else:
                counts["html_for_api_get"] += 1
                self._send(200, "text/html;charset=utf-8", SHELL)
            return
        self._send(200, "text/html;charset=utf-8", SHELL)

    def do_POST(self):  # noqa: N802
        counts["post_hanging"] += 1
        with open(f"D:/moodle/_qoder_b_ord0263_20260923/s5_counts.json", "w", encoding="utf-8") as fh:
            json.dump(counts, fh, ensure_ascii=False)
        threading.Event().wait()


srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
print(f"html-answer origin on 127.0.0.1:{PORT}: /api/*/health->200 json, other api GET->200 html, POST->hang",
      flush=True)
srv.serve_forever()
