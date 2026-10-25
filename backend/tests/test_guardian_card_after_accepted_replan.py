"""Issue #51 — the Guardian card must be able to say the issue was handled.

The existing Guardian card displays projected impact/action as current work.
An accepted replan must move those old records to history and project the
server's resolution, instead of showing an UNRESOLVED action beside RESOLVED.

The authority is server-persisted state, not text: acceptance writes
`Event.status = "RESOLVED"`, `Event.resolved_at = decided_at` and
`payload.resolution_reason`.  A public `POST /events` body can carry arbitrary
payload keys on a DETECTED event, so `resolution` must appear only when the Event
row itself says RESOLVED *and* carries the timestamp this server wrote.

Every record below is a deterministic offline fixture (TEST_FIXTURE); the
mobility legs are the module's declared scenario facts, not live measurements.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.core.config import settings
from app.db.models import Event as EventModel
from app.db.models import Journey
from app.db.session import SessionLocal
from app.traveler_principal import issue_traveler_token
from _qoder_explicit_demo_mobility import (
    GUARDIAN_MODEL_MOBILITY,
    seed_explicit_mobility,
)
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(main_module.app)

TEST_SECRET = "guardian-card-after-replan-secret-0123456789"


@pytest.fixture(autouse=True)
def _signed_fixture(monkeypatch):
    """Signed reads on, and only this module's declared mobility legs seeded."""

    previous = settings.traveler_auth_secret
    object.__setattr__(settings, "traveler_auth_secret", TEST_SECRET)
    seed_explicit_mobility(monkeypatch, GUARDIAN_MODEL_MOBILITY)
    try:
        yield
    finally:
        object.__setattr__(settings, "traveler_auth_secret", previous)


def _owner_headers(journey_id: str) -> dict[str, str]:
    with SessionLocal() as session:
        owner_id = session.get(Journey, journey_id).traveler_id
    return {"Authorization": f"Bearer {issue_traveler_token(owner_id)}"}


def _accepted_replan_journey() -> tuple[str, str]:
    """Drive the real Journey API to an accepted replan; return (journey, event)."""

    reset = client.post("/api/v1/demo/reset", headers=demo_reset_headers())
    assert reset.status_code == 200, reset.text
    journey_id = reset.json()["journey_id"]
    headers = _owner_headers(journey_id)

    generated = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate",
        json={"candidate_count": 1},
        headers=headers,
    )
    assert generated.status_code == 201, generated.text
    plan = generated.json()[0]
    assert (
        client.post(
            f"/api/v1/journeys/{journey_id}/plans/{plan['id']}/select", headers=headers
        ).status_code
        == 200
    )
    tech = next(item for item in plan["activities"] if item["place_id"] == "place-tech-art")
    started = client.post(f"/api/v1/journeys/{journey_id}/start", headers=headers)
    assert started.status_code == 200, started.text
    for activity in plan["activities"]:
        if activity["id"] == tech["id"]:
            break
        completed = client.post(
            f"/api/v1/journeys/{journey_id}/activities/{activity['id']}/complete",
            headers=headers,
        )
        assert completed.status_code == 200, completed.text

    event = client.post(
        f"/api/v1/journeys/{journey_id}/events",
        json={
            "event_type": "CLOSURE",
            "severity": "MAJOR",
            "affected_activity_id": tech["id"],
            "occurred_at": "2026-10-10T13:25:00+08:00",
            "payload": {"reason": "issue-51 accepted replan fixture"},
        },
    )
    assert event.status_code == 201, event.text
    event_id = event.json()["id"]

    proposal = client.post(
        f"/api/v1/journeys/{journey_id}/replans",
        json={"trigger_event_id": event_id, "candidate_count": 3},
        headers={"Idempotency-Key": f"issue-51-replan-{journey_id}"},
    )
    assert proposal.status_code == 201, proposal.text
    accepted = client.post(
        f"/api/v1/replans/{proposal.json()['id']}/accept",
        headers={
            **headers,
            "Idempotency-Key": f"issue-51-accept-{proposal.json()['id']}",
        },
    )
    assert accepted.status_code == 200, accepted.text
    return journey_id, event_id


def _observation(journey_id: str, event_id: str) -> dict:
    response = client.get(
        f"/api/v1/journeys/{journey_id}/guardian/stream", headers=_owner_headers(journey_id)
    )
    assert response.status_code == 200, response.text
    entries = [item for item in response.json()["stream"] if item["observation"]["id"] == event_id]
    assert len(entries) == 1, [item["observation"]["id"] for item in response.json()["stream"]]
    return entries[0]["observation"]


