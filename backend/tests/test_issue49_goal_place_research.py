"""Signed task-scoped place research contract; discovery is monkeypatched TEST_FIXTURE data."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from test_bootstrap_place_facts import enabled_settings, signed_place  # noqa: F401
from app.db.models import AgentRun, AgentRunStep, Journey, JourneyMission
from app.db.session import SessionLocal


def _task(client, headers, journey_id, *, online_consent=True):
    response = client.post(
        f"/api/v1/journeys/{journey_id}/agent/goal-tasks",
        headers=headers,
        json={
            "goal": "TEST_FIXTURE 在旅行城市找两处适合慢逛的地方",
            "model_consent": True,
            "online_research_consent": online_consent,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["task_id"]


def _set_task(journey_id, task_id, **changes):
    with SessionLocal() as session:
        mission = session.get(JourneyMission, task_id)
        assert mission is not None
        assert mission.journey_id == journey_id
        intent = json.loads(mission.intent_json)
        task = intent["goal_task"]
        task.update(changes)
        mission.intent_json = json.dumps(intent, ensure_ascii=False, sort_keys=True)
        session.commit()


def _set_journey_status(journey_id, status):
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        assert journey is not None
        journey.status = status
        session.commit()


def _make_other_journey_task(client, owner_headers, existing_journey_id):
    with SessionLocal() as session:
        existing_journey = session.get(Journey, existing_journey_id)
        assert existing_journey is not None
        traveler_id = existing_journey.traveler_id
    created = client.post(
        "/api/v1/journeys",
        headers=owner_headers,
        json={
            "traveler_id": traveler_id,
            "title": "TEST_FIXTURE unrelated goal task",
            "city_code": uuid4().hex,
            "timezone": "Asia/Shanghai",
            "start_at": "2026-11-02T09:00:00+08:00",
            "end_at": "2026-11-02T18:00:00+08:00",
            "budget": {"amount_minor": 50000, "currency": "CNY"},
        },
    )
    # Traveler IDs are not access tokens. Resolve the owner from the signed Journey fixture.
    if created.status_code != 201:
        pytest.fail(f"could not create unrelated TEST_FIXTURE Journey: {created.text}")
    journey_id = created.json()["id"]
    return journey_id, _task(client, owner_headers, journey_id)


def _error_reason(response):
    error = response.json().get("error", {})
    return error.get("reason_code") or error.get("message")


@pytest.mark.parametrize(
    ("case", "expected_status", "expected_reason"),
    [
        ("anonymous", 401, None),
        ("outsider", 403, None),
        ("wrong_task", 404, None),
        ("missing_key", 422, None),
        ("active_journey", 409, None),
        ("working", 409, "DRAFT_RESEARCH_RUNNING"),
        ("consent_denied", 403, "ONLINE_RESEARCH_CONSENT_REQUIRED"),
        ("explicit_false", 422, None),
        ("numeric_consent", 422, None),
        ("string_consent", 422, None),
    ],
)
def test_place_research_refuses_before_discovery(
    monkeypatch, signed_place, case, expected_status, expected_reason
):
    import app.agent.goal_place_research as research

    client, owner, outsider, journey_id, *_ = signed_place
    task_id = _task(client, owner, journey_id)
    calls = []

    def discover(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("the provider seam must not be reached for a refused request")

    monkeypatch.setattr(research, "discover_goal_places", discover)
    request_journey_id, request_task_id = journey_id, task_id
    headers = {**owner, "Idempotency-Key": str(uuid4())}
    body = {"query": "TEST_FIXTURE 慢逛景点", "provider_consent": True}

    if case == "anonymous":
        headers = {"Idempotency-Key": str(uuid4())}
    elif case == "outsider":
        headers = {**outsider, "Idempotency-Key": str(uuid4())}
    elif case == "wrong_task":
        _other_journey_id, _other_task = _make_other_journey_task(client, owner, journey_id)
        # Pair this Journey with the first Journey's task to exercise the binding check.
        request_journey_id, request_task_id = journey_id, _other_task
    elif case == "missing_key":
        headers = dict(owner)
    elif case == "active_journey":
        _set_journey_status(journey_id, "ACTIVE")
    elif case == "working":
        _set_task(journey_id, task_id, status="WORKING")
    elif case == "consent_denied":
        _set_task(journey_id, task_id, consent={"model": True, "online_research": False})
    elif case == "explicit_false":
        body["provider_consent"] = False
    elif case == "numeric_consent":
        body["provider_consent"] = 1
    elif case == "string_consent":
        body["provider_consent"] = "true"

    response = client.post(
        f"/api/v1/journeys/{request_journey_id}/agent/goal-tasks/{request_task_id}/research-places",
        headers=headers,
        json=body,
    )

    assert response.status_code == expected_status, response.text
    if expected_reason:
        assert _error_reason(response) == expected_reason, response.text
    assert calls == []


def _run_counts(task_id):
    with SessionLocal() as session:
        runs = session.scalar(select(func.count()).select_from(AgentRun).where(AgentRun.mission_id == task_id))
        steps = session.scalar(
            select(func.count())
            .select_from(AgentRunStep)
            .join(AgentRun, AgentRun.id == AgentRunStep.run_id)
            .where(AgentRun.mission_id == task_id)
        )
        return runs, steps


def test_place_research_persists_canonical_sources_without_changing_failed_model_state(
    monkeypatch, signed_place
):
    import app.agent.goal_place_research as research

    client, owner, _outsider, journey_id, *_ = signed_place
    task_id = _task(client, owner, journey_id)
    usage = {"model_turns": 3, "tool_calls": 2}
    _set_task(journey_id, task_id, status="FAILED_RECOVERABLE", failure_code="MODEL_TIMEOUT", usage=usage)
    before_runs = _run_counts(task_id)
    calls = []
    canonical_id = "place-issue49-test-fixture-01"
    lead = {
        "id": "amap:ISSUE49TESTFIXTURE01",
        "provider": "amap",
        "provider_object_id": "ISSUE49TESTFIXTURE01",
        "canonical_place_id": canonical_id,
        "name": "TEST_FIXTURE 湖畔慢行步道",
        "provider_provenance": "LIVE_PROVIDER",
        "region_status": "MATCHED",
        "source_url": "https://uri.amap.com/marker?position=121.4,31.2",
    }

    def discover(session, journey, task, query, source, public_action):
        calls.append((query, source))
        task["amap_region"] = {
            "city": "TEST_FIXTURE 上海",
            "adcode": "TEST_FIXTURE_ADCODE",
            "status": "RESOLVED",
        }
        task["research_places"] = [lead]
        task["candidate_place_ids"] = [canonical_id]
        return {
            "status": "SUCCESS",
            "reason_code": None,
            "source": source,
            "provider_call_id": "provider-call-issue49-test-fixture",
            "places": [lead],
            "candidate_place_ids": [canonical_id],
        }

    monkeypatch.setattr(research, "discover_goal_places", discover)
    path = f"/api/v1/journeys/{journey_id}/agent/goal-tasks/{task_id}/research-places"
    headers = {**owner, "Idempotency-Key": str(uuid4())}
    body = {"query": "TEST_FIXTURE 湖畔慢行步道", "provider_consent": True}

    first = client.post(path, headers=headers, json=body)
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["journey_id"] == journey_id
    assert result["task_id"] == task_id
    assert result["status"] == "SUCCESS"
    assert "reason_code" in result
    assert result["source"] == "amap"
    assert result["provider_call_id"] == "provider-call-issue49-test-fixture"
    assert result["places"][0]["id"] == lead["id"]
    assert result["candidate_place_ids"] == [canonical_id]
    assert result["idempotency_replay"] is False
    assert calls == [(body["query"], "amap")]

    serialized = json.dumps(result, ensure_ascii=False)
    assert owner["Authorization"] not in serialized
    assert "receipt_id" not in serialized
    assert "member_id" not in serialized

    restored = client.get(path.removesuffix("/research-places"), headers=owner)
    assert restored.status_code == 200, restored.text
    task_view = restored.json()
    assert task_view["status"] == "FAILED_RECOVERABLE"
    assert task_view["failure_code"] == "MODEL_TIMEOUT"
    assert task_view["usage"] == usage
    assert task_view["candidate_place_ids"] == [canonical_id]
    assert task_view["research_places"][0]["canonical_place_id"] == canonical_id
    with SessionLocal() as session:
        persisted_task = json.loads(session.get(JourneyMission, task_id).intent_json)["goal_task"]
    assert persisted_task["amap_region"]["status"] == "RESOLVED"
    assert _run_counts(task_id) == before_runs == (0, 0)


def test_place_research_idempotency_replay_conflict_and_query_deduplication(monkeypatch, signed_place):
    import app.agent.goal_place_research as research

    client, owner, _outsider, journey_id, *_ = signed_place
    task_id = _task(client, owner, journey_id)
    service_calls = []
    provider_calls = []
    query_results = {}
    canonical_id = "place-issue49-dedupe-test-fixture"
    lead = {
        "id": "amap:ISSUE49DEDUPEFIXTURE",
        "provider": "amap",
        "canonical_place_id": canonical_id,
        "name": "TEST_FIXTURE 同一条查询结果",
        "provider_provenance": "LIVE_PROVIDER",
        "region_status": "MATCHED",
    }

    def discover(session, journey, task, query, source, public_action):
        normalized = " ".join(query.casefold().split())
        service_calls.append((normalized, source))
        signature = f"{source}:{normalized}"
        if signature in task.setdefault("public_queries", []):
            return {**query_results[signature], "status": "QUERY_ALREADY_ATTEMPTED", "places": []}
        provider_calls.append((normalized, source))
        task["public_queries"].append(signature)
        task["research_places"] = [lead]
        task["candidate_place_ids"] = [canonical_id]
        result = {
            "status": "SUCCESS",
            "reason_code": None,
            "source": source,
            "provider_call_id": "provider-call-dedupe-test-fixture",
            "places": [lead],
            "candidate_place_ids": [canonical_id],
        }
        query_results[signature] = result
        return result

    monkeypatch.setattr(research, "discover_goal_places", discover)
    path = f"/api/v1/journeys/{journey_id}/agent/goal-tasks/{task_id}/research-places"
    body = {"query": "TEST_FIXTURE 同一条查询结果", "provider_consent": True}
    key = str(uuid4())
    first = client.post(path, headers={**owner, "Idempotency-Key": key}, json=body)
    assert first.status_code == 200, first.text
    replay = client.post(path, headers={**owner, "Idempotency-Key": key}, json=body)
    assert replay.status_code == 200, replay.text
    assert replay.json()["idempotency_replay"] is True
    assert replay.json()["provider_call_id"] == first.json()["provider_call_id"]
    assert service_calls == [(body["query"].casefold(), "amap")]

    conflicting = client.post(
        path,
        headers={**owner, "Idempotency-Key": key},
        json={**body, "query": "TEST_FIXTURE 改了请求内容"},
    )
    assert conflicting.status_code == 409, conflicting.text
    assert _error_reason(conflicting) == "RESEARCH_KEY_REUSE_CONFLICT", conflicting.text
    assert service_calls == [(body["query"].casefold(), "amap")]

    new_key_same_query = client.post(
        path, headers={**owner, "Idempotency-Key": str(uuid4())}, json=body
    )
    assert new_key_same_query.status_code == 200, new_key_same_query.text
    assert service_calls == [(body["query"].casefold(), "amap")] * 2
    assert provider_calls == [(body["query"].casefold(), "amap")]
    assert new_key_same_query.json()["status"] == "QUERY_ALREADY_ATTEMPTED"
    assert new_key_same_query.json()["candidate_place_ids"] == [canonical_id]
