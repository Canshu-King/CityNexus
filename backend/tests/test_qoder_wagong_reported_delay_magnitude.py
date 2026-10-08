"""A traveller saying "there is traffic" does not say how long.

`_capture_reported_disruption` stored `"extra_minutes": 15` into every TRAFFIC_DELAY event it
wrote, and wrote the key for *every* event type (None for the rest).  The recovery path then read
it back --

    payload.get("extra_minutes", payload.get("delay_minutes", 15))

-- and that 15 became the `delay_minutes` of an `F2_SUFFIX_DELAY` candidate, which shifts every
downstream activity of the plan by fifteen minutes and records `"delay_minutes": 15` in the new
plan's metadata.  A traveller reported a condition; this build chose a magnitude for them, and
the chosen number then appeared in the plan as if the provider had supplied it.

The same reader had a second failure behind the same line: `.get(key, fallback)` only falls back
when the key is *absent*, so the explicit `None` the capture wrote for every non-traffic event
reached `int(None)` and raised.  Folding absence and an explicit null into one state (`or None`)
is what makes "nobody stated a magnitude" readable as a single thing.

Measured on the offline demo journey: a TRAFFIC_DELAY report captured through the deterministic
copilot path wrote `payload["extra_minutes"] == 15` before this change, and the key is absent
after it.  An event whose caller really knows a magnitude still carries it, and the
`test_post_goal_five_defects` arm for the explicit 25-minute case still passes unchanged.

These arms are behavioural: they capture a real disruption and read the persisted Event, and they
run a real replan to read the number that reaches the plan.  None greps the source for a literal.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import app.main as main_module
from app.db.models import Activity, Event, Journey, PlanVersion, ReplanProposal, Traveler
from app.db.session import SessionLocal
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(main_module.app)


@pytest.fixture
def journey_row() -> str:
    """A journey with a plan selected and running, so a recovery has something to repair."""

    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    journey_id = ids["journey_id"]
    plan = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate", json={"candidate_count": 1}
    ).json()[0]
    assert client.post(
        f"/api/v1/journeys/{journey_id}/plans/{plan['id']}/select"
    ).status_code == 200
    assert client.post(f"/api/v1/journeys/{journey_id}/start").status_code == 200
    return journey_id


def _minimal_journey() -> str:
    """A journey row with no plan: enough to exercise the capture on its own."""

    client.post("/api/v1/demo/reset", headers=demo_reset_headers())
    with SessionLocal() as session:
        traveler = session.scalar(select(Traveler))
        journey_id = str(uuid4())
        session.add(
            Journey(
                id=journey_id,
                traveler_id=traveler.id,
                title="reported-disruption",
                city_code="CN-TIANJIN",
                timezone="Asia/Shanghai",
                start_at="2026-10-01T08:00:00+00:00",
                end_at="2026-10-02T22:00:00+00:00",
                budget_currency="CNY",
                budget_amount_minor=100000,
                planning_mode="balanced",
                status="PLANNED",
                created_at="2026-10-01T08:00:00+00:00",
                updated_at="2026-10-01T08:00:00+00:00",
            )
        )
        session.flush()
    return journey_id


def _capture(journey_id: str, *, commit: bool = False, **kwargs):
    with SessionLocal() as session:
        receipt = main_module._capture_reported_disruption(
            session,
            session.get(Journey, journey_id),
            event_type="TRAFFIC_DELAY",
            description="the road is congested right now",
            provider_key="user-copilot",
            source="copilot",
            semantic_payload={"assertion_status": "ASSERTED", "effective_time": "NOW"},
            semantic_envelope={"assertion_status": "ASSERTED", "effective_time": "NOW"},
            occurred_at_fallback=datetime.now(timezone.utc).isoformat(),
            audit_action=None,
            commit=commit,
            **kwargs,
        )
        payload = None
        row = session.get(Event, receipt["id"]) if receipt.get("id") else None
        if row is not None:
            payload = json.loads(row.payload_json or "{}")
        if not commit:
            session.rollback()
    return receipt, payload


def test_a_reported_delay_carries_no_magnitude_this_build_chose(
    journey_row: str,
) -> None:
    """The arm the defect is named by: on tip bytes this payload holds extra_minutes == 15."""

    _, payload = _capture(journey_row)
    assert payload is not None, "the capture must persist a real Event for this arm to read"
    assert "extra_minutes" not in payload, payload
    assert "delay_minutes" not in payload, payload
    # The report itself is still recorded in full -- what is withheld is only the number.
    assert payload["description"] == "the road is congested right now"
    assert payload["source"] == "copilot"


def test_the_magnitude_key_is_absent_for_every_event_type_not_just_traffic() -> None:
    """The key used to be written for all four types as an explicit None.

    That explicit null is the other half of the defect: `.get(key, 15)` cannot see an absent key,
    so a CLOSURE event's `extra_minutes: None` reached `int(None)`.  With the key gone, the reader
    has one state to interpret instead of two that mean the same thing.
    """

    for event_type in ("TRAFFIC_DELAY", "SCHEDULE_DELAY", "WEATHER", "CLOSURE"):
        with SessionLocal() as session:
            traveler = session.scalar(select(Traveler))
            journey_id = str(uuid4())
            session.add(
                Journey(
                    id=journey_id,
                    traveler_id=traveler.id,
                    title=f"probe-{event_type}",
                    city_code="CN-TIANJIN",
                    timezone="Asia/Shanghai",
                    start_at="2026-10-01T08:00:00+00:00",
                    end_at="2026-10-02T22:00:00+00:00",
                    budget_currency="CNY",
                    budget_amount_minor=100000,
                    planning_mode="balanced",
                    status="PLANNED",
                    created_at="2026-10-01T08:00:00+00:00",
                    updated_at="2026-10-01T08:00:00+00:00",
                )
            )
            session.flush()
            receipt = main_module._capture_reported_disruption(
                session,
                session.get(Journey, journey_id),
                event_type=event_type,
                description="a condition was reported",
                provider_key="user-copilot",
                source="copilot",
                semantic_payload={"assertion_status": "ASSERTED", "effective_time": "NOW"},
                semantic_envelope={"assertion_status": "ASSERTED", "effective_time": "NOW"},
                occurred_at_fallback=datetime.now(timezone.utc).isoformat(),
                audit_action=None,
                commit=False,
            )
            row = session.get(Event, receipt["id"]) if receipt.get("id") else None
            assert row is None or "extra_minutes" not in json.loads(row.payload_json or "{}"), event_type
            session.rollback()


def test_a_caller_that_states_a_magnitude_is_still_believed(journey_row: str) -> None:
    """Withholding a number is not refusing to record one.

    `payload_extra` is how a caller that really knows the delay says so, and that value must
    survive untouched -- otherwise this change would have thrown away a real measurement along
    with the invented one.
    """

    _, payload = _capture(journey_row, payload_extra={"extra_minutes": 40})
    assert payload is not None
    assert payload["extra_minutes"] == 40, payload


def test_a_report_with_no_magnitude_reaches_a_repair_instead_of_raising() -> None:
    """The half of this defect that is a crash rather than a fabrication.

    The capture wrote `"extra_minutes": 15 if event_type == "TRAFFIC_DELAY" else None` -- so every
    SCHEDULE_DELAY, WEATHER and CLOSURE report got an explicit `None` under that key.  The reader
    used `payload.get("extra_minutes", payload.get("delay_minutes", 15))`, and `.get` only falls
    back when a key is *absent*: the explicit null survived the default and reached `int(None)`.
    Measured on tip bytes, a SCHEDULE_DELAY report with no stated magnitude raises

        TypeError: int() argument must be a string, a bytes-like object or a real number, not 'NoneType'

    and the recovery answers with a 500 rather than a repair.  Folding absence and an explicit
    null into the one state they both mean is what makes "nobody stated a magnitude" readable.
    """

    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    journey_id = ids["journey_id"]
    plan = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate", json={"candidate_count": 1}
    ).json()[0]
    client.post(f"/api/v1/journeys/{journey_id}/plans/{plan['id']}/select")
    client.post(f"/api/v1/journeys/{journey_id}/start")

    with SessionLocal() as session:
        receipt = main_module._capture_reported_disruption(
            session,
            session.get(Journey, journey_id),
            event_type="SCHEDULE_DELAY",
            description="running late by an unstated amount",
            provider_key="user-copilot",
            source="copilot",
            semantic_payload={"assertion_status": "ASSERTED", "effective_time": "NOW"},
            semantic_envelope={"assertion_status": "ASSERTED", "effective_time": "NOW"},
            occurred_at_fallback=datetime.now(timezone.utc).isoformat(),
            audit_action=None,
            commit=True,
        )
    assert receipt.get("id"), receipt

    response = client.post(
        f"/api/v1/journeys/{journey_id}/replans",
        json={"trigger_event_id": receipt["id"], "candidate_count": 3},
    )
    # Tip bytes raise TypeError here, which the TestClient re-raises rather than turning into a 500.
    assert response.status_code == 201, response.status_code


def test_a_delay_stated_by_the_caller_still_reaches_the_plan(
    journey_row: str,
) -> None:
    """The positive path through the reader this change touches, so the arms above cannot be
    passed by refusing to repair anything at all.

    The magnitude is stated the way a caller states one -- on the event's own payload -- and the
    replan then has to move the itinerary by exactly that many minutes.  This is the invariant
    that must hold either way: it stays green when the product change is reverted, which is what
    tells the other arms apart from "the delay feature broke".
    """

    with SessionLocal() as session:
        journey = session.get(Journey, journey_row)
        assert journey is not None and journey.active_plan_version_id
        active = client.get(f"/api/v1/plans/{journey.active_plan_version_id}").json()
    activities = {item["place_id"]: item for item in active["activities"] if item.get("place_id")}
    target_place = next(
        place for place in activities if place in {"place-tech-art", "place-city-park"}
    )
    event = client.post(
        f"/api/v1/journeys/{journey_row}/events",
        json={
            "event_type": "TRAFFIC_DELAY",
            "affected_activity_id": activities[target_place]["id"],
            "occurred_at": "2026-10-10T12:50:00+08:00",
            "payload": {
                "from_place_id": "place-food-hall",
                "to_place_id": target_place,
                "extra_minutes": 25,
            },
        },
    )
    assert event.status_code == 201, event.text
    stored = client.get(f"/api/v1/journeys/{journey_row}/events").json()
    assert event.json()["id"] in {item["id"] for item in stored}
    response = client.post(
        f"/api/v1/journeys/{journey_row}/replans",
        json={"trigger_event_id": event.json()["id"], "candidate_count": 3},
    )
    assert response.status_code == 201, response.text
    with SessionLocal() as session:
        proposal = session.get(ReplanProposal, response.json()["id"])
        assert proposal is not None
        proposed = client.get(f"/api/v1/plans/{proposal.proposed_plan_version_id}").json()
    moved = next(item for item in proposed["activities"] if item["place_id"] == target_place)
    delta = int(
        (
            datetime.fromisoformat(moved["start_at"])
            - datetime.fromisoformat(activities[target_place]["start_at"])
        ).total_seconds()
        // 60
    )
    assert delta == 25, delta
