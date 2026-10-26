from __future__ import annotations

import json
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.agent import goal_amap, goal_tasks
from app.db.models import JourneyMission, Place, ProviderCall, RealPlaceCandidate
from app.db.session import SessionLocal
from app.agent.goal_place_identity import attach_canonical_places
from test_bootstrap_place_facts import enabled_settings, signed_place  # noqa: F401
from test_goal_tasks import goal_scope


def _provider_place(external_id: str = "amap:B00001", adcode: str = "350825") -> dict:
    return {
        "external_id": external_id,
        "name": "TEST_FIXTURE 冠豸山",
        "category": "scenic",
        "latitude": 25.7,
        "longitude": 116.7,
        "adcode": adcode,
    }


def _lead(receipt_id: str | None, *, adcode: str = "350825") -> dict:
    lead = {
        "id": "amap:B00001",
        "provider": "amap",
        "provider_object_id": "B00001",
        "name": "TEST_FIXTURE 冠豸山",
        "category": "scenic",
        "latitude": 25.7,
        "longitude": 116.7,
        "coordinate_system": "GCJ02",
        "source_url": "https://uri.amap.com/marker?position=116.7,25.7",
        "provider_provenance": "LIVE_PROVIDER",
        "region_status": "MATCHED" if adcode else "UNKNOWN",
        "requested_adcode": "350825",
        "adcode": adcode,
        "opening_status": "UNKNOWN",
        "cost_status": "UNKNOWN",
    }
    if receipt_id:
        lead["provider_call_id"] = receipt_id
    return lead


def _stored_metadata(session, journey_id: str, external_id: str) -> tuple[dict, dict]:
    candidate = session.scalar(
        select(RealPlaceCandidate).where(
            RealPlaceCandidate.journey_id == journey_id,
            RealPlaceCandidate.external_id == external_id,
        )
    )
    assert candidate is not None
    place = session.get(Place, candidate.materialized_place_id)
    assert place is not None
    return json.loads(candidate.metadata_json), json.loads(place.metadata_json)


def test_declarative_amap_receipt_matching_reaches_candidate_and_place_metadata(goal_scope):
    session, journey, _member = goal_scope
    raw = {"status": "ok", "places": [_provider_place()]}
    receipt = goal_amap._receipt(
        session,
        "goal_amap_search",
        {"query": "TEST_FIXTURE 冠豸山", "adcode": "350825", "center_place_id": None, "limit": 8},
        raw,
    )
    lead = _lead(receipt["provider_call_id"])
    task = {"journey_id": str(journey.id), "research_places": [lead]}

    attached = attach_canonical_places(session, journey, task, [lead])
    session.flush()

    assert attached == {"amap:B00001": lead["canonical_place_id"]}
    candidate_metadata, place_metadata = _stored_metadata(session, str(journey.id), "amap:B00001")
    expected = {
        "status": "VERIFIED",
        "provider_call_id": receipt["provider_call_id"],
        "provider_key": "amap-web-service",
        "operation": "goal_amap_search",
        "requested_adcode": "350825",
        "adcode": "350825",
        "provider_object_id": "B00001",
    }
    assert candidate_metadata["source_receipt"] == expected
    assert place_metadata["source_receipt"] == expected


