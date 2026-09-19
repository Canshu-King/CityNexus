"""The authoritative frontend E2E gate trusts /health only if it echoes the
token of the run that started the server.  These tests pin both halves of that
promise: a server nobody stamped says so, and the value a suite passes through
its own process environment is the value the browser sees.
"""

from fastapi.testclient import TestClient

import app.main as main
from app.core.config import Settings


def test_health_does_not_claim_a_run_id_it_was_never_given():
    client = TestClient(main.app)
    body = client.get("/api/v1/health").json()
    # A backend from another checkout/lane has no token, so it can never satisfy
    # the assertion the suite makes; the empty string is the safe default.
    assert body["e2e_run_id"] == ""


def test_health_echoes_the_token_of_the_process_that_started_it(monkeypatch):
    monkeypatch.setattr(main, "settings", Settings(e2e_run_id="run-20260919-p13"))
    body = TestClient(main.app).get("/api/v1/health").json()
    assert body["e2e_run_id"] == "run-20260919-p13"
    assert body["status"] == "ok"


def test_health_reports_which_database_this_process_opened(monkeypatch):
    monkeypatch.setattr(main, "settings", Settings(e2e_run_id="run-x"))
    body = TestClient(main.app).get("/api/v1/health").json()
    # The suite also asserts on this, so a run cannot silently read a shared file.
    assert body["database_url"].startswith("sqlite:///")
