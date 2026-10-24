"""A stub chat-completions endpoint that always answers 503, so the product's own recovery row can be pressed for real.

Deliberately narrow: it is a fault injector for one verification (the traveller's 「重试这一轮」 on the dock
must be reachable and work when the model door is down), not a product path.  Nothing reads a key here and
nothing is written to disk; every request is echoed to stdout so the receipt can say what actually happened.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(__import__("os").environ.get("STUB_PORT", "7899"))
seen = []


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length)
        seen.append((self.path, len(body)))
        print("STUB_HIT %s bytes=%d answering 503" % (self.path, len(body)), flush=True)
        payload = json.dumps({"error": {"message": "stub: upstream unavailable", "type": "server_error"}}).encode()
        self.send_response(503)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        print("STUB_PING %s" % self.path, flush=True)
        self.send_response(200)
        self.send_header("content-length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        return


print("STUB_LISTEN 127.0.0.1:%d" % PORT, flush=True)
HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
