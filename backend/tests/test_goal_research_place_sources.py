"""Task-local source cache routing for public research leads; no network fixtures."""
from __future__ import annotations

from copy import deepcopy

import pytest
from fastapi import HTTPException

from app.agent import goal_tasks


@pytest.fixture
def signed_goal_task():
    return {
        "journey_id": "TEST_FIXTURE_JOURNEY",
        "candidate_place_ids": ["canonical-place-1"],
        "research_places": [{
            "id": "photon:W/123",
            "name": "TEST_FIXTURE Museum",
            "category": "museum",
            "latitude": 31.23,
            "longitude": 121.47,
            "source_url": "https://www.openstreetmap.org/way/123",
            "provider": "photon",
            "provider_provenance": "LIVE_PROVIDER",
            "opening_status": "UNKNOWN",
            "cost_status": "UNKNOWN",
        }],
    }


def test_source_args_require_an_existing_task_lead_and_reject_urls(signed_goal_task):
    assert goal_tasks._safe_args("research_place_sources", {"place_id": "photon:W/123"}, signed_goal_task) == {
        "place_id": "photon:W/123"
    }
    assert goal_tasks._safe_args("research_place_sources", {"place_id": "canonical-place-1"}, signed_goal_task) == {
        "place_id": "canonical-place-1"
    }
    with pytest.raises(HTTPException) as unknown:
        goal_tasks._safe_args("research_place_sources", {"place_id": "photon:W/999"}, signed_goal_task)
    assert unknown.value.status_code == 403
    with pytest.raises(HTTPException) as url_input:
        goal_tasks._safe_args("research_place_sources", {
            "place_id": "photon:W/123", "url": "https://attacker.invalid/source"
        }, signed_goal_task)
    assert url_input.value.status_code == 422

    untrusted = deepcopy(signed_goal_task)
    untrusted["research_places"][0]["provider_provenance"] = "TEST_PROVIDER"
    with pytest.raises(HTTPException) as wrong_provenance:
        goal_tasks._safe_args("research_place_sources", {"place_id": "photon:W/123"}, untrusted)
    assert wrong_provenance.value.status_code == 403


def test_live_public_lead_returns_only_its_validated_cache(signed_goal_task):
    class Gateway:
        def __init__(self):
            self.calls = []

        def dispatch(self, *args):
            self.calls.append(args)
            return {"tool": "research_place_sources", "status": "SHOULD_NOT_DISPATCH"}

    gateway = Gateway()
    args = goal_tasks._safe_args("research_place_sources", {"place_id": "photon:W/123"}, signed_goal_task)
    raw = goal_tasks._dispatch_gateway_tool(gateway, "research_place_sources", object(), signed_goal_task, args)
    result = goal_tasks._safe_tool_result("research_place_sources", raw)

    assert gateway.calls == []
    assert result["status"] == "CACHED_ONLY"
    assert result["cached_references"] == [{
        "reference_type": "OSM_OBJECT",
        "provider": "photon",
        "url": "https://www.openstreetmap.org/way/123",
        "authority_status": "NON_AUTHORITATIVE",
    }]
    assert result["reference_status"] == "PRESENT"
    assert result["cached_facts"]["name"] == "TEST_FIXTURE Museum"
    assert result["cached_facts"]["latitude"] == 31.23
    assert result["cached_facts"]["longitude"] == 121.47
    assert result["cached_facts"]["opening_status"] == "UNKNOWN"
    assert {"opening_hours", "cost", "availability", "travel_time"} == set(result["not_acquired_fields"])
    assert result["source_discovery_attempted"] is False
    assert result["acquisition_attempted"] is False
    assert "observations" not in result and "observation_id" not in str(result)
    summary = goal_tasks._step_result_summary("research_place_sources", result)
    assert summary["cached_references"][0]["url"] == "https://www.openstreetmap.org/way/123"
    assert set(summary["not_acquired_fields"]) == set(result["not_acquired_fields"])


def test_bad_cached_url_is_omitted_and_canonical_id_keeps_gateway(signed_goal_task):
    class Gateway:
        def __init__(self):
            self.calls = []

        def dispatch(self, name, request):
            self.calls.append((name, request))
            return {"tool": name, "status": "GATEWAY_RESULT"}

    gateway = Gateway()
    tampered = deepcopy(signed_goal_task)
    tampered["research_places"][0]["source_url"] = "https://attacker.invalid/anything"
    args = goal_tasks._safe_args("research_place_sources", {"place_id": "photon:W/123"}, tampered)
    cached = goal_tasks._safe_tool_result("research_place_sources",
        goal_tasks._dispatch_gateway_tool(gateway, "research_place_sources", object(), tampered, args))
    assert cached["status"] == "CACHED_ONLY"
    assert cached["cached_references"] == []
    assert cached["reference_status"] == "NOT_VERIFIED"
    assert cached["not_acquired_fields"]
    assert gateway.calls == []

    request = object()
    canonical_args = goal_tasks._safe_args("research_place_sources", {"place_id": "canonical-place-1"}, tampered)
    canonical = goal_tasks._dispatch_gateway_tool(
        gateway, "research_place_sources", request, tampered, canonical_args)
    assert canonical["status"] == "GATEWAY_RESULT"
    assert gateway.calls == [("research_place_sources", request)]
