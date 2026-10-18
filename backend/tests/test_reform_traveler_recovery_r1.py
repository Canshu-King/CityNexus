"""Reform 2026-10-18, second baton: coming back after the credential is gone.

The 401 measured on the same day closed the cheap route (renewing an expired credential), so the way
back has to be a real re-authentication: a secret the person keeps, a digest and a lifecycle the
server keeps. These arms are the two callers the order asks for -- the owner with the secret, and
somebody else without it -- plus the refusals that make "used", "expired", "revoked" and "locked"
mean something rather than being words in a design note.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import traveler_principal
from app.core.config import settings
from app.db.models import TravelerRecoveryCredential
from app.db.session import SessionLocal, ensure_schema
from app.main import app

client = TestClient(app)
ensure_schema()

CREATE_PATH = "/api/v1/travelers"
SESSION_PATH = "/api/v1/travelers/session"
ISSUE = "/api/v1/travelers/{traveler_id}/recovery"
REDEEM = "/api/v1/travelers/recovery/redeem"
REVOKE = "/api/v1/travelers/{traveler_id}/recovery/{recovery_id}/revoke"
LONG_SECRET = uuid4().hex + uuid4().hex


@pytest.fixture(autouse=True)
def _signing(monkeypatch):
    monkeypatch.setattr(
        traveler_principal, "settings", replace(settings, traveler_auth_secret=LONG_SECRET)
    )


def _traveller(name: str) -> dict:
    answer = client.post(
        CREATE_PATH,
        json={"display_name": name, "locale": "zh-CN", "timezone": "Asia/Shanghai"},
    )
    assert answer.status_code == 201, answer.text
    return answer.json()


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _issue(traveller: dict) -> dict:
    answer = client.post(
        ISSUE.format(traveler_id=traveller["id"]), headers=_bearer(traveller["access_token"])
    )
    assert answer.status_code == 201, answer.text
    return answer.json()


def _snapshot(credential_id: str) -> dict:
    with SessionLocal() as session:
        row = session.get(TravelerRecoveryCredential, credential_id)
        assert row is not None
        return {
            "digest": row.digest,
            "traveler_id": row.traveler_id,
            "expires_at": row.expires_at,
            "used_at": row.used_at,
            "revoked_at": row.revoked_at,
            "failed_attempts": row.failed_attempts,
            "locked_until": row.locked_until,
        }


def _redeem(issued: dict, secret: str | None = None):
    return client.post(
        REDEEM,
        json={
            "recovery_id": issued["recovery_id"],
            "recovery_secret": issued["recovery_secret"] if secret is None else secret,
        },
    )


def test_r1_issue_needs_the_travellers_own_live_credential() -> None:
    a = _traveller("Recovery A")
    b = _traveller("Recovery B")
    assert client.post(ISSUE.format(traveler_id=a["id"])).status_code == 401

    foreign = client.post(
        ISSUE.format(traveler_id=a["id"]), headers=_bearer(b["access_token"])
    )
    assert foreign.status_code == 403, foreign.text
    assert foreign.json()["error"]["reason_code"] == traveler_principal.REASON_TRAVELER_NOT_PRINCIPAL

    issued = client.post(ISSUE.format(traveler_id=a["id"]), headers=_bearer(a["access_token"]))
    assert issued.status_code == 201, issued.text
    assert issued.headers["cache-control"] == "private, no-store"
    body = issued.json()
    assert body["shown_once"] is True
    assert len(body["recovery_secret"]) >= 32

    stored = _snapshot(body["recovery_id"])
    assert stored["traveler_id"] == a["id"]
    assert len(stored["digest"]) == 64
    assert stored["digest"] != body["recovery_secret"]
    assert body["recovery_secret"] not in str(stored), "the secret itself must never be stored"


def test_r2_the_owner_redeems_and_the_new_session_speaks_for_them() -> None:
    a = _traveller("Recovery A")
    issued = _issue(a)
    redeemed = _redeem(issued)
    assert redeemed.status_code == 200, redeemed.text
    assert redeemed.headers["cache-control"] == "private, no-store"
    body = redeemed.json()
    assert body["traveler_id"] == a["id"]
    assert body["session_state"] == "SIGNED"
    assert body["auth_method"] == "recovery_credential"

    session = client.get(SESSION_PATH, headers=_bearer(body["access_token"]))
    assert session.status_code == 200, session.text
    assert session.json()["traveler_id"] == a["id"]


def test_r3_a_wrong_secret_is_refused_and_repeated_guesses_lock_the_credential() -> None:
    a = _traveller("Recovery A")
    issued = _issue(a)
    for _ in range(5):
        wrong = _redeem(issued, secret="x" * 40)
        assert wrong.status_code == 401, wrong.text
        assert wrong.json()["error"]["reason_code"] == "RECOVERY_SECRET_MISMATCH"
    locked = _redeem(issued)
    assert locked.status_code == 429, locked.text
    assert locked.json()["error"]["reason_code"] == "RECOVERY_LOCKED"
    assert _snapshot(issued["recovery_id"])["used_at"] is None, "a lock must not consume the credential"


def test_r4_a_used_credential_cannot_be_replayed() -> None:
    a = _traveller("Recovery A")
    issued = _issue(a)
    assert _redeem(issued).status_code == 200
    replay = _redeem(issued)
    assert replay.status_code == 401, replay.text
    assert replay.json()["error"]["reason_code"] == "RECOVERY_USED"


def test_r5_an_expired_credential_is_refused() -> None:
    a = _traveller("Recovery A")
    issued = _issue(a)
    with SessionLocal() as session:
        row = session.get(TravelerRecoveryCredential, issued["recovery_id"])
        assert row is not None
        row.expires_at = "2020-01-01T00:00:00+00:00"
        session.commit()
    answer = _redeem(issued)
    assert answer.status_code == 401, answer.text
    assert answer.json()["error"]["reason_code"] == "RECOVERY_EXPIRED"


def test_r6_only_the_owner_can_revoke_and_a_revoked_credential_is_dead() -> None:
    a = _traveller("Recovery A")
    b = _traveller("Recovery B")
    issued = _issue(a)
    foreign = client.post(
        REVOKE.format(traveler_id=a["id"], recovery_id=issued["recovery_id"]),
        headers=_bearer(b["access_token"]),
    )
    assert foreign.status_code == 403, foreign.text

    revoked = client.post(
        REVOKE.format(traveler_id=a["id"], recovery_id=issued["recovery_id"]),
        headers=_bearer(a["access_token"]),
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["revoked"] is True

    answer = _redeem(issued)
    assert answer.status_code == 401, answer.text
    assert answer.json()["error"]["reason_code"] == "RECOVERY_REVOKED"


def test_r7_the_id_alone_is_not_a_credential() -> None:
    a = _traveller("Recovery A")
    issued = _issue(a)
    short = _redeem(issued, secret="short")
    assert short.status_code == 422, short.text
    unknown = client.post(
        REDEEM, json={"recovery_id": str(uuid4()), "recovery_secret": "y" * 40}
    )
    assert unknown.status_code == 401, unknown.text
    assert unknown.json()["error"]["reason_code"] == "RECOVERY_UNKNOWN"
