from __future__ import annotations

# PROPOSED R6.1 RED TESTS ONLY.
# Store under evidence on this coordination branch. Copy into the exact R6.1
# worktree only after independent H11 accepts frozen R6.

import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.models import Activity, Place, PlanVersion
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)

def _journey(city: str) -> str:
    traveler = client.post(
        "/api/v1/travelers",
        json={"display_name": "R6.1 role truth", "locale": "zh-CN", "timezone": "Asia/Shanghai"},
    )
    traveler.raise_for_status()
    response = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": traveler.json()["id"],
            "title": "R6.1 explicit role boundary",
            "city_code": city,
            "timezone": "Asia/Shanghai",
            "start_at": "2026-10-02T09:00:00+08:00",
            "end_at": "2026-10-02T20:00:00+08:00",
            "party_size": 1,
            "budget": {"amount_minor": 100000, "currency": "CNY"},
        },
    )
    response.raise_for_status()
    return response.json()["id"]

def _place(place_id: str, *, city: str, category: str, amount: int) -> Place:
    return Place(
        id=place_id,
        provider_key="openstreetmap-replay",
        external_id=f"r61:{place_id}",
        city_code=city,
        name=place_id,
        category=category,
        latitude=27.74,
        longitude=98.66 + (0.01 if place_id.endswith("b") else 0.0),
        tags_json="[]",
        opening_hours_json=json.dumps({"open": "09:00", "close": "18:00"}),
        metadata_json=json.dumps({
            "discovery_mode": "captured_replay",
            "duration_min": 60,
            "cost_minor": amount,
            "price_known": True,
            "cost_evidence": {
                "status": "KNOWN",
                "amount_minor": amount,
                "currency": "CNY",
                "source": "R61_TEST_FIXTURE",
            },
        }),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )

def test_explicit_lodging_ids_cannot_become_generic_visit_activities() -> None:
    client.post("/api/v1/demo/reset").raise_for_status()
    city = "R61-EXPLICIT-LODGING"
    with SessionLocal() as session:
        session.add_all([
            _place("r61-hotel-a", city=city, category="hotel", amount=1000),
            _place("r61-hotel-b", city=city, category="hotel", amount=2000),
        ])
        session.commit()

    journey_id = _journey(city)
    response = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate",
        json={"place_ids": ["r61-hotel-a", "r61-hotel-b"], "candidate_count": 1},
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error"]["reason_code"] == "PLACE_ROLE_NOT_VISIT_ELIGIBLE", body

    with SessionLocal() as session:
        plans = session.scalar(
            select(func.count()).select_from(PlanVersion).where(PlanVersion.journey_id == journey_id)
        )
        activities = session.scalar(
            select(func.count())
            .select_from(Activity)
            .join(PlanVersion, Activity.plan_version_id == PlanVersion.id)
            .where(PlanVersion.journey_id == journey_id)
        )
        assert int(plans or 0) == 0
        assert int(activities or 0) == 0

def test_each_explicit_activity_binds_cost_evidence_from_its_own_place() -> None:
    client.post("/api/v1/demo/reset").raise_for_status()
    city = "R61-COST-EVIDENCE-BINDING"
    with SessionLocal() as session:
        session.add_all([
            _place("r61-park-a", city=city, category="park", amount=0),
            _place("r61-park-b", city=city, category="park", amount=5000),
        ])
        session.commit()

    journey_id = _journey(city)
    response = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate",
        json={"place_ids": ["r61-park-a", "r61-park-b"], "candidate_count": 1},
    )
    assert response.status_code == 201, response.text
    plan_id = response.json()[0]["id"]

    with SessionLocal() as session:
        rows = list(session.scalars(
            select(Activity)
            .where(Activity.plan_version_id == plan_id)
            .order_by(Activity.sequence_no)
        ).all())
        evidence_by_place = {
            row.place_id: json.loads(row.metadata_json or "{}").get("cost_evidence")
            for row in rows
        }

    assert evidence_by_place["r61-park-a"]["amount_minor"] == 0
    assert evidence_by_place["r61-park-b"]["amount_minor"] == 5000
