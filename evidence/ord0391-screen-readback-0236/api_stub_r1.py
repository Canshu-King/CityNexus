# -*- coding: utf-8 -*-
"""ORD-0391 screen read-back - a scenario switch in front of this lane's own backend.

The 23 lines ORD-0391 reworded are the sentences a screen shows when a request goes wrong, so taking a
reading means producing each of those wrong answers on purpose. Nothing in the product is edited to do
it: this proxy sits between my static front door (:4541) and my backend (:7041) and, for the routes a
scenario names, answers with a canned response instead of forwarding. Every other request goes through
unchanged, so the rest of the app still behaves like the real thing.

  GET  /__scenario            -> the scenario in force and its rules
  POST /__scenario            -> {"name": "<scenario>"} switches it; the answer echoes what is now live

A scenario can therefore be proven to have landed before any screen reading is trusted.
"""
import http.client
import io
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = "127.0.0.1"
UPSTREAM_PORT = 7041
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 7042
RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scenarios_r1.json")

with io.open(RULES_PATH, encoding="utf-8") as fh:
    SPEC = json.load(fh)

STATE = {"scenario": SPEC.get("default", "off"), "switches": []}
HOP_BY_HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te",
              "trailers", "transfer-encoding", "content-length", "host"}


def current():
    return SPEC["scenarios"][STATE["scenario"]]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "cnx-ord0391-stub/1"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.log_date_time_string(), fmt % args))
        sys.stderr.flush()

    def _json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _match(self, method, path):
        for rule in current().get("rules", []):
            if rule["method"] not in ("*", method):
                continue
            if re.search(rule["path"], path):
                return rule
        return None

    def _canned(self, rule):
        res = rule["response"]
        body = res.get("body", "")
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        raw = body.encode("utf-8")
        self.send_response(res["status"])
        self.send_header("Content-Type", res.get("content_type", "application/json"))
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Cnx-Stub-Scenario", STATE["scenario"])
        self.end_headers()
        self.wfile.write(raw)

    def _forward(self):
        length = int(self.headers.get("Content-Length") or 0)
        payload = self.rfile.read(length) if length else None
        conn = http.client.HTTPConnection(UPSTREAM, UPSTREAM_PORT, timeout=60)
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP_BY_HOP}
        try:
            conn.request(self.command, self.path, body=payload, headers=headers)
            res = conn.getresponse()
            raw = res.read()
            self.send_response(res.status, res.reason)
            for k, v in res.getheaders():
                if k.lower() not in HOP_BY_HOP:
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except Exception as exc:  # the upstream is mine; a failure here is a fact, not a fallback
            self._json(502, {"code": "STUB_UPSTREAM_UNREACHABLE", "detail": "%s: %s"
                             % (type(exc).__name__, str(exc)[:200])})
        finally:
            conn.close()

    def do_GET(self):
        if self.path == "/__scenario":
            return self._json(200, {"scenario": STATE["scenario"], "spec": current(),
                                    "switches": STATE["switches"][-8:]})
        rule = self._match("GET", self.path)
        if rule:
            return self._canned(rule)
        return self._forward()

    def do_POST(self):
        if self.path == "/__scenario":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                name = json.loads(raw.decode("utf-8")).get("name")
            except Exception:
                return self._json(400, {"code": "STUB_BAD_SWITCH_BODY"})
            if name not in SPEC["scenarios"]:
                return self._json(400, {"code": "STUB_UNKNOWN_SCENARIO", "named": name,
                                        "known": sorted(SPEC["scenarios"])})
            STATE["scenario"] = name
            STATE["switches"].append({"to": name, "at": self.log_date_time_string()})
            return self._json(200, {"scenario": STATE["scenario"], "spec": current()})
        rule = self._match("POST", self.path)
        if rule:
            return self._canned(rule)
        return self._forward()

    do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_GET


def main():
    print(json.dumps({"stub_port": PORT, "upstream": "%s:%s" % (UPSTREAM, UPSTREAM_PORT),
                      "scenarios": sorted(SPEC["scenarios"]), "default": STATE["scenario"],
                      "rules_file": RULES_PATH}, ensure_ascii=False), flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


raise SystemExit(main())