def test_accepted_replan_exposes_the_persisted_resolution():
    """The trigger Event the accept path closed carries its resolution through."""

    journey_id, event_id = _accepted_replan_journey()

    with SessionLocal() as session:
        row = session.get(EventModel, event_id)
        stored = {
            "status": row.status,
            "resolved_at": row.resolved_at,
            "reason": json.loads(row.payload_json).get("resolution_reason"),
        }
    # The accept path really did close the trigger (not merely in this test's head).
    assert stored["status"] == "RESOLVED"
    assert stored["resolved_at"], "accept must persist a server timestamp"
    assert stored["reason"] == "JOURNEY_ADAPTED"

    observation = _observation(journey_id, event_id)
    assert observation["status"] == "RESOLVED"
    resolution = observation["resolution"]
    assert resolution is not None, "an accepted replan must not read as still unresolved"
    # The column is the authority: the projection echoes exactly what the server wrote.
    assert resolution["decided_at"] == stored["resolved_at"]
    assert resolution["reason"] == "JOURNEY_ADAPTED"
    stream = client.get(f"/api/v1/journeys/{journey_id}/guardian/stream", headers=_owner_headers(journey_id)).json()
    entry = next(item for item in stream["stream"] if item["observation"]["id"] == event_id)
    assert entry["impact"] is None
    assert entry["proposed_action"] is None
    assert entry["history"]["impact"] is not None
    assert entry["history"]["impact"]["status"] == "VALIDATED"
    assert stream["counts"]["open_events"] == 0


@pytest.mark.parametrize("payload", ["[]", "null", "1", "broken-json"])
def test_closed_event_with_non_object_payload_keeps_its_server_resolution(payload):
    from types import SimpleNamespace
    from app.agent.guardian_stream import _resolution

    timestamp = "2026-10-25T12:00:00+00:00"
    event = SimpleNamespace(status="RESOLVED", resolved_at=timestamp, payload_json=payload)
    assert _resolution(event) == {"reason": "UNKNOWN", "decided_at": timestamp}


def test_user_supplied_resolution_text_cannot_hide_an_open_issue():
    """A DETECTED event with spoofed payload closure text must stay unresolved."""

    reset = client.post("/api/v1/demo/reset", headers=demo_reset_headers())
    assert reset.status_code == 200, reset.text
    journey_id = reset.json()["journey_id"]
    headers = _owner_headers(journey_id)

    created = client.post(
        f"/api/v1/journeys/{journey_id}/events",
        json={
            "event_type": "WEATHER",
            "severity": "MINOR",
            "occurred_at": "2026-10-10T14:00:00+08:00",
            "payload": {
                "reason": "issue-51 spoof fixture",
                "resolution_reason": "JOURNEY_ADAPTED",
                "resolved_at": "2026-10-10T14:05:00+08:00",
                "resolution": "RESOLVED",
            },
        },
    )
    assert created.status_code == 201, created.text
    event_id = created.json()["id"]
    # The public door stored the client's payload but not a server resolution.
    assert created.json()["status"] == "DETECTED"
    assert created.json()["resolved_at"] is None

    observation = _observation(journey_id, event_id)
    assert observation["status"] == "DETECTED"
    assert observation["resolution"] is None, (
        "user-supplied payload text was promoted to a resolved card"
    )


def test_resolved_status_without_a_server_timestamp_is_not_a_resolution():
    """The timestamp column, not the status string or payload, is the authority."""

    reset = client.post("/api/v1/demo/reset", headers=demo_reset_headers())
    assert reset.status_code == 200, reset.text
    journey_id = reset.json()["journey_id"]
    headers = _owner_headers(journey_id)

    created = client.post(
        f"/api/v1/journeys/{journey_id}/events",
        json={
            "event_type": "WEATHER",
            "severity": "MINOR",
            "occurred_at": "2026-10-10T14:00:00+08:00",
            "payload": {"resolution_reason": "JOURNEY_ADAPTED"},
        },
    )
    assert created.status_code == 201, created.text
    event_id = created.json()["id"]
    with SessionLocal() as session:
        row = session.get(EventModel, event_id)
        row.status = "RESOLVED"
        row.resolved_at = None
        session.commit()

    observation = _observation(journey_id, event_id)
    assert observation["status"] == "RESOLVED"
    assert observation["resolution"] is None
