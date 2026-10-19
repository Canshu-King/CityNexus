"""Guardian: the live-context watch is ported, and its truth is one typed stream.

The stream is a projection over rows that already exist (`Event`,
`ImpactAssessment`, `GuardianRun`).  These arms prove the projection, the
WATCH_NOT_RUNNING state, the server-owned watch switch, and that a watch without
an active plan is named rather than reported as an empty success.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import app.main as main_module
from app.agent.mission_plan import build_mission_plan
from app.agent.runtime import _MUTATION_TOOLS
from app.agent.tool_catalog import RUNTIME_MCP_ALLOWLIST_V2, TOOL_BY_NAME
from app.core import config as config_module
from app.db.models import (
    Event,
    GuardianRun,
    ImpactAssessment,
    Journey,
    JourneyMission,
    RouteAcquisitionOperation,
)
from app.db.session import SessionLocal
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(main_module.app)
READ = "read_guardian_stream"
REFRESH = "refresh_live_context"


@pytest.fixture(scope="module", autouse=True)
def _schema_present() -> None:
    from app.db.session import ensure_schema

    ensure_schema()


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
                user_text="guardian arm",
                requested_autonomy="PLAN_ONLY",
                status="DRAFT",
                created_at=now,
            )
        )
        session.commit()
    return mission_id


def _call(name: str, journey_id: str, **extra):
    payload = {"request_id": "reform-guardian-" + str(uuid4()), "journey_id": journey_id}
    payload.update(extra)
    return client.post(f"/api/v1/agent/tools/v2/{name}", json=payload)


def test_r1_tools_are_advertised_and_granted_correctly() -> None:
    v1 = {row["name"] for row in client.get("/api/v1/agent/tools").json()}
    v2 = {row["name"] for row in client.get("/api/v1/agent/tools/v2").json()}
    assert {READ, REFRESH} <= v2
    assert not ({READ, REFRESH} & v1), "new capabilities land in v2 only"
    assert {READ, REFRESH} <= RUNTIME_MCP_ALLOWLIST_V2
    assert READ not in _MUTATION_TOOLS
    assert REFRESH in _MUTATION_TOOLS
    assert TOOL_BY_NAME[READ].as_dict()["mutates_domain_truth"] is False
    assert TOOL_BY_NAME[REFRESH].as_dict()["mutates_domain_truth"] is True
    plan_only = build_mission_plan(autonomy="PLAN_ONLY")
    assert READ in set(plan_only.allowed_tools)
    # Arbiter ruling 2026-10-19 item 1: refreshing the live context measures and stores
    # observations; it can invalidate a pending replan but it commits nothing, so it is inside the
    # mandate now. The commitments (accept/replace/reschedule/booking/cancel/commitment-change)
    # are asserted where the grant vocabulary is built, and stay outside.
    assert REFRESH in set(plan_only.allowed_tools), "live measurement is inside the mandate"
    assert REFRESH not in set(plan_only.approval_required_tools)


def test_r2_no_watch_is_a_named_state_not_an_empty_success() -> None:
    journey_id, _target_id, _place_id = _planned_journey()
    answer = _call(READ, journey_id)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "WATCH_NOT_RUNNING", body
    assert body["stream"] == []
    assert body["next_legal_path"]


def test_r3_event_impact_and_action_project_into_one_stream() -> None:
    journey_id, target_id, _place_id = _planned_journey()
    now = datetime.now(timezone.utc).isoformat()
    event_id, impact_id, run_id = str(uuid4()), str(uuid4()), str(uuid4())
    with SessionLocal() as session:
        session.add(
            Event(
                id=event_id,
                journey_id=journey_id,
                provider_key="truth-mesh",
                provenance="SYSTEM_DERIVED",
                event_type="CLOSURE",
                severity="MAJOR",
                status="DETECTED",
                affected_activity_id=target_id,
                occurred_at=now,
                detected_at=now,
                payload_json=json.dumps(
                    {
                        "summary": "Venue closed at the planned hour",
                        "reason_code": "EXPLICIT_CLOSED_STATE",
                        "planned_local_interval": {"start": "09:00", "end": "10:00"},
                    }
                ),
                created_at=now,
            )
        )
        session.add(
            ImpactAssessment(
                id=impact_id,
                event_id=event_id,
                journey_id=journey_id,
                provider_key="deterministic",
                model_key="server",
                status="ASSESSED",
                maturity_stage="DETERMINISTIC",
                selected_activity_id=target_id,
                reason_codes_json=json.dumps(["VENUE_CLOSED"]),
                semantic_reason="The planned visit falls inside a closed interval.",
                created_at=now,
            )
        )
        session.add(
            GuardianRun(
                id=run_id,
                journey_id=journey_id,
                trigger_event_id=event_id,
                decision="RECOVER",
                status="COMPLETED",
                action_status="PROPOSAL_CREATED",
                evidence_fingerprint=str(uuid4()),
                evidence_json="{}",
                reasoning_summary="One indoor alternative preserves the day.",
                created_at=now,
            )
        )
        session.commit()

    answer = _call(READ, journey_id)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "HAS_EVENTS", body
    assert body["counts"] == {
        "events": 1,
        "open_events": 1,
        "impacts": 1,
        "actions": 1,
    }
    item = body["stream"][0]
    assert item["observation"]["event_type"] == "CLOSURE"
    assert item["observation"]["evidence"]["reason_code"] == "EXPLICIT_CLOSED_STATE"
    assert item["impact"]["selected_activity_id"] == target_id
    assert item["impact"]["reason_codes"] == ["VENUE_CLOSED"]
    assert item["proposed_action"]["action_status"] == "PROPOSAL_CREATED"
    assert item["proposed_action"]["reasoning_summary"]


def test_r4_refresh_refuses_when_the_server_switch_is_off(monkeypatch) -> None:
    journey_id, _target_id, _place_id = _planned_journey()
    monkeypatch.setattr(
        config_module,
        "settings",
        config_module.settings.__class__(**{**config_module.settings.__dict__, "guardian_autorun": False}),
    )

    def must_not_run(*_args, **_kwargs):
        raise AssertionError("a provider ran while the Guardian watch was off")

    import app.live_context_watch as watch_module

    monkeypatch.setattr(watch_module, "run_live_context_watch", must_not_run)
    answer = _call(REFRESH, journey_id)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "WATCH_NOT_ENABLED", body
    assert body["reason_code"] == "GUARDIAN_AUTORUN_OFF"
    assert body["stream"] == []


def test_r5_refresh_names_a_journey_without_an_active_plan(monkeypatch) -> None:
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    journey_id = ids["journey_id"]
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        journey.active_plan_version_id = None
        session.commit()
    monkeypatch.setattr(
        config_module,
        "settings",
        config_module.settings.__class__(**{**config_module.settings.__dict__, "guardian_autorun": True}),
    )
    answer = _call(REFRESH, journey_id)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "NO_ACTIVE_PLAN", body
    assert body["reason_code"] == "WATCH_REQUIRES_ACTIVE_PLAN"


def test_r6_refresh_runs_the_watch_only_when_enabled(monkeypatch) -> None:
    journey_id, _target_id, _place_id = _planned_journey()
    monkeypatch.setattr(
        config_module,
        "settings",
        config_module.settings.__class__(**{**config_module.settings.__dict__, "guardian_autorun": True}),
    )
    import app.live_context_watch as watch_module

    def canned(*_args, **_kwargs):
        return {"refreshed": True, "observations": [], "conflicts": []}

    monkeypatch.setattr(watch_module, "run_live_context_watch", canned)
    answer = _call(REFRESH, journey_id)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["status"] == "REFRESHED", body
    assert body["watch"]["refreshed"] is True
