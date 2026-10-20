"""Classroom mode: search first, estimate when the provider cannot answer, never pretend.

The user's instruction behind this slice is "让 Agent 尽量搜出来，搜不出就估计，不要畏首畏尾"
-- a coursework demo must keep moving when Photon/Overpass/Valhalla/SearXNG are not
configured.  The switch is `CITYNEXUS_CLASSROOM_MODE=true`; off by default.

These arms are paired, and the negative arms are the point:

  r1/r4/r6/r7/r8  strict behaviour (switch off) -- a dead end stays a dead end;
  r2/r3/r5/r7/r8  classroom behaviour (switch on) -- the same call answers with a
                  labelled `MODEL_ESTIMATE`.

and one arm guards the line that must NOT move: an estimate never becomes feasibility
evidence (r6), never becomes a Place fact (r8), never becomes a captured web page (r2),
and never turns an unknown opening-hours state into a green light (r7).
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

import app.core.config as config_module
import app.main as main_module
import app.route_session_operations as route_operations
from app.classroom_mode import AUTHORITY, classroom_mode
from app.db.models import (
    Activity,
    Journey,
    JourneyLaunchContext,
    JourneyMission,
    MobilityFact,
    Place,
    Traveler,
    WebObservation,
)
from app.db.session import SessionLocal
from app.execution.route_session_contract import RouteRequest
from app.integrations.mobility.snapshot_capture import MobilitySnapshotCaptureError
from app.integrations.web import source_discovery
from app.integrations.web.public_region import REGION_PENDING
from app.live_context_watch import classify_opening_hours
from app.replanning.provider_snapshots import SYNTHETIC_DEFAULT
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(main_module.app)


@pytest.fixture(scope="module", autouse=True)
def _schema_present() -> None:
    from app.db.session import ensure_schema

    ensure_schema()


def _classroom(monkeypatch, on: bool) -> None:
    monkeypatch.setattr(
        config_module,
        "settings",
        replace(config_module.settings, classroom_mode=on),
    )
    assert classroom_mode() is on


def _journey(city_code: str = "CN-XIAMEN", title: str = "Classroom arms") -> str:
    now = datetime.now(timezone.utc)
    traveler_id, journey_id = str(uuid4()), str(uuid4())
    with SessionLocal() as session:
        session.add(
            Traveler(
                id=traveler_id,
                display_name="classroom arm",
                email=None,
                locale="zh-CN",
                timezone="Asia/Shanghai",
                created_at=now.isoformat(),
                updated_at=now.isoformat(),
            )
        )
        session.flush()
        session.add(
            Journey(
                id=journey_id,
                traveler_id=traveler_id,
                title=title,
                city_code=city_code,
                timezone="Asia/Shanghai",
                start_at=now.isoformat(),
                end_at=(now + timedelta(days=2)).isoformat(),
                budget_currency="CNY",
                budget_amount_minor=90000,
                planning_mode="balanced",
                status="DRAFT",
                active_plan_version_id=None,
                current_activity_id=None,
                created_at=now.isoformat(),
                updated_at=now.isoformat(),
            )
        )
        session.commit()
    return journey_id


def _leads_call(journey_id: str, topic: str) -> tuple[int, dict]:
    response = client.post(
        "/api/v1/agent/tools/v2/discover_source_leads",
        json={
            "request_id": "classroom-leads-" + str(uuid4()),
            "journey_id": journey_id,
            "topic": topic,
        },
    )
    return response.status_code, response.json()


def _no_provider(monkeypatch) -> None:
    monkeypatch.setattr(
        source_discovery, "provider_availability", lambda: {"web": False, "searxng": False}
    )


def test_r1_strict_no_provider_is_still_a_named_dead_end(monkeypatch) -> None:
    _classroom(monkeypatch, False)
    _no_provider(monkeypatch)
    journey_id = _journey()
    status, body = _leads_call(journey_id, "古村落")
    assert status == 200, body
    assert body["status"] == "SOURCE_DISCOVERY_UNAVAILABLE"
    assert "estimate" not in body, "the switch is off, so nothing may be estimated"
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(WebObservation)
                .where(WebObservation.journey_id == journey_id)
            )
            == 0
        )


def test_r2_classroom_estimates_angles_without_inventing_a_page(monkeypatch) -> None:
    _classroom(monkeypatch, True)
    _no_provider(monkeypatch)
    journey_id = _journey()
    status, body = _leads_call(journey_id, "古村落")
    assert status == 200, body
    assert body["status"] == "ESTIMATED"
    assert body["authority"] == AUTHORITY
    assert body["leads"] == []
    estimate = body["estimate"]
    assert estimate["authority_eligible"] is False
    assert estimate["kind"] == "source_angles"
    assert len(estimate["angles"]) == 4
    assert "古村落" in estimate["angles"][0]
    # The whole payload must be free of a URL: an estimate has no page to cite, and a
    # fabricated link is indistinguishable from a captured one on the next read.
    assert "http" not in json.dumps(body, ensure_ascii=False).lower()
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(WebObservation)
                .where(WebObservation.journey_id == journey_id)
            )
            == 0
        )


def test_r3_classroom_unconfirmed_region_still_sends_no_query(monkeypatch) -> None:
    _classroom(monkeypatch, True)
    _no_provider(monkeypatch)

    def must_not_run(*_args, **_kwargs):
        raise AssertionError("a search ran without a confirmed public region")

    monkeypatch.setattr(source_discovery, "run_web_search", must_not_run)
    journey_id = _journey(city_code="CN-RV-random", title="周末随便走走")
    status, body = _leads_call(journey_id, "古村落")
    assert status == 200, body
    assert body["status"] == "ESTIMATED"
    assert body["region"]["confirmed"] is False
    assert body["query"] is None
    assert "city not confirmed" in body["estimate"]["region"]


def test_r4_strict_unconfirmed_region_is_still_region_pending(monkeypatch) -> None:
    _classroom(monkeypatch, False)
    journey_id = _journey(city_code="CN-RV-random", title="周末随便走走")
    status, body = _leads_call(journey_id, "古村落")
    assert status == 200, body
    assert body["status"] == REGION_PENDING
    assert "estimate" not in body


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


def _ground_origin(journey_id: str, target_activity_id: str, target_place_id: str) -> None:
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


def _mission(journey_id: str) -> str:
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
                user_text="classroom route arm",
                requested_autonomy="PLAN_ONLY",
                status="DRAFT",
                created_at=now,
            )
        )
        session.commit()
    return mission_id


def _snapshot(journey_id: str, mission_id: str) -> dict:
    from app.agent.route_mission import route_snapshot

    with SessionLocal() as session:
        return route_snapshot(session, session.get(Journey, journey_id), mission_id)


def _unacquired_snapshot() -> dict:
    """One grounded origin -> active target edge with no MobilityFact stored for it.

    The demo seed's facts for that pair are deleted first, so the read side genuinely has
    nothing -- that is the state classroom mode must estimate around instead of fake out.
    """

    journey_id, target_id, target_place = _planned_journey()
    origin_place = _ground_origin(journey_id, target_id, target_place)
    mission_id = _mission(journey_id)
    with SessionLocal() as session:
        session.query(MobilityFact).filter(
            MobilityFact.journey_id == journey_id,
            MobilityFact.to_key.in_([target_place, origin_place]),
        ).delete(synchronize_session=False)
        session.commit()
    return _snapshot(journey_id, mission_id)


def test_r5_strict_unknown_edge_stays_unknown_classroom_models_the_eta(monkeypatch) -> None:
    _classroom(monkeypatch, False)
    strict = _unacquired_snapshot()
    assert strict["status"] == "UNKNOWN", strict
    assert strict["eta"] == {"status": "UNKNOWN"}
    assert "estimate" not in strict
    assert strict["authority"] == "STORED_FACT_ONLY"

    _classroom(monkeypatch, True)
    relaxed = _unacquired_snapshot()
    assert relaxed["status"] == "UNKNOWN", relaxed
    eta = relaxed["eta"]
    assert eta["status"] == "ESTIMATED_CLASSROOM"
    assert eta["authority"] == AUTHORITY
    assert eta["authority_eligible"] is False
    assert eta["duration_min"] > 0
    assert eta["basis"]
    assert relaxed["authority"] == AUTHORITY


def test_r6_a_classroom_number_still_cannot_drive_hard_feasibility(monkeypatch) -> None:
    """The line the switch must not cross: display yes, feasibility no."""

    _classroom(monkeypatch, True)
    fact = SimpleNamespace(fact_quality=SYNTHETIC_DEFAULT, minutes=20)
    mobility = SimpleNamespace(
        facts={("a", "b"): fact},
        hard_minutes=lambda *_: (_ for _ in ()).throw(AssertionError("gate bypassed")),
        estimate_minutes=lambda *_: 20,
    )
    with pytest.raises(main_module.MobilityEvidenceNotHardEligible) as refused:
        main_module._hard_leg_minutes(mobility, "a", "b")
    assert refused.value.fact_quality == SYNTHETIC_DEFAULT


def test_r7_opening_hours_unknown_gets_an_estimate_but_stays_unknown(monkeypatch) -> None:
    journey_id, target_id, _place = _planned_journey()
    with SessionLocal() as session:
        activity = session.get(Activity, target_id)
        journey = session.get(Journey, journey_id)
        place = session.get(Place, activity.place_id)
        kwargs = {
            "activity": activity,
            "place": place,
            "opening": {"status": "UNKNOWN"},
            "timezone_name": journey.timezone,
        }

        _classroom(monkeypatch, False)
        strict = classify_opening_hours(**kwargs)
        assert strict["status"] == "UNKNOWN"
        assert "estimate" not in strict

        _classroom(monkeypatch, True)
        relaxed = classify_opening_hours(**kwargs)
        assert relaxed["status"] == "UNKNOWN", "an estimate must not close or open a venue"
        assert relaxed["reason_code"] == "OPENING_HOURS_UNQUALIFIED"
        window = relaxed["estimate"]
        assert window["authority"] == AUTHORITY
        assert window["authority_eligible"] is False
        assert window["open"] and window["close"]
        assert window["planned_local_interval_fit"] in {
            "INSIDE_ESTIMATED_WINDOW",
            "EARLY_OF_WINDOW",
            "LATE_OF_WINDOW",
            "OVERNIGHT_UNDECIDABLE",
        }


def test_r8_classroom_route_capture_falls_back_and_stays_inert_in_the_gate(monkeypatch) -> None:
    """The on-demand capture path: strict refuses the pair, classroom captures a tagged default.

    Both arms stop at the provider boundary with a probe exception, so nothing lands --
    what is asserted is the flag the switch puts on the capture call, which is the only
    thing that decides whether the stored row is a measurement or a fixture default.
    """

    seen: list[dict] = []

    def probe(_session, _journey, pairs, **kwargs):
        seen.append({"pairs": list(pairs), **kwargs})
        raise MobilitySnapshotCaptureError("classroom probe")

    monkeypatch.setattr(route_operations, "capture_runtime_mobility_snapshot", probe)
    journey_id, _target_id, target_place = _planned_journey()
    request = RouteRequest(
        journey_id=journey_id,
        origin_key="origin-" + str(uuid4()),
        target_key=target_place,
        target_activity_id=None,
        requested_mode="TRANSIT",
    )

    _classroom(monkeypatch, False)
    with SessionLocal() as session:
        route_operations.submit_operation(session, session.get(Journey, journey_id), request)
    _classroom(monkeypatch, True)
    with SessionLocal() as session:
        route_operations.submit_operation(
            session,
            session.get(Journey, journey_id),
            replace(request, origin_key="origin-" + str(uuid4())),
        )

    assert len(seen) == 2, seen
    assert seen[0]["require_explicit_facts"] is True, "strict must stay strict"
    assert seen[1]["require_explicit_facts"] is False, "classroom must fall back"


def test_r9_the_prompt_invites_estimates_only_while_the_switch_is_on(monkeypatch) -> None:
    """The model must hear about the estimate vocabulary exactly when the tools use it."""

    from test_qoder_prompt_tool_grant_is_per_mission import _prompt_for

    _classroom(monkeypatch, False)
    strict, _granted, _supplied = _prompt_for("PLAN_ONLY")
    assert "MODEL_ESTIMATE" not in strict

    _classroom(monkeypatch, True)
    relaxed, granted, supplied = _prompt_for("PLAN_ONLY")
    assert "MODEL_ESTIMATE" in relaxed
    assert "never present it as a provider measurement" in relaxed
    assert "Never invent" in relaxed, "the estimate sentence must not replace the invention ban"
    assert granted <= supplied
