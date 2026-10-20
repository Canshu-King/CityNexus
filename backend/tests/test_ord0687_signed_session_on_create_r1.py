"""ORD-0687 -- creating a traveller also hands back a session that can be recognised.

Issue #27 could only say "never store anything" because nothing on this line could answer
"which traveller is this".  ORD-0685 built the verifier; this is the half that lets an ordinary
person *get* a credential: the create door signs one for the traveller it just made, and the
client can then be recognised by the server instead of by its own claim.

The rules these tests hold:

* a configured verifier signs a token for the newly created traveller, and the session door
  answers that same traveller -- nothing else;
* the same signed traveller can open more than one journey (identity is not per-trip);
* no verifier configured, or a configured-but-unusable one, is named in the answer instead of
  quietly sending no token;
* there is no way to obtain a token for a traveller you did not just create -- the payload's
  shape and the door's behaviour are both checked for that;
* the running OpenAPI contract carries the new fields, so a client can read them from the
  contract rather than from a changelog.

Secrets are generated per run and never written into the tree.
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
LONG_SECRET = uuid4().hex + uuid4().hex


def _use_secret(monkeypatch, secret: str | None) -> None:
    monkeypatch.setattr(traveler_principal, "settings", replace(settings, traveler_auth_secret=secret))


def _create(display_name: str = "Issue 31 traveller", **extra) -> dict:
    body = {"display_name": display_name, "locale": "zh-CN", "timezone": "Asia/Shanghai", **extra}
    answer = client.post(CREATE_PATH, json=body)
    assert answer.status_code == 201, answer.text
    return answer


def _bearer(traveler: dict) -> dict:
    """The credential this server handed this very person, in the shape the doors read."""

    return {"Authorization": "Bearer " + traveler["access_token"]}


def _journey(traveler_id: str, city: str, headers: dict | None = None) -> tuple[int, dict]:
    """The same payload the V8 creation wizard sends, so this proves the real user path."""
    start_at = "2026-11-01T09:00:00+08:00"
    end_at = "2026-11-02T18:00:00+08:00"
    answer = client.post("/api/v1/journeys", json={
        "traveler_id": traveler_id,
        "title": f"{city} · journey",
        "city_code": f"CN-{city}",
        "timezone": "Asia/Shanghai",
        "start_at": start_at,
        "end_at": end_at,
        "budget": {"amount_minor": 120000, "currency": "CNY"},
        "stay_budget": {"amount_minor": 60000, "currency": "CNY"},
        "party_size": 2,
        "occupancy": {"adults": 2, "rooms": 1},
        "arrival_anchor": {"at": start_at, "location": f"{city} station"},
        "departure_anchor": {"at": end_at, "location": f"{city} airport"},
    }, headers=headers)
    if answer.status_code < 300:
        return answer.status_code, answer.json()
    # A refusal keeps its own envelope, so a test can assert on `error.reason_code` instead of
    # on a truncated sentence -- the reason is the part the screen branches on.
    try:
        return answer.status_code, answer.json()
    except ValueError:
        return answer.status_code, {"raw": answer.text[:200]}


def test_create_hands_back_a_token_the_session_door_recognises(monkeypatch):
    _use_secret(monkeypatch, LONG_SECRET)
    answer = _create()
    body = answer.json()

    assert body["session_state"] == "SIGNED"
    assert isinstance(body.get("access_token"), str) and body["access_token"].count(".") == 1
    assert answer.headers["Cache-Control"] == "private, no-store"
    assert "Authorization" in answer.headers["Vary"]

    who = client.get(SESSION_PATH, headers={"Authorization": f"Bearer {body['access_token']}"})
    assert who.status_code == 200, who.text
    assert who.json()["traveler_id"] == body["id"]


def test_one_signed_traveller_can_open_two_journeys(monkeypatch):
    _use_secret(monkeypatch, LONG_SECRET)
    body = _create().json()
    token = body["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    first_status, first = _journey(body["id"], "Ningbo", headers=headers)
    second_status, second = _journey(body["id"], "Xiamen", headers=headers)

    assert first_status == 201 and second_status == 201, (first, second)
    assert first["id"] != second["id"]
    # Re-reading who we are must not have drifted to a second identity along the way.
    who = client.get(SESSION_PATH, headers=headers)
    assert who.json()["traveler_id"] == body["id"]


def test_without_a_configured_verifier_the_answer_says_so(monkeypatch):
    _use_secret(monkeypatch, None)
    answer = _create()
    body = answer.json()

    assert body["session_state"] == "NOT_CONFIGURED"
    assert body.get("access_token") is None
    # And the door is still a named refusal, not an anonymous pass.
    who = client.get(SESSION_PATH)
    assert who.status_code == 401
    assert who.json()["error"]["reason_code"] == traveler_principal.REASON_CREDENTIALS_MISSING


def test_a_too_short_secret_is_reported_as_misconfigured_not_forged(monkeypatch):
    _use_secret(monkeypatch, "abc123")
    body = _create().json()

    assert body["session_state"] == "MISCONFIGURED"
    assert body.get("access_token") is None


def test_a_supplied_id_does_not_become_the_traveller_you_are_signed_for(monkeypatch):
    """No back door: the token always names the traveller this call created."""
    _use_secret(monkeypatch, LONG_SECRET)
    someone_else = _create("someone else").json()["id"]

    body = _create("attacker", id=someone_else, traveler_id=someone_else).json()

    assert body["id"] != someone_else
    who = client.get(SESSION_PATH, headers={"Authorization": f"Bearer {body['access_token']}"})
    assert who.json()["traveler_id"] == body["id"]


def test_forged_and_expired_tokens_keep_their_own_names(monkeypatch):
    _use_secret(monkeypatch, LONG_SECRET)
    body = _create().json()
    token = body["access_token"]

    forged = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
    answer = client.get(SESSION_PATH, headers={"Authorization": f"Bearer {forged}"})
    assert answer.json()["error"]["reason_code"] == traveler_principal.REASON_CREDENTIALS_INVALID

    expired = traveler_principal.issue_traveler_token(body["id"], ttl_seconds=60, now=int(time.time()) - 600)
    stale = client.get(SESSION_PATH, headers={"Authorization": f"Bearer {expired}"})
    assert stale.json()["error"]["reason_code"] == traveler_principal.REASON_CREDENTIALS_EXPIRED


def test_an_old_journey_pointer_does_not_authorise_the_next_traveller(monkeypatch):
    """Issue #31 A(5): a uuid on the device is not an authorisation.

    This is the exact situation Issue #27 could only half-fix: one phone, two people, and the
    second one's screen still opening the first one's trip because `localStorage` remembered the
    id.  With a signed session the server -- not the pointer -- decides, and it refuses by name.
    """

    _use_secret(monkeypatch, LONG_SECRET)
    owner = _create("First traveller").json()
    status, journey = _journey(owner["id"], "Xiamen", headers=_bearer(owner))
    assert status == 201, journey
    guest = _create("The next person holding the phone").json()

    mine = client.get(f"/api/v1/journeys/{journey['id']}",
                      headers={"Authorization": f"Bearer {owner['access_token']}"})
    assert mine.status_code == 200, mine.text

    for path in (f"/api/v1/journeys/{journey['id']}", f"/api/v1/journeys/{journey['id']}/experience"):
        refused = client.get(path, headers={"Authorization": f"Bearer {guest['access_token']}"})
        assert refused.status_code == 403, f"{path} answered {refused.status_code}: {refused.text[:200]}"
        assert refused.json()["error"]["reason_code"] == traveler_principal.REASON_JOURNEY_NOT_SCOPED


def test_a_member_seat_opens_the_trip_it_was_given(monkeypatch):
    """The refusal is about *who is asking*, not about the trip being private to its owner.

    A fellow traveller with a seat on this journey reads it with their own credential; the same
    credential still cannot read the trip it was never added to, which is why the test above and
    this one have to exist together.
    """

    _use_secret(monkeypatch, LONG_SECRET)
    owner = _create("Trip owner").json()
    status, journey = _journey(owner["id"], "Fuzhou", headers=_bearer(owner))
    assert status == 201, journey
    seatmate = _create("Seated fellow traveller").json()

    invited = client.post(f"/api/v1/journeys/{journey['id']}/members", json={
        "traveler_id": seatmate["id"],
        "role": "COLLABORATOR",
        "invited_by": "Trip owner",
    })
    assert invited.status_code == 201, invited.text

    read = client.get(f"/api/v1/journeys/{journey['id']}/experience",
                      headers={"Authorization": f"Bearer {seatmate['access_token']}"})
    assert read.status_code == 200, read.text[:300]

    outsider = _create("Nobody on this trip").json()
    denied = client.get(f"/api/v1/journeys/{journey['id']}",
                        headers={"Authorization": f"Bearer {outsider['access_token']}"})
    assert denied.status_code == 403, denied.text[:200]


def test_a_signed_traveller_cannot_open_a_journey_in_somebody_elses_name(monkeypatch):
    """Issue #31 A(6): no path turns a claim about an id into a trip for that id.

    Both branches, after GPT's P0-SEC review: somebody else's credential naming this id is 403,
    and *no* credential naming it is 401 -- dropping the header used to be the way around the
    first rule, and the body's `traveler_id` is not an identity.
    """

    _use_secret(monkeypatch, LONG_SECRET)
    caller = _create("Signed in").json()
    stranger = _create("Someone else entirely").json()

    status, body = _journey(stranger["id"], "Guangzhou",
                            headers={"Authorization": f"Bearer {caller['access_token']}"})
    assert status == 403, body
    assert body["error"]["reason_code"] == traveler_principal.REASON_TRAVELER_NOT_PRINCIPAL

    anonymous_status, anonymous_body = _journey(stranger["id"], "Guangzhou")
    assert anonymous_status == 401, anonymous_body
    assert anonymous_body["error"]["reason_code"] == traveler_principal.REASON_CREDENTIALS_MISSING


def test_a_private_trip_needs_the_server_to_know_who_is_asking(monkeypatch):
    """GPT P0-SEC, the named regression: same trip, three callers, three different answers.

    The owner reads it; a second traveller's genuine credential is refused because it is not
    theirs; and no credential at all is refused before the trip's existence is confirmed.  The
    middle and last cases used to be 403 and 200 -- the second was right, the first was a hole:
    a private uuid was readable by anybody who simply stopped sending a header.
    """

    _use_secret(monkeypatch, LONG_SECRET)
    owner = _create("Owner of the private trip").json()
    status, journey = _journey(owner["id"], "Quanzhou",
                              headers={"Authorization": f"Bearer {owner['access_token']}"})
    assert status == 201, journey
    outsider = _create("A different person").json()
    path = f"/api/v1/journeys/{journey['id']}"

    mine = client.get(path, headers={"Authorization": f"Bearer {owner['access_token']}"})
    assert mine.status_code == 200, mine.text

    foreign = client.get(path, headers={"Authorization": f"Bearer {outsider['access_token']}"})
    assert foreign.status_code == 403, foreign.text
    assert foreign.json()["error"]["reason_code"] == traveler_principal.REASON_JOURNEY_NOT_SCOPED

    anonymous = client.get(path)
    assert anonymous.status_code == 401, anonymous.text
    assert anonymous.json()["error"]["reason_code"] == traveler_principal.REASON_CREDENTIALS_MISSING

    listing = client.get("/api/v1/journeys")
    assert listing.status_code == 401, listing.text


def test_anonymous_reads_stay_available_only_where_signing_is_off(monkeypatch):
    """The other half of the same rule, so the strict branch cannot be a blanket wall.

    With no secret configured there is no identity this server could require, so the doors answer
    as they always have.  That is the shared-preview and local-development shape, and it is now a
    stated configuration rather than an accident of nobody carrying a token.
    """

    _use_secret(monkeypatch, None)
    owner = _create("Owner on an unsigned build").json()
    status, journey = _journey(owner["id"], "Dali")
    assert status == 201, journey
    assert client.get(f"/api/v1/journeys/{journey['id']}").status_code == 200
    assert client.get("/api/v1/journeys").status_code == 200


def test_the_running_contract_carries_the_new_fields():
    schema = app.openapi()["paths"][CREATE_PATH]["post"]["responses"]["201"]["content"]["application/json"]["schema"]
    ref = schema.get("$ref", schema.get("anyOf", [{}])[0].get("$ref", ""))
    name = ref.split("/")[-1]
    definition = app.openapi()["components"]["schemas"][name]
    assert {"access_token", "session_state"} <= set(definition["properties"]), sorted(definition["properties"])
