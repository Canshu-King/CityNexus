"""Navigator: a signed Mission triggers one exact edge, without development parameters.

The adapter is deliberately thin: it verifies the Mission belongs to the
Journey, resolves the target/origin with the product chain, reads stored facts
or says UNKNOWN, and acquires through the same gateway/approval path the model
uses.  These arms prove the read side, the acquire side, the ownership refusal,
and that a live provider still needs a receipt inside a PLAN_ONLY Mission.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

import app.core.config as config_module
import app.main as main_module
import app.route_session_operations as route_operations
from app.agent.route_mission import acquire_route_for_mission, route_snapshot
from app.db.models import (
    Journey,
    JourneyLaunchContext,
    JourneyMission,
    MobilityFact,
    Place,
    RouteAcquisitionOperation,
)
from app.db.session import SessionLocal
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(main_module.app)


def _planned_journey() -> tuple[str, str, str]:
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    journey_id = ids["journey_id"]
    generated = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate", json={"candidate_count": 1}
    )
    assert generated.status_code == 201, generated.text
    plan = generated.json()[0]
    selected = client.post(f"/api/v1/journeys/{journey_id}/plans/{plan['id']}/select")
    assert selected.status_code == 200, selected.text
    target = next(item for item in plan["activities"] if item.get("place_id"))
    return journey_id, target["id"], target["place_id"]


def _confirm_origin(journey_id: str, target_activity_id: str, target_place_id: str) -> str:
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        origin = session.scalar(
            select(Place).where(
                Place.city_code == journey.city_code, Place.id != target_place_id
            ).order_by(Place.id)
        )
        assert origin is not None
        stamp = datetime.now(timezone.utc)
        session.add(
            JourneyLaunchContext(
                journey_id=journey_id,
                source_kind="PLANNED_PLACE",
                authority_kind="USER_CONFIRMED_PLANNED_ORIGIN",
                place_id=origin.id,
                target_activity_id=target_activity_id,
                display_name=origin.name,
                latitude=float(origin.latitude or 39.1),
                longitude=float(origin.longitude or 117.2),
                coordinate_crs="WGS84",
                valid_from="2000-01-01T00:00:00+00:00",
                valid_until="2100-01-01T00:00:00+00:00",
                created_at=stamp.isoformat(),
                updated_at=stamp.isoformat(),
            )
        )
        session.commit()
        return origin.id


def _mission(journey_id: str, *, autonomy: str = "PLAN_ONLY") -> str:
    now = datetime.now(timezone.utc).isoformat()
    mission_id = str(uuid4())
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        session.add(
            JourneyMission(
                id=mission_id,
                journey_id=journey_id,
                traveler_id=journey.traveler_id,
                user_text="route this mission",
                requested_autonomy=autonomy,
                status="DRAFT",
                created_at=now,
            )
        )
        session.commit()
    return mission_id


def _journey(journey_id: str) -> Journey:
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        return journey


def test_r1_snapshot_says_unknown_before_anything_was_acquired() -> None:
    journey_id, _target_id, _place_id = _planned_journey()
    mission_id = _mission(journey_id)
    with SessionLocal() as session:
        snapshot = route_snapshot(session, session.get(Journey, journey_id), mission_id)
    assert snapshot["status"] in {"UNKNOWN", "NO_GROUNDED_ORIGIN", "NO_EXACT_TARGET"}
    assert snapshot["eta"]["status"] == "UNKNOWN"
    assert snapshot["cost"]["status"] == "UNKNOWN"
    assert snapshot["options"] == []
    with SessionLocal() as session:
        rows = session.scalars(
            select(RouteAcquisitionOperation).where(
                RouteAcquisitionOperation.journey_id == journey_id
            )
        ).all()
    assert rows == [], "a snapshot must not acquire anything"


def test_r2_mission_acquires_then_snapshot_reads_the_stored_fact() -> None:
    journey_id, target_id, target_place = _planned_journey()
    origin_place = _confirm_origin(journey_id, target_id, target_place)
    mission_id = _mission(journey_id)

    with SessionLocal() as session:
        result = acquire_route_for_mission(
            session,
            session.get(Journey, journey_id),
            mission_id,
            mode="walk",
        )
    assert result["decision"] == "ALLOW_AUTO", result
    assert result["executed"] is True, result
    assert result["result"]["origin"]["key"] == origin_place
    provider_status = result["result"]["status"]
    assert provider_status in {"COMPLETED", "UNAVAILABLE", "FAILED"}

    with SessionLocal() as session:
        snapshot = route_snapshot(
            session, session.get(Journey, journey_id), mission_id, mode="walk"
        )
    if provider_status == "COMPLETED":
        assert snapshot["status"] == "STORED_FACTS", snapshot
        assert snapshot["eta"]["status"] == "STORED_FACT"
        assert snapshot["eta"]["captured_at"]
        assert snapshot["eta"]["source"]
        assert snapshot["limits"]["mode"] == "WALK"
        assert snapshot["cost"]["status"] in {"UNKNOWN", "VERIFIED", "ESTIMATED"}
    else:
        # The strict mock has no explicit matrix fact for this pair.  The honest
        # answer is UNKNOWN, not a zero invented from the blanket default.
        assert snapshot["status"] == "UNKNOWN", snapshot
        assert snapshot["eta"]["status"] == "UNKNOWN"
        assert snapshot["cost"]["status"] == "UNKNOWN"

    with SessionLocal() as session:
        rows = session.scalars(
            select(RouteAcquisitionOperation).where(
                RouteAcquisitionOperation.journey_id == journey_id
            )
        ).all()
    assert len(rows) == 1


def test_r5_snapshot_reads_a_stored_fact_without_acquiring() -> None:
    """The read half against a stored row: ETA source/time and cost status pass through.

    The row is a fixture on purpose; this arm is about the projection, not about
    claiming a provider answered.
    """

    journey_id, target_id, target_place = _planned_journey()
    origin_place = _confirm_origin(journey_id, target_id, target_place)
    mission_id = _mission(journey_id)
    captured_at = "2026-10-18T10:00:00+00:00"
    with SessionLocal() as session:
        session.add(
            MobilityFact(
                id=str(uuid4()),
                journey_id=journey_id,
                option_id=None,
                from_key=origin_place,
                to_key=target_place,
                mode="WALK",
                duration_min=12,
                distance_m=800,
                cost_amount_minor=None,
                currency=None,
                cost_status="UNKNOWN",
                walking_min=12,
                transfers=0,
                weather_exposure="UNKNOWN",
                reliability_score=1.0,
                provider_key="fixture",
                provenance="EXPLICIT_FROZEN_FIXTURE",
                geometry_json="[]",
                captured_at=captured_at,
            )
        )
        session.commit()
        snapshot = route_snapshot(
            session, session.get(Journey, journey_id), mission_id, mode="walk"
        )
    assert snapshot["status"] == "STORED_FACTS", snapshot
    assert snapshot["eta"] == {
        "status": "STORED_FACT",
        "duration_min": 12,
        "source": "EXPLICIT_FROZEN_FIXTURE",
        "provider": "fixture",
        "captured_at": captured_at,
    }
    assert snapshot["cost"]["status"] == "UNKNOWN"
    assert snapshot["limits"]["mode"] == "WALK"
    assert snapshot["limits"]["distance_m"] == 800
    with SessionLocal() as session:
        rows = session.scalars(
            select(RouteAcquisitionOperation).where(
                RouteAcquisitionOperation.journey_id == journey_id
            )
        ).all()
    assert rows == [], "the read projection must not acquire"


def _clone_journey(journey_id: str) -> str:
    with SessionLocal() as session:
        base = session.get(Journey, journey_id)
        assert base is not None
        clone = Journey(
            id=str(uuid4()),
            traveler_id=base.traveler_id,
            title=base.title + " clone",
            city_code=base.city_code,
            timezone=base.timezone,
            start_at=base.start_at,
            end_at=base.end_at,
            budget_currency=base.budget_currency,
            budget_amount_minor=base.budget_amount_minor,
            planning_mode=base.planning_mode,
            status="DRAFT",
            active_plan_version_id=None,
            current_activity_id=None,
            created_at=base.created_at,
            updated_at=base.updated_at,
        )
        session.add(clone)
        session.commit()
        return clone.id


def test_r3_a_mission_from_another_journey_is_refused() -> None:
    journey_id, _target_id, _place_id = _planned_journey()
    mission_id = _mission(journey_id)
    other_id = _clone_journey(journey_id)
    with SessionLocal() as session:
        try:
            route_snapshot(session, session.get(Journey, other_id), mission_id)
        except Exception as exc:  # HTTPException
            assert getattr(exc, "status_code", None) == 404, exc
        else:  # pragma: no cover - the refusal is the assertion
            raise AssertionError("a foreign mission was accepted")


def test_r4_live_provider_in_a_plan_only_mission_still_needs_a_receipt(monkeypatch) -> None:
    journey_id, target_id, target_place = _planned_journey()
    _confirm_origin(journey_id, target_id, target_place)
    mission_id = _mission(journey_id, autonomy="PLAN_ONLY")
    live = dataclasses.replace(
        config_module.settings, live_valhalla_url="http://valhalla.invalid"
    )
    monkeypatch.setattr(config_module, "settings", live)
    monkeypatch.setattr(route_operations, "settings", live)

    with SessionLocal() as session:
        result = acquire_route_for_mission(
            session, session.get(Journey, journey_id), mission_id, mode="walk"
        )
    assert result["decision"] == "REQUIRE_CONFIRMATION", result
    assert result["executed"] is False
    assert result["approval_id"]
    with SessionLocal() as session:
        rows = session.scalars(
            select(RouteAcquisitionOperation).where(
                RouteAcquisitionOperation.journey_id == journey_id
            )
        ).all()
    assert rows == []
