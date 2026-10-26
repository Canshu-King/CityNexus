"""Signed cross-Journey canonical Place reuse; all provider-shaped rows are TEST_FIXTURE."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from test_bootstrap_place_facts import enabled_settings, signed_place

from app.agent import goal_tasks
from app.db.models import (
    AgentRun,
    AuditLog,
    Journey,
    JourneyMember,
    JourneyMission,
    Place,
    ProviderCall,
    RealPlaceCandidate,
)
from app.db.session import SessionLocal


def _create_journey(client, headers, *, traveler_id: str, city_code: str, title: str) -> str:
    response = client.post(
        "/api/v1/journeys",
        headers=headers,
        json={
            "traveler_id": traveler_id,
            "title": title,
            "city_code": city_code,
            "timezone": "Asia/Shanghai",
            "start_at": "2026-11-01T09:00:00+08:00",
            "end_at": "2026-11-01T18:00:00+08:00",
            "budget": {"amount_minor": 50000, "currency": "CNY"},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_goal_task(client, headers, journey_id: str, *, goal: str) -> str:
    response = client.post(
        f"/api/v1/journeys/{journey_id}/agent/goal-tasks",
        headers=headers,
        json={
            "goal": goal,
            "model_consent": True,
            "online_research_consent": True,
            "max_model_turns": 4,
            "max_tool_calls": 4,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["task_id"]


def _seed_source_task(
    *,
    journey_id: str,
    traveler_id: str,
    place_ids: list[str],
    live_evidence: bool = True,
    source_status: str = "COMPLETED",
) -> str:
    """Seed source ownership and TEST_FIXTURE provider-shaped canonical evidence."""
    stamp = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        member = session.scalar(
            select(JourneyMember).where(
                JourneyMember.journey_id == journey_id,
                JourneyMember.traveler_id == traveler_id,
            )
        )
        assert member is not None
        created = goal_tasks.create_goal_task(
            session,
            journey,
            member,
            goal="TEST_FIXTURE source Journey Place research",
            model_consent=True,
            online_research_consent=True,
            max_model_turns=4,
            max_tool_calls=4,
        )
        mission = session.get(JourneyMission, created["task_id"])
        assert mission is not None
        intent = json.loads(mission.intent_json)
        task = intent["goal_task"]
        task["status"] = source_status
        task["failure_code"] = None
        task["candidate_place_ids"] = list(place_ids)
        task["source_observation_ids"] = ["TEST_FIXTURE_SOURCE_PRIVATE_OBSERVATION"]
        task["conversation"] = [
            {
                "role": "user",
                "text": "TEST_FIXTURE_SOURCE_PRIVATE_CONVERSATION",
                "message_id": "TEST_FIXTURE_SOURCE_PRIVATE_MESSAGE",
                "at": stamp,
            }
        ]
        task["research_places"] = [
            {
                "id": "TEST_FIXTURE_SOURCE_VERIFIED_MARKER",
                "name": "TEST_FIXTURE_SOURCE_PRIVATE_RESEARCH_PLACE",
                "provider": "TEST_FIXTURE",
                "provider_provenance": "LIVE_PROVIDER",
                "region_status": "MATCHED",
            }
        ]
        task["research_routes"] = [{"id": "TEST_FIXTURE_SOURCE_PRIVATE_ROUTE"}]
        task["research_areas"] = [{"id": "TEST_FIXTURE_SOURCE_PRIVATE_AREA"}]
        task["draft_variants"] = [{"id": "TEST_FIXTURE_SOURCE_PRIVATE_VARIANT"}]
        task["draft_artifact"]["revision"] = 19
        task["draft_artifact"]["days"][0]["slots"] = [
            {"title": "TEST_FIXTURE_SOURCE_PRIVATE_OLD_SLOT", "place_id": place_ids[0]}
        ] if place_ids else []
        mission.status = source_status
        mission.completed_at = stamp

        for index, place_id in enumerate(place_ids):
            latitude = 31.2000 + index * 0.01
            longitude = 121.4000 + index * 0.01
            provider_key = "TEST_FIXTURE"
            external_id = f"TEST_FIXTURE:{journey_id}:canonical-{index}"
            session.add(
                Place(
                    id=place_id,
                    provider_key=provider_key,
                    external_id=external_id,
                    city_code=journey.city_code,
                    name=f"TEST_FIXTURE public place {index}",
                    category="park",
                    latitude=latitude,
                    longitude=longitude,
                    opening_hours_json=json.dumps({"status": "UNKNOWN"}),
                    tags_json="[]",
                    metadata_json=json.dumps(
                        {
                            "fixture_label": "TEST_FIXTURE, not an actual provider",
                            "cost_evidence": {"status": "UNKNOWN", "amount_minor": None},
                        }
                    ),
                    updated_at=stamp,
                    coordinate_system="WGS84",
                    source_coordinate_system=None,
                )
            )
            if live_evidence:
                session.add(
                    RealPlaceCandidate(
                        id=str(uuid4()),
                        journey_id=journey_id,
                        provider_key=provider_key,
                        external_id=external_id,
                        city_code=journey.city_code,
                        name=f"TEST_FIXTURE public place {index}",
                        category="park",
                        latitude=latitude,
                        longitude=longitude,
                        tags_json="[]",
                        opening_hours_json=json.dumps({"status": "UNKNOWN"}),
                        metadata_json=json.dumps(
                            {
                                "discovery_mode": "live",
                                "fixture_label": "TEST_FIXTURE, not an actual provider",
                            }
                        ),
                        captured_at=stamp,
                        expires_at=None,
                        distance_m=None,
                        evidence_json=json.dumps(
                            {
                                "provenance": "LIVE_PROVIDER",
                                "provider": provider_key,
                                "fixture_label": "TEST_FIXTURE, not an actual provider",
                            }
                        ),
                        materialized_place_id=place_id,
                        status="DISCOVERED",
                    )
                )
        mission.intent_json = json.dumps(intent, ensure_ascii=False)
        session.commit()
        return mission.id


def _draft_days(place_ids: list[str]) -> list[dict]:
    return [
        {
            "date": "2026-11-01",
            "slots": [
                {
                    "title": f"TEST_FIXTURE reused stop {index + 1}",
                    "time_of_day": "flexible",
                    "notes": "TEST_FIXTURE user-authored selection",
                    "place_id": place_id,
                }
                for index, place_id in enumerate(place_ids)
            ],
        }
    ]


def test_signed_reuse_after_model_timeout_prepares_four_slot_candidate(monkeypatch, signed_place):
    client, owner_headers, _outsider_headers, target_journey_id, *_ = signed_place
    target_task_id = _create_goal_task(
        client, owner_headers, target_journey_id, goal="TEST_FIXTURE four-stop target"
    )

    class TimeoutFixtureAgent:
        provider_key = "TEST_FIXTURE"
        model_key = "TEST_FIXTURE"

        def _complete(self, _messages):
            raise TimeoutError("TEST_FIXTURE simulated model timeout")

    monkeypatch.setattr(goal_tasks, "_new_goal_agent", lambda *_args: TimeoutFixtureAgent())
    target_root = f"/api/v1/journeys/{target_journey_id}/agent/goal-tasks/{target_task_id}"
    failed = client.post(target_root + "/run", headers=owner_headers, json={})
    assert failed.status_code == 200, failed.text
    assert failed.json()["status"] == "FAILED_RECOVERABLE"
    assert failed.json()["failure_code"] == "MODEL_TIMEOUT"
    failed_run_id = failed.json()["latest_run_id"]
    assert failed_run_id

    with SessionLocal() as session:
        target_journey = session.get(Journey, target_journey_id)
        assert target_journey is not None
        target_city = target_journey.city_code
        owner_id = target_journey.traveler_id
    source_journey_id = _create_journey(
        client,
        owner_headers,
        traveler_id=owner_id,
        city_code=target_city,
        title="TEST_FIXTURE same-owner source Journey",
    )
    source_place_ids = [str(uuid4()) for _ in range(5)]
    reused_place_ids = source_place_ids[:4]
    source_task_id = _seed_source_task(
        journey_id=source_journey_id,
        traveler_id=owner_id,
        place_ids=source_place_ids,
    )
    with SessionLocal() as session:
        run_count_before_reuse = session.scalar(select(func.count()).select_from(AgentRun))
        provider_call_count_before_reuse = session.scalar(
            select(func.count()).select_from(ProviderCall)
        )
    draft_path = target_root + "/draft"
    days = _draft_days(reused_place_ids)

    stale = client.put(
        draft_path,
        headers=owner_headers,
        json={
            "expected_revision": 1,
            "days": days,
            "reuse_source_task_id": source_task_id,
        },
    )
    assert stale.status_code == 409, stale.text
    invalid = client.put(
        draft_path,
        headers=owner_headers,
        json={
            "expected_revision": 0,
            "days": [{"date": "2026-11-02", "slots": days[0]["slots"]}],
            "reuse_source_task_id": source_task_id,
        },
    )
    assert invalid.status_code == 422, invalid.text
    with SessionLocal() as session:
        target_mission = session.get(JourneyMission, target_task_id)
        assert target_mission is not None
        target_before_success = json.loads(target_mission.intent_json)["goal_task"]
        assert target_before_success["candidate_place_ids"] == []
        assert target_before_success["draft_artifact"]["revision"] == 0
        prior_draft_events = [
            row
            for row in session.scalars(
                select(AuditLog).where(
                    AuditLog.action == "agent.goal_task.event",
                    AuditLog.entity_id == target_task_id,
                )
            ).all()
            if row.after_json
            and json.loads(row.after_json).get("event_type") == "TASK_DRAFT_UPDATED"
        ]
        assert prior_draft_events == []

    updated = client.put(
        draft_path,
        headers=owner_headers,
        json={
            "expected_revision": 0,
            "days": days,
            "reuse_source_task_id": source_task_id,
        },
    )
    assert updated.status_code == 200, updated.text
    result = updated.json()
    assert result["candidate_place_ids"] == reused_place_ids
    assert result["failure_code"] == "MODEL_TIMEOUT"
    assert result["latest_run_id"] == failed_run_id
    assert result["source_observation_ids"] == []
    assert result["research_places"] == []
    assert result["research_routes"] == []
    assert result["research_areas"] == []
    assert result["draft_variants"] == []
    assert all(
        slot[field] == "UNKNOWN"
        for day in result["draft_artifact"]["days"]
        for slot in day["slots"]
        for field in ("opening_status", "cost_status", "travel_time_status")
    )
    assert all(
        message["text"] != "TEST_FIXTURE_SOURCE_PRIVATE_CONVERSATION"
        for message in result["conversation"]
    )

    schedule = [
        {"day_index": 0, "slot_index": 0, "start_time": "09:00", "end_time": "10:00"},
        {"day_index": 0, "slot_index": 1, "start_time": "10:30", "end_time": "11:30"},
        {"day_index": 0, "slot_index": 2, "start_time": "12:00", "end_time": "13:00"},
        {"day_index": 0, "slot_index": 3, "start_time": "13:30", "end_time": "14:30"},
    ]
    prepared = client.post(
        target_root + "/prepare-plan",
        headers={**owner_headers, "Idempotency-Key": str(uuid4())},
        json={"expected_revision": 1, "schedule": schedule},
    )
    assert prepared.status_code == 201, prepared.text
    assert prepared.json()["slots_count"] == 4
    assert prepared.json()["selected"] is False
    assert prepared.json()["activated"] is False

    with SessionLocal() as session:
        target_mission = session.get(JourneyMission, target_task_id)
        source_mission = session.get(JourneyMission, source_task_id)
        run = session.get(AgentRun, failed_run_id)
        assert target_mission is not None and source_mission is not None and run is not None
        target_task = json.loads(target_mission.intent_json)["goal_task"]
        source_task = json.loads(source_mission.intent_json)["goal_task"]
        assert target_mission.status == "FAILED_RECOVERABLE"
        assert target_mission.failure_reason == "MODEL_TIMEOUT"
        assert target_task["failure_code"] == "MODEL_TIMEOUT"
        assert target_task["latest_run_id"] == failed_run_id
        assert target_task["source_observation_ids"] == []
        assert target_task["research_places"] == []
        assert target_task["conversation"][0]["text"] == "TEST_FIXTURE four-stop target"
        assert source_task["status"] == "COMPLETED"
        assert source_task["source_observation_ids"] == ["TEST_FIXTURE_SOURCE_PRIVATE_OBSERVATION"]
        assert source_task["research_places"][0]["id"] == "TEST_FIXTURE_SOURCE_VERIFIED_MARKER"
        assert run.status == "FAILED_EXTERNAL"
        assert run.provider_key == "TEST_FIXTURE"
        draft_events = [
            json.loads(row.after_json)
            for row in session.scalars(
                select(AuditLog).where(
                    AuditLog.action == "agent.goal_task.event",
                    AuditLog.entity_id == target_task_id,
                )
            ).all()
            if row.after_json and json.loads(row.after_json).get("event_type") == "TASK_DRAFT_UPDATED"
        ]
        assert len(draft_events) == 1
        assert draft_events[0]["reuse_source_task_id"] == source_task_id
        assert draft_events[0]["reused_place_ids"] == reused_place_ids
        assert session.scalar(select(func.count()).select_from(AgentRun)) == run_count_before_reuse
        assert session.scalar(select(func.count()).select_from(ProviderCall)) == provider_call_count_before_reuse
        source_candidates = session.scalars(
            select(RealPlaceCandidate).where(RealPlaceCandidate.journey_id == source_journey_id)
        ).all()
        assert len(source_candidates) == 5
        assert {row.materialized_place_id for row in source_candidates} == set(source_place_ids)
        assert all(row.provider_key == "TEST_FIXTURE" for row in source_candidates)
        canonical_places = [session.get(Place, place_id) for place_id in source_place_ids]
        assert all(place is not None and place.coordinate_system == "WGS84" for place in canonical_places)
        assert all(json.loads(place.opening_hours_json)["status"] == "UNKNOWN" for place in canonical_places)
        assert all(
            json.loads(place.metadata_json)["cost_evidence"]["status"] == "UNKNOWN"
            and json.loads(place.metadata_json)["fixture_label"]
            == "TEST_FIXTURE, not an actual provider"
            for place in canonical_places
        )


def test_signed_reuse_rejects_foreign_owner_without_expanding_target(signed_place):
    client, owner_headers, outsider_headers, target_journey_id, *_ = signed_place
    target_task_id = _create_goal_task(
        client, owner_headers, target_journey_id, goal="TEST_FIXTURE target stays private"
    )
    with SessionLocal() as session:
        target_journey = session.get(Journey, target_journey_id)
        assert target_journey is not None
        city_code = target_journey.city_code
    outsider = client.get("/api/v1/travelers/session", headers=outsider_headers)
    assert outsider.status_code == 200, outsider.text
    outsider_id = outsider.json()["traveler_id"]
    foreign_journey_id = _create_journey(
        client,
        outsider_headers,
        traveler_id=outsider_id,
        city_code=city_code,
        title="TEST_FIXTURE foreign-owner source Journey",
    )
    foreign_place_id = str(uuid4())
    foreign_task_id = _seed_source_task(
        journey_id=foreign_journey_id,
        traveler_id=outsider_id,
        place_ids=[foreign_place_id],
    )
    response = client.put(
        f"/api/v1/journeys/{target_journey_id}/agent/goal-tasks/{target_task_id}/draft",
        headers=owner_headers,
        json={
            "expected_revision": 0,
            "days": _draft_days([foreign_place_id]),
            "reuse_source_task_id": foreign_task_id,
        },
    )
    assert response.status_code == 403, response.text
    with SessionLocal() as session:
        mission = session.get(JourneyMission, target_task_id)
        assert mission is not None
        task = json.loads(mission.intent_json)["goal_task"]
        assert task["candidate_place_ids"] == []
        assert task["draft_artifact"]["revision"] == 0


def test_signed_reuse_rejects_revoked_source_owner_read_scope_without_write(signed_place):
    client, owner_headers, _outsider_headers, target_journey_id, *_ = signed_place
    target_task_id = _create_goal_task(
        client, owner_headers, target_journey_id, goal="TEST_FIXTURE target after source revocation"
    )
    with SessionLocal() as session:
        target_journey = session.get(Journey, target_journey_id)
        assert target_journey is not None
        owner_id = target_journey.traveler_id
        city_code = target_journey.city_code
    source_journey_id = _create_journey(
        client,
        owner_headers,
        traveler_id=owner_id,
        city_code=city_code,
        title="TEST_FIXTURE revoked-source owner Journey",
    )
    place_id = str(uuid4())
    source_task_id = _seed_source_task(
        journey_id=source_journey_id,
        traveler_id=owner_id,
        place_ids=[place_id],
    )
    with SessionLocal() as session:
        source_member = session.scalar(
            select(JourneyMember).where(
                JourneyMember.journey_id == source_journey_id,
                JourneyMember.traveler_id == owner_id,
            )
        )
        assert source_member is not None
        source_member.removed_at = datetime.now(timezone.utc).isoformat()
        session.commit()

    response = client.put(
        f"/api/v1/journeys/{target_journey_id}/agent/goal-tasks/{target_task_id}/draft",
        headers=owner_headers,
        json={
            "expected_revision": 0,
            "days": _draft_days([place_id]),
            "reuse_source_task_id": source_task_id,
        },
    )
    assert response.status_code == 403, response.text
    with SessionLocal() as session:
        target_mission = session.get(JourneyMission, target_task_id)
        assert target_mission is not None
        target_task = json.loads(target_mission.intent_json)["goal_task"]
        assert target_task["candidate_place_ids"] == []
        assert target_task["draft_artifact"]["revision"] == 0


@pytest.mark.parametrize("evidence_mode", ["MISSING", "REPLAY"])
def test_signed_reuse_rejects_legacy_or_replay_source_evidence_without_write(
    signed_place, evidence_mode
):
    client, owner_headers, _outsider_headers, target_journey_id, *_ = signed_place
    target_task_id = _create_goal_task(
        client, owner_headers, target_journey_id, goal="TEST_FIXTURE evidence rejection target"
    )
    with SessionLocal() as session:
        target_journey = session.get(Journey, target_journey_id)
        assert target_journey is not None
        owner_id = target_journey.traveler_id
        city_code = target_journey.city_code
    source_journey_id = _create_journey(
        client,
        owner_headers,
        traveler_id=owner_id,
        city_code=city_code,
        title="TEST_FIXTURE legacy source Journey",
    )
    place_id = str(uuid4())
    source_task_id = _seed_source_task(
        journey_id=source_journey_id,
        traveler_id=owner_id,
        place_ids=[place_id],
        live_evidence=evidence_mode != "MISSING",
        source_status="COMPLETED",
    )
    if evidence_mode == "REPLAY":
        with SessionLocal() as session:
            row = session.scalar(
                select(RealPlaceCandidate).where(
                    RealPlaceCandidate.journey_id == source_journey_id,
                    RealPlaceCandidate.materialized_place_id == place_id,
                )
            )
            assert row is not None
            row.evidence_json = json.dumps(
                {
                    "provenance": "REPLAY",
                    "provider": "TEST_FIXTURE",
                    "fixture_label": "TEST_FIXTURE, not an actual provider",
                }
            )
            session.commit()

    response = client.put(
        f"/api/v1/journeys/{target_journey_id}/agent/goal-tasks/{target_task_id}/draft",
        headers=owner_headers,
        json={
            "expected_revision": 0,
            "days": _draft_days([place_id]),
            "reuse_source_task_id": source_task_id,
        },
    )
    assert response.status_code == 422, response.text
    with SessionLocal() as session:
        mission = session.get(JourneyMission, target_task_id)
        source_mission = session.get(JourneyMission, source_task_id)
        assert mission is not None and source_mission is not None
        target_task = json.loads(mission.intent_json)["goal_task"]
        assert target_task["candidate_place_ids"] == []
        assert target_task["draft_artifact"]["revision"] == 0
        assert json.loads(source_mission.intent_json)["goal_task"]["candidate_place_ids"] == [place_id]
