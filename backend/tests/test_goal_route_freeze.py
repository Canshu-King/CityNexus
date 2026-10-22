"""The hops a saved candidate walks have to become frozen provider evidence, or nothing is frozen.

Written against the door the traveller actually reaches: `prepare-plan` saves real places and the screen
then offers no 选用 button, because selecting reads a snapshot id the draft path never wrote
(backend/app/main.py:18120, and the same absence reported as staleness at backend/app/services.py:584).
These arms pin the narrow bridge: reuse what AMap already measured, freeze only when every walked edge
has a live fact, skip pairs nobody walks, and never let a key replay double-write.

Every arm replaces the live measuring call with one that answers nothing, so no test reaches the
network: an edge that comes out verified here can only have been verified from a receipt the task holds.
"""

import json
from datetime import datetime, timezone
from uuid import uuid4

from test_bootstrap_place_facts import enabled_settings, signed_place  # noqa: F401  (fixtures are imported on purpose)
from app.agent import goal_route_freeze
from app.agent.goal_place_identity import attach_canonical_places
from app.db.models import Journey, JourneyMission, PlanVersion
from app.db.session import SessionLocal
from sqlalchemy import select

TOWER = {"id": "amap:TESTFIX-FREEZE-TOWER", "provider": "amap", "provider_object_id": "TESTFIX-FREEZE-TOWER",
         "name": "TEST_FIXTURE 塔", "category": "landmark", "latitude": 39.91, "longitude": 116.39,
         "coordinate_system": "GCJ02", "provider_provenance": "LIVE_PROVIDER", "region_status": "MATCHED"}
PARK = {"id": "amap:TESTFIX-FREEZE-PARK", "provider": "amap", "provider_object_id": "TESTFIX-FREEZE-PARK",
        "name": "TEST_FIXTURE 湖", "category": "park", "latitude": 39.94, "longitude": 116.39,
        "coordinate_system": "GCJ02", "provider_provenance": "LIVE_PROVIDER", "region_status": "MATCHED"}


def _no_live_answer(monkeypatch):
    """The provider cannot answer, so a verified edge here can only come from a stored receipt."""
    monkeypatch.setattr(goal_route_freeze, "_measure_now", lambda *args, **kwargs: None)


def _draft_with_canonical_places(client, owner, journey_id, task_id):
    """The screen's own path: research -> canonical row -> confirmed schedule -> saved candidate."""
    root = f"/api/v1/journeys/{journey_id}"
    with SessionLocal() as session:
        trip = session.get(Journey, journey_id)
        trip.start_at = "2026-11-02T08:00:00+08:00"
        trip.end_at = "2026-11-03T22:00:00+08:00"
        session.commit()
    draft = client.put(root + f"/agent/goal-tasks/{task_id}/draft", headers=owner, json={"expected_revision": 0,
        "days": [{"date": "2026-11-02", "slots": [
            {"title": "TEST_FIXTURE 上午塔", "time_of_day": "morning", "notes": ""},
            {"title": "TEST_FIXTURE 下午湖", "time_of_day": "afternoon", "notes": ""}]},
            {"date": "2026-11-03", "slots": [{"title": "TEST_FIXTURE 第二天湖", "time_of_day": "morning",
                                             "notes": ""}]}]})
    assert draft.status_code == 200, draft.text
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        mission = session.get(JourneyMission, task_id)
        intent = json.loads(mission.intent_json)
        task = intent["goal_task"]
        leads = [dict(TOWER), dict(PARK)]
        assert len(attach_canonical_places(session, journey, task, leads)) == 2
        ids = {lead["id"]: lead["canonical_place_id"] for lead in leads}
        task["draft_artifact"]["days"][0]["slots"][0]["place_id"] = TOWER["id"]
        task["draft_artifact"]["days"][0]["slots"][1]["place_id"] = PARK["id"]
        task["draft_artifact"]["days"][1]["slots"][0]["place_id"] = PARK["id"]
        task["research_places"] = leads
        task["candidate_place_ids"] = list(ids.values())
        mission.intent_json = json.dumps(intent, ensure_ascii=False)
        session.commit()
    schedule = [{"day_index": 0, "slot_index": 0, "start_time": "09:00", "end_time": "10:00"},
                {"day_index": 0, "slot_index": 1, "start_time": "14:00", "end_time": "15:00"},
                {"day_index": 1, "slot_index": 0, "start_time": "09:00", "end_time": "10:00"}]
    result = client.post(root + f"/agent/goal-tasks/{task_id}/prepare-plan",
                         headers={**owner, "Idempotency-Key": str(uuid4())},
                         json={"expected_revision": 1, "schedule": schedule})
    assert result.status_code == 201, result.text
    return root, result.json()["plan_version_id"], ids


def _store_route(task_id, origin_id, destination_id, *, minutes=27):
    with SessionLocal() as session:
        mission = session.get(JourneyMission, task_id)
        intent = json.loads(mission.intent_json)
        intent["goal_task"].setdefault("research_routes", []).append({
            "id": f"pc-{uuid4()}", "from_place_id": origin_id, "to_place_id": destination_id,
            "from_name": "TEST_FIXTURE 塔", "to_name": "TEST_FIXTURE 湖", "provider": "amap",
            "coordinate_system": "GCJ02", "distance_m": 1840, "duration_seconds": minutes * 60,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "source_url": "https://uri.amap.com/navigation?fixture=1"})
        mission.intent_json = json.dumps(intent, ensure_ascii=False)
        session.commit()


