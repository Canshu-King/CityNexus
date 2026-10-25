# ruff: noqa: F811 -- pytest fixture arguments use imported fixture names
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
import socket
import threading
import time
from uuid import uuid4

import httpx
import uvicorn
from sqlalchemy import select

from test_issue47_private_reads import stack  # noqa: F401
from app import demo_pairing, traveler_principal
from app.db.session import get_session


@contextmanager
def proxied(app):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", lifespan="off"))
    worker = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    worker.start()
    deadline = time.monotonic() + 5
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.01)
    assert server.started

    class Proxy(BaseHTTPRequestHandler):
        def forward(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            # A LAN-facing development proxy forwards to a loopback backend and omits Origin.
            headers = {
                k: v
                for k, v in self.headers.items()
                if k.lower() not in {"host", "origin", "connection"}
            }
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request(self.command, self.path, body=body or None, headers=headers)
            response = conn.getresponse()
            data = response.read()
            self.send_response(response.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            conn.close()

        do_GET = forward
        do_POST = forward

        def log_message(self, *args):
            pass

    proxy = ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
    proxy_worker = threading.Thread(target=proxy.serve_forever, daemon=True)
    proxy_worker.start()
    try:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{proxy.server_port}", trust_env=False
        ) as client:
            yield client
    finally:
        proxy.shutdown()
        proxy.server_close()
        proxy_worker.join(3)
        server.should_exit = True
        worker.join(5)
        sock.close()


def test_real_proxy_cannot_mint_owner_and_pairing_is_single_use(stack, monkeypatch):
    client, ids, path = stack
    client.app.include_router(demo_pairing.router)
    monkeypatch.setenv("CITYNEXUS_DEMO_DATABASE_PATH", str(path.resolve()))
    key = uuid4().hex + uuid4().hex
    monkeypatch.setenv("CITYNEXUS_DEMO_PRESENTER_KEY", key)
    with proxied(client.app) as proxy:
        assert proxy.get("/api/v1/demo/session").status_code == 403
        assert (
            proxy.get("/api/v1/demo/session", headers={"X-Forwarded-For": "127.0.0.1"}).status_code
            == 403
        )
        body = {"journey_id": ids["journey"]}
        assert proxy.post("/api/v1/demo/pairing", json=body).status_code == 403
        issued = proxy.post(
            "/api/v1/demo/pairing", json=body, headers={"X-CityNexus-Presenter-Key": key}
        )
        assert issued.status_code == 201, issued.text
        ticket = issued.json()["ticket"]
        paired = proxy.post("/api/v1/demo/pairing/redeem", json={"ticket": ticket})
        assert paired.status_code == 200, paired.text
        assert paired.json()["expires_in"] == 900
        assert proxy.post("/api/v1/demo/pairing/redeem", json={"ticket": ticket}).status_code == 401
        signed = proxy.get(
            "/api/v1/journeys/" + ids["journey"],
            headers={"Authorization": "Bearer " + paired.json()["access_token"]},
        )
        assert signed.status_code == 200, signed.text
        assert key not in paired.text
    db = client.app.dependency_overrides[get_session]()
    s = next(db)
    row = s.scalar(select(demo_pairing.DemoPairingTicket))
    assert row.ticket_sha256 != ticket and len(row.ticket_sha256) == 64
    assert row.consumed_at is not None
    db.close()


def test_pairing_expiry_and_rate_limit(stack, monkeypatch):
    client, ids, path = stack
    client.app.include_router(demo_pairing.router)
    monkeypatch.setenv("CITYNEXUS_DEMO_DATABASE_PATH", str(path.resolve()))
    key = uuid4().hex + uuid4().hex
    monkeypatch.setenv("CITYNEXUS_DEMO_PRESENTER_KEY", key)
    issued = client.post(
        "/api/v1/demo/pairing",
        json={"journey_id": ids["journey"]},
        headers={"X-CityNexus-Presenter-Key": key},
    )
    ticket = issued.json()["ticket"]
    db = client.app.dependency_overrides[get_session]()
    s = next(db)
    row = s.scalar(select(demo_pairing.DemoPairingTicket))
    row.expires_at = int(time.time()) - 1
    s.commit()
    db.close()
    assert client.post("/api/v1/demo/pairing/redeem", json={"ticket": ticket}).status_code == 401
    for _ in range(19):
        assert (
            client.post(
                "/api/v1/demo/pairing/redeem", json={"ticket": "invalid-ticket-" + "x" * 32}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/v1/demo/pairing/redeem", json={"ticket": "invalid-ticket-" + "x" * 32}
        ).status_code
        == 429
    )


def test_collection_reads_do_not_disclose_other_travelers(stack):
    client, ids, path = stack
    for url in ("/api/v1/journeys", "/api/v1/recycle-bin/journeys"):
        assert client.get(url).status_code == 401
        stranger = {
            "Authorization": "Bearer " + traveler_principal.issue_traveler_token(ids["stranger"])
        }
        assert client.get(url, headers=stranger).json() == []
    owner = {"Authorization": "Bearer " + traveler_principal.issue_traveler_token(ids["owner"])}
    response = client.get("/api/v1/journeys", headers=owner)
    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()] == [ids["journey"]]


def test_competing_pairing_redemption_only_one_succeeds(stack, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    client, ids, path = stack
    client.app.include_router(demo_pairing.router)
    monkeypatch.setenv("CITYNEXUS_DEMO_DATABASE_PATH", str(path.resolve()))
    key = uuid4().hex + uuid4().hex
    monkeypatch.setenv("CITYNEXUS_DEMO_PRESENTER_KEY", key)
    response = client.post(
        "/api/v1/demo/pairing",
        json={"journey_id": ids["journey"]},
        headers={"X-CityNexus-Presenter-Key": key},
    )
    ticket = response.json()["ticket"]

    def redeem(_):
        return client.post("/api/v1/demo/pairing/redeem", json={"ticket": ticket}).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(redeem, range(2))) == [200, 401]
