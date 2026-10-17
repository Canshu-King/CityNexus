"""Issue #33 Q1 -- the renewal door, and the four ways it must refuse.

Issue #31 A gave a traveller a credential and then left them nowhere to go with it: tokens are
short-lived on purpose, and when one lapsed the tab had no way back, even though the trips on the
server were still that person's.  This is the smallest door that closes that gap -- and the night
order's condition for it was explicit: *no bare id or uuid may be exchanged for a token.*

So the tests are mostly about refusal.  Each one names the reason code the screen branches on,
because "sign in again", "this build has no identity" and "that credential was forged" are three
different things to a person holding a phone.
"""

from __future__ import annotations

import time
from dataclasses import replace
from uuid import uuid4

from fastapi.testclient import TestClient

from app import traveler_principal
from app.core.config import settings
from app.db.session import ensure_schema
from app.main import app

client = TestClient(app)
ensure_schema()

CREATE_PATH = "/api/v1/travelers"
SESSION_PATH = "/api/v1/travelers/session"
REFRESH_PATH = "/api/v1/travelers/session/refresh"
LONG_SECRET = uuid4().hex + uuid4().hex


def _use_secret(monkeypatch, secret: str | None = LONG_SECRET) -> None:
    monkeypatch.setattr(
        traveler_principal, "settings", replace(settings, traveler_auth_secret=secret)
    )


def _traveller(name: str = "Q1 traveller") -> dict:
    answer = client.post(
        CREATE_PATH,
        json={"display_name": name, "locale": "zh-CN", "timezone": "Asia/Shanghai"},
    )
    assert answer.status_code == 201, answer.text
    return answer.json()


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _claims(token: str) -> dict:
    """Read the window out of a credential -- the payload is a plain sorted-key JSON body."""

    import base64
    import json

    body = token.split(".")[0]
    raw = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
    return json.loads(raw)


def test_a_live_session_can_be_slid_forward_and_the_new_token_works(monkeypatch):
    _use_secret(monkeypatch)
    person = _traveller()
    # Present a credential already half-way through its window: that is the state a real tab
    # reaches when it comes back to this door.  A signature is deterministic per second, so a
    # token minted and refreshed inside one tick would be byte-identical and prove nothing.
    stale_for = 300
    clock = int(time.time())
    headers = _bearer(
        traveler_principal.issue_traveler_token(
            person["id"], ttl_seconds=settings.traveler_auth_ttl_seconds, now=clock - stale_for
        )
    )

    answer = client.post(REFRESH_PATH, headers=headers)
    assert answer.status_code == 200, answer.text
    body = answer.json()

    assert body["traveler_id"] == person["id"]
    assert body["session_state"] == "SIGNED"
    assert isinstance(body["access_token"], str) and body["access_token"].count(".") == 1
    assert body["access_token"] != headers["Authorization"][7:], "续期没给出新凭据"
    # What a renewal actually buys: a later expiry, not a different person.
    old_exp = _claims(headers["Authorization"][7:])["exp"]
    new_exp = _claims(body["access_token"])["exp"]
    assert new_exp > old_exp, (old_exp, new_exp)
    assert _claims(body["access_token"])["sub"] == person["id"]
    # The number the answer gives must be the number the credential carries -- otherwise a
    # countdown on the screen is decoration and the token dies under it.
    assert body["expires_at"] == new_exp, (body["expires_at"], new_exp)
    assert body["renewed_from_expires_at"] == old_exp

    assert answer.headers["Cache-Control"] == "private, no-store"
    assert "Authorization" in answer.headers["Vary"]

    # The point of the exercise: the fresh credential is accepted where the old one was.
    who = client.get(SESSION_PATH, headers=_bearer(body["access_token"]))
    assert who.status_code == 200, who.text
    assert who.json()["traveler_id"] == person["id"]