@pytest.mark.parametrize(
    ("call_status", "operation", "provider_key", "request_adcode", "response_status",
     "response_external_id", "response_adcode", "include_receipt", "store_on_task", "same_journey"),
    [
        ("SUCCESS", "goal_amap_search", "amap-web-service", "350825", "RESULTS", "amap:OTHER", "350825", True, True, True),
        ("SUCCESS", "goal_amap_search", "amap-web-service", "350825", "ERROR", "amap:B00001", "350825", True, True, True),
        ("FAILURE", "goal_amap_search", "amap-web-service", "350825", "RESULTS", "amap:B00001", "350825", True, True, True),
        ("SUCCESS", "bootstrap_city_discovery", "amap-web-service", "350825", "RESULTS", "amap:B00001", "350825", True, True, True),
        ("SUCCESS", "goal_amap_search", "photon", "350825", "RESULTS", "amap:B00001", "350825", True, True, True),
        ("SUCCESS", "goal_amap_search", "amap-web-service", "110000", "RESULTS", "amap:B00001", "350825", True, True, True),
        ("SUCCESS", "goal_amap_search", "amap-web-service", "350825", "RESULTS", "amap:B00001", "350923", True, True, True),
        ("SUCCESS", "goal_amap_search", "amap-web-service", "350825", "RESULTS", "amap:B00001", None, True, True, True),
        ("SUCCESS", "goal_amap_search", "amap-web-service", "350825", "RESULTS", "amap:B00001", "350825", False, True, True),
        ("SUCCESS", "goal_amap_search", "amap-web-service", "350825", "RESULTS", "amap:B00001", "350825", True, False, True),
        ("SUCCESS", "goal_amap_search", "amap-web-service", "350825", "RESULTS", "amap:B00001", "350825", True, True, False),
    ],
)
def test_error_wrong_object_rejected_or_missing_receipt_stays_unknown(
    goal_scope, call_status, operation, provider_key, request_adcode, response_status,
    response_external_id, response_adcode, include_receipt, store_on_task, same_journey,
):
    session, journey, _member = goal_scope
    receipt_id = str(uuid4())
    if include_receipt:
        session.add(
            ProviderCall(
                id=receipt_id,
                provider_key=provider_key,
                operation=operation,
                request_json=json.dumps({"query": "TEST_FIXTURE 冠豸山", "adcode": request_adcode, "center_place_id": None}),
                response_json=json.dumps({"status": response_status, "places": [_provider_place(response_external_id, response_adcode)]}),
                status=call_status,
                latency_ms=None,
                created_at="2026-10-26T00:00:00+00:00",
            )
        )
    lead = _lead(receipt_id if include_receipt else None, adcode="" if response_adcode is None else "350825")
    task = {
        "journey_id": str(journey.id) if same_journey else str(uuid4()),
        "research_places": [lead] if store_on_task else [],
    }

    attach_canonical_places(session, journey, task, [lead])
    session.flush()

    candidate_metadata, place_metadata = _stored_metadata(session, str(journey.id), "amap:B00001")
    assert candidate_metadata.get("source_receipt") is None
    assert place_metadata.get("source_receipt") is None
    assert receipt_id not in json.dumps(candidate_metadata)
    assert receipt_id not in json.dumps(place_metadata)


def test_signed_goal_task_discovery_persists_verified_receipt_lineage(monkeypatch, signed_place):
    client, owner_headers, _outsider_headers, journey_id, *_ = signed_place

    class AmapFixture:
        def close(self):
            pass

        def district(self, query):
            return {
                "status": "ok",
                "http_status": 200,
                "districts": [{"name": "连城县", "adcode": "350825", "level": "district"}],
            }

        def search(self, query, **_kwargs):
            return {"status": "ok", "http_status": 200, "places": [_provider_place()]}

    class FixtureAgent:
        provider_key = model_key = "TEST_FIXTURE"

        def __init__(self):
            self.turn = 0

        def _complete(self, _messages):
            self.turn += 1
            if self.turn == 1:
                name, args = "discover_places", {"query": "TEST_FIXTURE 冠豸山", "source": "amap"}
                return {"tool_calls": [{
                    "id": f"fixture-{self.turn}",
                    "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)},
                }]}
            return {"content": "TEST_FIXTURE 已保存研究地点"}

    created = client.post(
        f"/api/v1/journeys/{journey_id}/agent/goal-tasks",
        headers=owner_headers,
        json={
            "goal": "TEST_FIXTURE 研究冠豸山并整理行程",
            "model_consent": True,
            "online_research_consent": True,
            "max_model_turns": 4,
            "max_tool_calls": 4,
        },
    )
    assert created.status_code == 201, created.text
    monkeypatch.setattr(goal_amap, "settings", replace(goal_amap.settings, amap_web_key="TEST_FIXTURE"))
    monkeypatch.setattr(goal_amap, "_client", AmapFixture)
    monkeypatch.setattr("app.agent.goal_artifacts.public_city_label", lambda *_args: "连城县")
    monkeypatch.setattr(goal_tasks, "_new_goal_agent", lambda *_args: FixtureAgent())

    run = client.post(
        f"/api/v1/journeys/{journey_id}/agent/goal-tasks/{created.json()['task_id']}/run",
        headers=owner_headers,
        json={},
    )
    assert run.status_code == 200, run.text

    with SessionLocal() as session:
        mission = session.get(JourneyMission, created.json()["task_id"])
        intent = json.loads(mission.intent_json)
        task = intent["goal_task"]
        lead = next(item for item in task["research_places"] if item.get("provider_object_id") == "B00001")
        assert lead["provider_call_id"]
        assert lead["requested_adcode"] == "350825"
        assert lead["adcode"] == "350825"
        candidate = session.scalar(select(RealPlaceCandidate).where(
            RealPlaceCandidate.journey_id == journey_id,
            RealPlaceCandidate.external_id == "amap:B00001",
        ))
        assert candidate is not None
        canonical = session.get(Place, candidate.materialized_place_id)
        assert canonical is not None
        candidate_receipt = json.loads(candidate.metadata_json)["source_receipt"]
        place_receipt = json.loads(canonical.metadata_json)["source_receipt"]
        assert candidate_receipt == place_receipt
        assert candidate_receipt["provider_call_id"] == lead["provider_call_id"]
        assert candidate_receipt["requested_adcode"] == lead["requested_adcode"]
        assert candidate_receipt["adcode"] == lead["adcode"]
