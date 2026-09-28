"""ORD-0434 step 1 - a share grant becomes a server fact, and it ends on schedule.

Measured at the authoritative tip `3543928ea1b7a0466871b6fbc3c3d24f64b14044`: the share exit was a
client-side string concat (`frontend/src/lib/journeyLink.ts:34`), the journey read
(`backend/app/main.py:3099`) accepted no caller identity at all, and nothing in the store could hold
a visibility, a deadline or a withdrawal. So "who can see this trip" existed only in a URL.

What the constraints became in code, and which arm proves each:

* the anonymous read is untouched - one arm compares that function's bytes against the same function
  recorded at the base tip in `review/ord0434/ANON_READ_BASELINE_r1.json`, and another arm shows the
  behaviour: a journey whose grant has been revoked is still readable anonymously, because tightening
  that door is step 2 and is decided with the user, not shipped under it;
* expiry and withdrawal are two different named codes, and "never existed" is a third - the arms read
  all three off the same request shape, so a client cannot collapse them into one message;
* revocation is immediate and not repeatable: the same POST gives a different answer the second time;
* `PRIVATE` and `INVITEES_ONLY` are stored but fail closed on the token read, because there is no
  member data yet to check a holder against;
* no deadline is stored as a date: a grant without `expires_at` answers `null`, and an expiry sent
  without an offset is refused rather than silently read in the server's own zone.

The vocabulary was checked before naming anything: `PRIVATE`/`LINK_READ`/`INVITEES_ONLY`/`PUBLIC`
have no other meaning in this tree, while `EXPIRED`/`REVOKED` already belong to the agent-approval
status enum (`contracts/openapi.yaml:2220`), so this slice never emits those bare words - every code
it adds is prefixed `SHARE_GRANT_`.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import yaml
from fastapi.testclient import TestClient

from app.db.models import Traveler
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "openapi.yaml"
GENERATED = ROOT / "frontend/src/generated/api.ts"
BASELINE_ARTIFACT = ROOT / "review/ord0434/ANON_READ_BASELINE_r1.json"
TZ = timezone(timedelta(hours=8))
START = datetime(2026, 11, 3, 9, 0, tzinfo=TZ)

GRANT_PATH = "/api/v1/journeys/{journey_id}/share-grants"
REVOKE_PATH = "/api/v1/journeys/{journey_id}/share-grants/{grant_id}/revoke"
TOKEN_PATH = "/api/v1/shared/journeys/{token}"


def _traveler() -> str:
    traveler_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        session.add(
            Traveler(
                id=traveler_id,
                display_name="ORD-0434 probe",
                email=None,
                locale="zh-CN",
                timezone="Asia/Shanghai",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    return traveler_id


def _journey() -> str:
    created = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": _traveler(),
            "title": "ORD-0434",
            "city_code": "CN-XIAMEN",
            "timezone": "Asia/Shanghai",
            "start_at": START.isoformat(),
            "end_at": (START + timedelta(days=2, hours=8)).isoformat(),
            "budget": {"amount_minor": 90000, "currency": "CNY"},
            "planning_mode": "balanced",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _create(journey_id: str, visibility: str = "LINK_READ", expires_at: str | None = None) -> dict:
    response = client.post(
        GRANT_PATH.format(journey_id=journey_id),
        json={"visibility": visibility, "created_by": "lane-rel", "expires_at": expires_at},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _reason(payload: dict) -> str:
    """The named fact rides in `error.reason_code`; `error.code` stays the one existing family."""
    return str((payload.get("error") or {}).get("reason_code"))


# ---------------------------------------------------------------- grant as a server fact


def test_grant_creation_answers_a_token_and_stores_no_invented_deadline() -> None:
    journey_id = _journey()
    grant = _create(journey_id)
    assert grant["visibility"] == "LINK_READ"
    assert len(grant["token"]) >= 20, "the token is the only capability the holder gets"
    # "no deadline" is NULL, not a far-future date and not the server's clock.
    assert grant["expires_at"] is None
    assert grant["revoked_at"] is None
    assert grant["created_by"] == "lane-rel"
    assert grant["journey_id"] == journey_id


def test_one_journey_holds_many_grants_and_the_list_keeps_withdrawn_rows() -> None:
    journey_id = _journey()
    first = _create(journey_id, "LINK_READ")
    second = _create(journey_id, "PUBLIC")
    listed = client.get(GRANT_PATH.format(journey_id=journey_id))
    assert listed.status_code == 200
    ids = [row["id"] for row in listed.json()]
    assert sorted(ids) == sorted([first["id"], second["id"]])

    revoked = client.post(REVOKE_PATH.format(journey_id=journey_id, grant_id=first["id"]))
    assert revoked.status_code == 200, revoked.text
    after = client.get(GRANT_PATH.format(journey_id=journey_id))
    rows = {row["id"]: row for row in after.json()}
    # A row that vanished would look identical to one that never existed; the bin stays visible.
    assert first["id"] in rows, "a withdrawn grant must still be listed, marked as withdrawn"
    assert rows[first["id"]]["revoked_at"], rows[first["id"]]
    assert rows[second["id"]]["revoked_at"] is None


def test_an_expiry_without_an_offset_is_refused_rather_than_guessed() -> None:
    journey_id = _journey()
    naive = (datetime.now(timezone.utc) + timedelta(days=1)).replace(tzinfo=None).isoformat()
    response = client.post(
        GRANT_PATH.format(journey_id=journey_id),
        json={"visibility": "LINK_READ", "created_by": "lane-rel", "expires_at": naive},
    )
    assert response.status_code == 422, response.text
    assert _reason(response.json()) == "SHARE_GRANT_EXPIRY_NO_OFFSET"


# ---------------------------------------------------------------- the two-way readings


def test_revoke_then_the_same_request_gives_a_different_answer() -> None:
    journey_id = _journey()
    grant = _create(journey_id)
    same_request = REVOKE_PATH.format(journey_id=journey_id, grant_id=grant["id"])
    first = client.post(same_request)
    assert first.status_code == 200, first.text
    assert first.json()["already_revoked"] is False
    second = client.post(same_request)
    assert second.status_code != first.status_code, "the same request must not answer the same twice"
    assert _reason(second.json()) == "SHARE_GRANT_ALREADY_REVOKED"


def test_a_revoked_token_stops_working_on_the_next_read() -> None:
    journey_id = _journey()
    grant = _create(journey_id)
    before = client.get(TOKEN_PATH.format(token=grant["token"]))
    assert before.status_code == 200, before.text
    assert before.json()["id"] == journey_id

    assert client.post(REVOKE_PATH.format(journey_id=journey_id, grant_id=grant["id"])).status_code == 200
    after = client.get(TOKEN_PATH.format(token=grant["token"]))
    assert after.status_code == 409, after.text
    assert _reason(after.json()) == "SHARE_GRANT_REVOKED"
    assert after.json()["error"]["details"]["grant_id"] == grant["id"]


def test_expired_and_never_existed_are_different_named_codes() -> None:
    journey_id = _journey()
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    grant = _create(journey_id, "LINK_READ", past)
    expired = client.get(TOKEN_PATH.format(token=grant["token"]))
    assert expired.status_code == 409, expired.text
    assert _reason(expired.json()) == "SHARE_GRANT_EXPIRED"
    assert expired.json()["error"]["details"]["expires_at"] == grant["expires_at"]

    absent = client.get(TOKEN_PATH.format(token="not-a-grant-" + uuid4().hex))
    assert _reason(absent.json()) == "SHARE_GRANT_UNKNOWN"
    assert absent.status_code == 404, "an unknown token is not the same fact as an expired one"
    assert _reason(absent.json()) != _reason(expired.json())


def test_visibility_without_a_member_store_fails_closed() -> None:
    journey_id = _journey()
    for visibility in ("PRIVATE", "INVITEES_ONLY"):
        grant = _create(journey_id, visibility)
        response = client.get(TOKEN_PATH.format(token=grant["token"]))
        assert response.status_code == 409, f"{visibility} must not read as open: {response.text}"
        assert _reason(response.json()) == "SHARE_GRANT_NOT_LINK_READABLE"
        assert response.json()["error"]["details"]["visibility"] == visibility


def test_a_public_grant_reads_the_journey() -> None:
    journey_id = _journey()
    grant = _create(journey_id, "PUBLIC")
    response = client.get(TOKEN_PATH.format(token=grant["token"]))
    assert response.status_code == 200, response.text
    assert response.json()["id"] == journey_id


# ---------------------------------------------------------------- the untouched door


def _function_slice(text: str) -> str:
    start = text.index('@app.get("/api/v1/journeys/{journey_id}")')
    end = text.index('@app.get("/api/v1/journeys/{journey_id}/experience")')
    return text[start:end]


def test_the_anonymous_read_bytes_are_unchanged_from_the_base_tip() -> None:
    baseline = json.loads(BASELINE_ARTIFACT.read_text(encoding="utf-8"))
    live = _function_slice((ROOT / "backend/app/main.py").read_text(encoding="utf-8"))
    # The region now also holds the new grant doors, so the claim is about the function's own bytes:
    # the base tip's text must still appear verbatim inside it.
    assert baseline["get_journey_text"] in live, (
        "ORD-0434 promised the anonymous read would not move one word; it moved"
    )


def test_a_revoked_grant_does_not_change_what_the_anonymous_read_answers() -> None:
    journey_id = _journey()
    grant = _create(journey_id)
    before = client.get(f"/api/v1/journeys/{journey_id}")
    assert client.post(REVOKE_PATH.format(journey_id=journey_id, grant_id=grant["id"])).status_code == 200
    after = client.get(f"/api/v1/journeys/{journey_id}")
    assert before.status_code == after.status_code == 200
    assert before.json() == after.json(), (
        "the phone demo chain and every existing e2e walk this door; grants must not reach it"
    )


# ---------------------------------------------------------------- contract and client, one commit


def test_contract_and_generated_client_carry_the_same_four_doors() -> None:
    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    # The hand-written contract keys carry no `/api/v1` prefix; the servers block supplies it.
    declared = {
        "/journeys/{journey_id}/share-grants",
        "/journeys/{journey_id}/share-grants/{grant_id}/revoke",
        "/shared/journeys/{token}",
    }
    missing = sorted(path for path in declared if path not in spec["paths"])
    assert not missing, f"declared in code but absent from the contract: {missing}"

    operations = {
        operation["operationId"]
        for item in spec["paths"].values()
        for operation in item.values()
        if isinstance(operation, dict) and operation.get("operationId", "").startswith(("createShare", "listShare", "revokeShare", "readShared"))
    }
    assert operations == {
        "createShareGrant",
        "listShareGrants",
        "revokeShareGrant",
        "readSharedJourney",
    }, operations
    generated = GENERATED.read_text(encoding="utf-8")
    unported = sorted(op for op in operations if op not in generated)
    assert not unported, f"the checked-in client is behind the contract: {unported}"

    visibility = spec["components"]["schemas"]["ShareVisibility"]["enum"]
    assert visibility == ["PRIVATE", "LINK_READ", "INVITEES_ONLY", "PUBLIC"]
