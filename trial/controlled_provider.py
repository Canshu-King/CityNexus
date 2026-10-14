"""Loopback-only source-labelled TEST_PROVIDER for a human Revolution first look.

Not a live provider and not real OSM proof. Never bind to a public interface.
"""
from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


CITY_PORT = int(os.environ.get("REV_TRIAL_CITY_PORT", "18202"))
OVERPASS_PORT = int(os.environ.get("REV_TRIAL_OVERPASS_PORT", "18203"))


class TrialHandler(BaseHTTPRequestHandler):
    provider_kind = "unknown"

    def log_message(self, format, *args):  # noqa: A002
        # Do not log raw URLs/query strings, exact map centers, or bearer tokens.
        pass

    def _json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/status":
            self._json(200, {"provider": self.provider_kind, "grade": "TEST_PROVIDER",
                             "live": False, "loopback_only": True})
            return
        if self.provider_kind == "city" and path == "/search":
            query = parse_qs(urlparse(self.path).query).get("q", [""])[0]
            if "shanghai" not in query.casefold() and "上海" not in query:
                self._json(200, [])
                return
            self._json(200, [{
                "place_id": 107001, "osm_type": "relation", "osm_id": 107001,
                "lat": "31.2304", "lon": "121.4737",
                "display_name": "Shanghai, China (CONTROLLED TEST RESPONSE)",
                "type": "city", "class": "place",
            }])
            return
        self._json(404, {"error": "TEST_PROVIDER_ROUTE_NOT_FOUND"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if self.provider_kind != "overpass" or path != "/api/interpreter":
            self._json(404, {"error": "TEST_PROVIDER_ROUTE_NOT_FOUND"})
            return
        # Discard the bounded Overpass query. This fixture never contacts a public service.
        try:
            count = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"error": "INVALID_LENGTH"})
            return
        if count < 0 or count > 200000:
            self._json(413, {"error": "QUERY_TOO_LARGE"})
            return
        self.rfile.read(count)
        self._json(200, {
            "version": 0.6,
            "generator": "CityNexus Revolution HANDS-ON CONTROLLED TEST_PROVIDER",
            "elements": [
                {"type": "node", "id": 107011, "lat": 31.2304, "lon": 121.4737,
                 "tags": {"name": "SAMPLE ONLY - Revolution Museum", "tourism": "museum"}},
                {"type": "node", "id": 107012, "lat": 31.231, "lon": 121.474,
                 "tags": {"name": "SAMPLE ONLY - Revolution Gallery", "tourism": "gallery"}},
                {"type": "node", "id": 107013, "lat": 31.2315, "lon": 121.4745,
                 "tags": {"name": "SAMPLE ONLY - Revolution Park", "leisure": "park"}},
            ],
        })


class CityHandler(TrialHandler):
    provider_kind = "city"


class OverpassHandler(TrialHandler):
    provider_kind = "overpass"


def main() -> None:
    servers = [
        ThreadingHTTPServer(("127.0.0.1", CITY_PORT), CityHandler),
        ThreadingHTTPServer(("127.0.0.1", OVERPASS_PORT), OverpassHandler),
    ]
    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    print(
        f"CONTROLLED TEST_PROVIDER ONLY: city=127.0.0.1:{CITY_PORT} "
        f"overpass=127.0.0.1:{OVERPASS_PORT}; no public-provider calls",
        flush=True,
    )
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
