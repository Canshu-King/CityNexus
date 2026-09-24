"""A fake origin that ANSWERS with well-formed error envelopes (read-only probe, lane C's own surface).

Why this exists: the格 I owe is "an answered error envelope really is classified VALID on the normal
path", and the only honest way to read that is to let the shipped bundle fetch, answer it with a real
envelope, and then read what the traveller actually sees. So:

  * the response body shape is the product's own frozen envelope - `{"error": {"code": ..., "message": ...}}`
    (V8Experience.tsx:209 reads `body.error.code`); nothing here invents a field;
  * the scenario is chosen by a file, so the app's own request path is untouched - I never call the
    classifier myself, the bundle does;
  * every request/response is appended to a JSONL so the receipt's server side is read from a log the
    origin wrote, not from my memory;
  * `/__probe/*` endpoints belong to THIS instrument only (scenario get/set, log path) and never match a
    product route; they exist so the probe can switch scenarios without restarting anything.

0 writes to any product DB: this process never opens a .db file at all.
"""
from __future__ import annotations

import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).parent
SCEN = HERE / "scenario.txt"
LOG = HERE / "origin_log.jsonl"
PORT = int(re.sub(r"\D", "", Path(__file__).with_suffix(".port").read_text().strip()
                  if Path(__file__).with_suffix(".port").exists() else "8611"))

# Each scenario is exactly what the product's own reader expects: status + {"error":{"code","message"}}.
ENVELOPES = {
    "404_journey_not_found": (404, {"error": {"code": "JOURNEY_NOT_FOUND",
                                              "message": "the journey this device was pointed at is gone"}}),
    "422_validation_error": (422, {"error": {"code": "VALIDATION_ERROR",
                                                  "message": "stay budget is missing"}}),
    "503_hydration_busy": (503, {"error": {"code": "HYDRATION_STORE_BUSY",
                                           "message": "the catalogue writer is busy"}}),
    "200_not_a_journey_at_all": (200, {"unexpected_root": ["not", "a", "projection"]}),
}
# the product asks these on boot; everything else on /api answers the same scenario
BOOT_ROUTES = re.compile(r"^/api/v1/(experience|travelers|journeys)")


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a) -> None:  # keep stderr clean
        pass

    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/__probe/scenario"):
            cur = SCEN.read_text(encoding="utf-8").strip() if SCEN.exists() else ""
            return self._send(200, json.dumps({"scenario": cur}).encode(), "application/json")
        scenario = SCEN.read_text(encoding="utf-8").strip() if SCEN.exists() else ""
        if not BOOT_ROUTES.match(self.path):
            # a product route the probe didn't script: say so loudly rather than fake an answer
            status, payload = 599, {"error": {"code": "PROBE_UNSPECIFIED_ROUTE", "message": self.path}}
        else:
            status, payload = ENVELOPES.get(scenario, (204, {}))
        raw = json.dumps(payload).encode()
        with LOG.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"t": round(time.time(), 3), "dir": "resp", "scenario": scenario,
                                 "method": "GET", "route": self.path, "status": status,
                                 "content_type": "application/json",
                                 "server_error_code": (payload.get("error") or {}).get("code"),
                                 "body_bytes": len(raw)}, ensure_ascii=False) + "\n")
        self._send(status, raw, "application/json")

    def do_POST(self) -> None:  # noqa: N802
        n = int(self.headers.get("Content-Length") or 0)
        raw_in = self.rfile.read(n) if n else b""
        if self.path.startswith("/__probe/scenario"):
            new = json.loads(raw_in.decode() or "{}").get("scenario", "")
            if new not in ENVELOPES and new != "":
                return self._send(400, b'{"error":"unknown scenario"}', "application/json")
            SCEN.write_text(new, encoding="utf-8", newline="\n")
            return self._send(200, json.dumps({"scenario": new}).encode(), "application/json")
        with LOG.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"t": round(time.time(), 3), "dir": "resp", "method": "POST",
                                 "route": self.path, "status": 599,
                                 "note": "POST from the app was not scripted by this probe"},
                                ensure_ascii=False) + "\n")
        self._send(501, b'{"error":{"code":"PROBE_UNSCRIPTED_POST"}}', "application/json")


def main() -> int:
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()  # blocks; killed by the probe teardown
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
