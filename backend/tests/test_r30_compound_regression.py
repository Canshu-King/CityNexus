"""R30 regression: two grounded opportunity Places form one compound replan.

This intentionally drives the public ``request_replan`` endpoint.  The fixture only
supplies the provider-backed legs needed by the two-place insertion, so a missing
adjacent leg cannot be hidden by the mobility default.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import Activity, Event, Journey, JourneyConstraint
from app.db.session import SessionLocal
from app.main import app
from demo_stage import demo_reset_headers

from _qoder_explicit_demo_mobility import seed_module_mobility


client = TestClient(app)


def test_r30_compound_opportunity_replan_preserves_anchor_and_canonical_legs(monkeypatch):
    seed_module_mobility(
        monkeypatch,
        {
            ("place-tech-art", "place-city-park"): 8,
            ("place-tech-art", "place-design-library"): 12,
            ("place-city-park", "place-design-library"): 10,
            ("place-design-library", "place-city-park"): 10,
            ("place-design-library", "place-river-cruise"): 20,
            ("place-city-park", "place-river-cruise"): 20,
        },
    )
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    journey_id = ids["journey_id"]
    generated = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate",
        json={"candidate_count": 1},
    )
    assert generated.status_code == 201, generated.text
    plan = generated.json()[0]
    assert client.post(
        f"/api/v1/journeys/{journey_id}/plans/{plan['id']}/select"
    ).status_code == 200

    tech = next(item for item in plan["activities"] if item["place_id"] == "place-tech-art")
    assert client.post(f"/api/v1/journeys/{journey_id}/start").status_code == 200
    for activity in plan["activities"]:
        if activity["id"] == tech["id"]:
            break
        completed = client.post(
            f"/api/v1/journeys/{journey_id}/activities/{activity['id']}/complete"
        )
        assert completed.status_code == 200, completed.text

    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        current = session.get(Activity, journey.current_activity_id)
        assert current is not None
        future = session.scalar(
            select(Activity)
            .where(
                Activity.plan_version_id == journey.active_plan_version_id,
                Activity.sequence_no > current.sequence_no,
            )
            .order_by(Activity.sequence_no)
        )
        assert future is not None
        # The stock six-stop fixture leaves only a short gap before the next
        # activity.  Widen that provider-backed opportunity window so the
        # regression exercises the two-place composition rather than a timing
        # refusal.
        shift = timedelta(minutes=180)
        later = session.scalars(
            select(Activity)
            .where(
                Activity.plan_version_id == journey.active_plan_version_id,
                Activity.sequence_no >= future.sequence_no,
            )
            .order_by(Activity.sequence_no)
        ).all()
        for item in later:
            item.start_at = (datetime.fromisoformat(item.start_at) + shift).isoformat()
            item.end_at = (datetime.fromisoformat(item.end_at) + shift).isoformat()
        journey.end_at = (datetime.fromisoformat(journey.end_at) + timedelta(minutes=360)).isoformat()
        for constraint in session.scalars(
            select(JourneyConstraint).where(
                JourneyConstraint.journey_id == journey_id,
                JourneyConstraint.rule_code == "JOURNEY_END_BY",
            )
        ).all():
            params = json.loads(constraint.params_json or "{}")
            params["time"] = journey.end_at
            constraint.params_json = json.dumps(params, sort_keys=True)
        session.flush()
        occurred_at = current.end_at
        event = Event(
            id=str(uuid4()),
            journey_id=journey_id,
            provider_key="citynexus-twin-opportunity",
            provenance="SYSTEM_DERIVED",
            event_type="OPPORTUNITY_WINDOW",
            severity="INFO",
            status="DETECTED",
            affected_activity_id=current.id,
            occurred_at=occurred_at,
            detected_at=occurred_at,
            payload_json=json.dumps(
                {
                    "active_plan_version_id": journey.active_plan_version_id,
                    "current_execution_activity_id": current.id,
                    "next_activity_id": future.id,
                    "next_commitment_start": future.start_at,
                    "safety_buffer_min": 15,
                },
                sort_keys=True,
            ),
            created_at=occurred_at,
        )
        session.add(event)
        session.commit()
        event_id = event.id
        anchor_place_id = future.place_id

    response = client.post(
        f"/api/v1/journeys/{journey_id}/replans",
        json={
            "trigger_event_id": event_id,
            "candidate_count": 5,
            "place_ids": ["place-city-park", "place-design-library"],
        },
        headers={"Idempotency-Key": f"r30-compound-{uuid4()}"},
    )
    assert response.status_code == 201, response.text
    proposals = [
        item
        for item in client.get(f"/api/v1/journeys/{journey_id}/replans").json()
        if item["trigger_event_id"] == event_id
    ]
    compound = next(
        item
        for item in proposals
        if item["diff"].get("candidate_family") == "F4_OPPORTUNITY_INSERTION"
        and set(item["diff"].get("added") or [])
        >= {"place-city-park", "place-design-library"}
    )
    assert compound["hard_constraints_passed"] is True
    assert compound["locked_commitments_preserved"] is True
    evidence = compound["diff"]["opportunity_window_evidence"]
    assert evidence["candidate_place_ids"] == [
        "place-city-park",
        "place-design-library",
    ] or evidence["candidate_place_ids"] == [
        "place-design-library",
        "place-city-park",
    ]
    assert len(evidence["insertions"]) == 2
    assert anchor_place_id not in {
        "place-city-park",
        "place-design-library",
    }
    facts = compound["diff"]["verified_evidence"]["mobility"]["snapshot"]["facts"]
    fact_pairs = {
        (item["origin_key"], item["destination_key"])
        for item in facts
    }
    inserted = evidence["candidate_place_ids"]
    expected_pairs = {
        ("place-tech-art", inserted[0]),
        (inserted[0], inserted[1]),
        (inserted[1], anchor_place_id),
    }
    assert expected_pairs <= fact_pairs
