"""ORD-0685 -- the traveller principal: who is this request speaking for?

The door this file pins is the one the Copilot cache fix (Issue 27) could not find: nothing on
the authoritative line could answer "which traveller is this", so the only safe cache was none.
These tests hold the answer to four rules the order names:

* a signed token answers the traveller it names, and nothing else;
* no token, a forged token, and an expired token are three different named refusals -- not one
  undifferentiated 401 sentence (the envelope's `error.reason_code` is what the screen reads);
* an unconfigured verifier refuses with its own name instead of accepting an unverifiable
  identity;
* the running app's own contract carries the path with `GET` and no other method.

The secret used here is generated at run time, never written into the tree: a credential-shaped
literal in a test file is exactly what ORD-0307's startup gate scans for.
"""

from __future__ import annotations

import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import yaml
from fastapi.testclient import TestClient

from app import traveler_principal
from app.core.config import settings
from app.db.models import Traveler
from app.db.session import SessionLocal, ensure_schema
from app.main import app

client = TestClient(app)
ensure_schema()

SECRET = uuid4().hex + uuid4().hex  # 64 hex chars, generated per run
SESSION_PATH = "/api/v1/travelers/session"


def _traveler() -> str:
    traveler_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        session.add(
            Traveler(
                id=traveler_id,
                display_name="ORD-0685 probe",
                email=None,
                locale="zh-CN",
                timezone="Asia/Shanghai",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    return traveler_id


def _configured(monkeypatch) -> None:
    monkeypatch.setattr(
        traveler_principal, "settings", replace(settings, traveler_auth_secret=SECRET)
    )


def test_a_signed_token_answers_the_traveller_it_names(monkeypatch):
    _configured(monkeypatch)
    traveler_id = _traveler()
    token = traveler_principal.issue_traveler_token(traveler_id)

    answer = client.get(SESSION_PATH, headers={"Authorization": f"Bearer {token}"})

    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["traveler_id"] == traveler_id
    assert body["auth_method"] == "SIGNED_HMAC_BEARER"
    assert isinstance(body["expires_at"], int) and body["expires_at"] > int(time.time())
    # A principal is per-person and per-request; a shared cache keeping it would be a leak.
    assert answer.headers["Cache-Control"] == "private, no-store"
    assert "Authorization" in answer.headers["Vary"]


def test_the_explicit_header_is_accepted_too(monkeypatch):
    _configured(monkeypatch)
    traveler_id = _traveler()
    token = traveler_principal.issue_traveler_token(traveler_id)

    answer = client.get(SESSION_PATH, headers={"X-CityNexus-Traveler-Token": token})

    assert answer.status_code == 200, answer.text
    assert answer.json()["traveler_id"] == traveler_id


def test_no_credentials_is_a_named_refusal(monkeypatch):
    _configured(monkeypatch)
    answer = client.get(SESSION_PATH)

    assert answer.status_code == 401, answer.text
    assert answer.json()["error"]["reason_code"] == "TRAVELER_CREDENTIALS_MISSING"


def test_a_token_signed_with_another_secret_is_invalid(monkeypatch):
    _configured(monkeypatch)
    traveler_id = _traveler()
    with monkeypatch.context() as patch:
        patch.setattr(
            traveler_principal, "settings",
            replace(settings, traveler_auth_secret=uuid4().hex + uuid4().hex),
        )
        forged = traveler_principal.issue_traveler_token(traveler_id)

    answer = client.get(SESSION_PATH, headers={"Authorization": f"Bearer {forged}"})

    assert answer.status_code == 401, answer.text
    assert answer.json()["error"]["reason_code"] == "TRAVELER_CREDENTIALS_INVALID"


def test_an_expired_token_names_expiry(monkeypatch):
    _configured(monkeypatch)
    traveler_id = _traveler()
    token = traveler_principal.issue_traveler_token(
        traveler_id, ttl_seconds=60, now=int(time.time()) - 120
    )

    answer = client.get(SESSION_PATH, headers={"Authorization": f"Bearer {token}"})

    assert answer.status_code == 401, answer.text
    assert answer.json()["error"]["reason_code"] == "TRAVELER_CREDENTIALS_EXPIRED"


def test_an_unconfigured_verifier_refuses_by_name(monkeypatch):
    monkeypatch.setattr(
        traveler_principal, "settings", replace(settings, traveler_auth_secret=None)
    )
    answer = client.get(SESSION_PATH, headers={"Authorization": "Bearer anything"})

    assert answer.status_code == 503, answer.text
    assert answer.json()["error"]["reason_code"] == "TRAVELER_AUTH_NOT_CONFIGURED"


def test_the_running_contract_carries_the_path_with_get_only():
    spec = client.get("/openapi.json").json()
    path = spec["paths"][SESSION_PATH]

    assert set(path.keys()) == {"get"}, path.keys()


def test_the_committed_contract_carries_the_path_with_get_only():
    contract = Path(__file__).resolve().parents[2] / "contracts" / "openapi.yaml"
    spec = yaml.safe_load(contract.read_text(encoding="utf-8"))

    assert "/travelers/session" in spec["paths"]
    assert set(spec["paths"]["/travelers/session"].keys()) == {"get"}