def test_no_credential_is_a_named_refusal_not_an_anonymous_pass(monkeypatch):
    _use_secret(monkeypatch)
    answer = client.post(REFRESH_PATH)
    assert answer.status_code == 401, answer.text
    assert answer.json()["error"]["reason_code"] == traveler_principal.REASON_CREDENTIALS_MISSING


def test_an_expired_credential_is_told_apart_from_a_forged_one(monkeypatch):
    _use_secret(monkeypatch)
    person = _traveller()
    clock = int(time.time())

    expired = traveler_principal.issue_traveler_token(person["id"], ttl_seconds=60, now=clock - 600)
    stale = client.post(REFRESH_PATH, headers=_bearer(expired))
    assert stale.status_code == 401, stale.text
    assert stale.json()["error"]["reason_code"] == traveler_principal.REASON_CREDENTIALS_EXPIRED

    # Same shape, wrong signature: a well-formed token is not a credential.
    parts = person["access_token"].split(".")
    forged = f"{parts[0]}.{uuid4().hex[:43]}"
    refused = client.post(REFRESH_PATH, headers=_bearer(forged))
    assert refused.status_code == 401, refused.text
    assert refused.json()["error"]["reason_code"] == traveler_principal.REASON_CREDENTIALS_INVALID


def test_a_body_naming_a_traveller_is_refused_before_anything_is_signed(monkeypatch):
    """The night order's condition, asserted rather than promised.

    A valid credential plus a body that names somebody else must not produce a token for either
    of them -- the door has no parameter to put that claim in, and says so.
    """

    _use_secret(monkeypatch)
    mine = _traveller("mine")
    theirs = _traveller("theirs")

    answer = client.post(
        REFRESH_PATH, headers=_bearer(mine["access_token"]), json={"traveler_id": theirs["id"]}
    )
    assert answer.status_code == 400, answer.text
    body = answer.json()
    assert body["error"]["reason_code"] == traveler_principal.REASON_TRAVELER_NOT_PRINCIPAL
    # Nothing was signed on this request -- neither for the stranger named in the body, nor as a
    # side effect for the person who held the credential.
    assert "access_token" not in body, "被拒的续期还是发出了一枚凭据"
    still_mine = client.get(SESSION_PATH, headers=_bearer(mine["access_token"]))
    assert still_mine.status_code == 200, still_mine.text
    assert still_mine.json()["traveler_id"] == mine["id"]


def test_a_wellformed_token_for_a_traveller_who_does_not_exist_refreshes_nothing(monkeypatch):
    """`sub` is checked against the table, so the id inside a signature is not taken on faith."""

    _use_secret(monkeypatch)
    ghost = traveler_principal.issue_traveler_token(str(uuid4()))
    answer = client.post(REFRESH_PATH, headers=_bearer(ghost))
    assert answer.status_code == 401, answer.text
    assert answer.json()["error"]["reason_code"] == traveler_principal.REASON_PRINCIPAL_UNKNOWN


def test_there_is_no_door_that_takes_an_id_from_the_path(monkeypatch):
    """`POST /travelers/{id}/session/refresh` must not exist -- that is the bare-id exchange.

    Read as a set: the only renewal door is the one that speaks for whoever already holds a
    credential, so an attacker with a uuid and nothing else has no route to try.
    """

    _use_secret(monkeypatch)
    person = _traveller()

    by_path = client.post(f"/api/v1/travelers/{person['id']}/session/refresh")
    assert by_path.status_code in {404, 405}, by_path.text
    # And the renewal door is write-only on purpose: it cannot be read with a GET.
    wrong_method = client.get(REFRESH_PATH, headers=_bearer(person["access_token"]))
    assert wrong_method.status_code == 405, wrong_method.text


def test_without_a_configured_verifier_nothing_is_issued(monkeypatch):
    _use_secret(monkeypatch, secret=None)
    answer = client.post(REFRESH_PATH)
    assert answer.status_code in {401, 503}, answer.text
    assert answer.json()["error"]["reason_code"] in {
        traveler_principal.REASON_NOT_CONFIGURED,
        traveler_principal.REASON_CREDENTIALS_MISSING,
    }