def _freeze(client, headers, root, task_id, plan_id, key=None):
    return client.post(root + f"/agent/goal-tasks/{task_id}/plans/{plan_id}/freeze-routes",
                       headers={**headers, "Idempotency-Key": key or str(uuid4())})


def _task(client, owner, journey_id):
    return client.post(f"/api/v1/journeys/{journey_id}/agent/goal-tasks", headers=owner,
                       json={"goal": "TEST_FIXTURE 塔与湖两日", "model_consent": False,
                             "online_research_consent": False}).json()["task_id"]


def test_every_walked_edge_with_a_provider_receipt_freezes_one_snapshot(signed_place, monkeypatch):
    client, owner, outsider, journey_id, *_ = signed_place
    _no_live_answer(monkeypatch)
    task_id = _task(client, owner, journey_id)
    root, plan_id, ids = _draft_with_canonical_places(client, owner, journey_id, task_id)
    _store_route(task_id, TOWER["id"], PARK["id"])

    answer = _freeze(client, owner, root, task_id, plan_id)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert (body["total"], body["verified"], body["frozen"]) == (1, 1, True), body
    assert [row["status"] for row in body["edges"]] == ["REUSED_PROVIDER_RECEIPT"], body["edges"]
    assert body["edges"][0]["minutes"] == 27 and body["edges"][0]["provider"] == "amap", body["edges"]
    assert body["mobility_snapshot_id"], body
    with SessionLocal() as session:
        plan = session.get(PlanVersion, plan_id)
        assert plan.mobility_snapshot_id == body["mobility_snapshot_id"]
        gaps = json.loads(plan.explanation_json)["unresolved_facts"]
        # A hop the traveller was told to go and measure is no longer a to-do once it is frozen;
        # everything else the provider could not answer stays on the list.
        assert "TRANSFER_ROUTE" not in {row["kind"] for row in gaps}, gaps
        assert {"ADMISSION_PRICE", "PLACE_REQUIRED"} & {row["kind"] for row in gaps}, gaps
        evidence = json.loads(plan.mobility_evidence_json)
        assert evidence["snapshot_id"] == plan.mobility_snapshot_id
        # The keys are the canonical place ids the selection gate itself asks about, and only the
        # same-day hop is in there: nobody walks the overnight pair.
        origins = sorted({fact["origin_key"] for fact in evidence["facts"]})
        assert origins == [ids[TOWER["id"]]], evidence["facts"]


def test_a_hop_nobody_measured_freezes_nothing(signed_place, monkeypatch):
    client, owner, outsider, journey_id, *_ = signed_place
    _no_live_answer(monkeypatch)
    task_id = _task(client, owner, journey_id)
    root, plan_id, _ = _draft_with_canonical_places(client, owner, journey_id, task_id)

    body = _freeze(client, owner, root, task_id, plan_id).json()
    assert (body["total"], body["verified"], body["frozen"]) == (1, 0, False), body
    assert body["mobility_snapshot_id"] is None and body["reason_code"] == "ROUTE_UNAVAILABLE", body
    assert body["edges"][0]["reason_code"] == "PROVIDER_ROUTE_UNAVAILABLE", body["edges"]
    with SessionLocal() as session:
        plan = session.get(PlanVersion, plan_id)
        # Fail closed means the plan stays exactly as unevidenced as it was: no partial snapshot.
        assert plan.mobility_snapshot_id is None and plan.mobility_evidence_json in (None, "")


def test_the_same_key_replays_without_writing_twice(signed_place, monkeypatch):
    from app.db.models import IdempotencyKey
    client, owner, outsider, journey_id, *_ = signed_place
    _no_live_answer(monkeypatch)
    task_id = _task(client, owner, journey_id)
    root, plan_id, _ = _draft_with_canonical_places(client, owner, journey_id, task_id)
    _store_route(task_id, TOWER["id"], PARK["id"])
    key = str(uuid4())

    first = _freeze(client, owner, root, task_id, plan_id, key).json()
    second = _freeze(client, owner, root, task_id, plan_id, key)
    assert second.status_code == 200, second.text
    assert second.json()["idempotency_replay"] is True
    assert {k: v for k, v in second.json().items() if k != "idempotency_replay"} == \
           {k: v for k, v in first.items() if k != "idempotency_replay"}
    with SessionLocal() as session:
        rows = session.scalars(select(IdempotencyKey).where(
            IdempotencyKey.operation == "goal.freeze-routes",
            IdempotencyKey.key.like(f"goal.freeze:{journey_id}:%"))).all()
        assert len(rows) == 1, [row.key for row in rows]


def test_a_stranger_cannot_free_evidence_onto_another_travelers_plan(signed_place, monkeypatch):
    client, owner, outsider, journey_id, *_ = signed_place
    _no_live_answer(monkeypatch)
    task_id = _task(client, owner, journey_id)
    root, plan_id, _ = _draft_with_canonical_places(client, owner, journey_id, task_id)
    refused = _freeze(client, outsider, root, task_id, plan_id)
    assert refused.status_code in {401, 403}, refused.text
    with SessionLocal() as session:
        assert session.get(PlanVersion, plan_id).mobility_snapshot_id is None
