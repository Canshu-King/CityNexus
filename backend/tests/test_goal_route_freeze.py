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
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from test_bootstrap_place_facts import enabled_settings, signed_place  # noqa: F401  (fixtures are imported on purpose)
from app.agent import goal_route_freeze
from app.agent.goal_place_identity import attach_canonical_places
from app.db.models import (Activity, IdempotencyKey, Journey, JourneyIntent, JourneyMission,
                           Place, PlanVersion)
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
    # This fixture models a configured provider returning no route, not a
    # machine without credentials. No network is reachable through the double.
    monkeypatch.setattr(goal_route_freeze, "settings", replace(goal_route_freeze.settings, amap_web_key="TEST_FIXTURE_NOT_A_KEY"))


def _draft_with_canonical_places(client, owner, journey_id, task_id, schedule=None, bind=True):
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
    if schedule is None:
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


def _research_rows(task_id):
    """The rows the drawer under 「高德转场路线」 lists, read back from where they are stored."""
    with SessionLocal() as session:
        return json.loads(session.get(JourneyMission, task_id).intent_json)["goal_task"].get(
            "research_routes") or []


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


def test_a_traveller_who_accepted_the_unknown_price_can_select_and_start(signed_place, monkeypatch):
    """The whole door, end to end: freeze the walked hops, accept the price nobody answered, choose it.

    This is what the walked screens never reached (trial/results/20261022_v3_human_chrome/walk-61-log.txt:34
    reads SELECT_BUTTONS 0): selecting refuses a candidate with no frozen evidence and one whose used
    places have unresolved facts.  The evidence is real here -- the stored AMap receipt -- and the price
    stays what it is, unknown; only the traveller's own recorded decision changes the cost arm, so the
    arm that is not about money has to still be satisfied for the button to work.  That is the point of
    the arm: an accepted price must not smuggle an unverified opening window past the same gate.
    """
    client, owner, outsider, journey_id, *_ = signed_place
    _no_live_answer(monkeypatch)
    task_id = _task(client, owner, journey_id)
    root, plan_id, ids = _draft_with_canonical_places(client, owner, journey_id, task_id)
    _store_route(task_id, TOWER["id"], PARK["id"])
    with SessionLocal() as session:
        # Both places are asked about the same way a provider row would be: opening window verified by
        # the source, price left unknown.  Nothing here invents a price.
        for place_id in ids.values():
            place = session.get(Place, place_id)
            place.opening_hours_json = json.dumps({"status": "VERIFIED_PROVIDER",
                                                   "intervals": [{"open": "09:00", "close": "17:00"}]})
            session.commit()
    assert _freeze(client, owner, root, task_id, plan_id).json()["frozen"] is True

    with SessionLocal() as session:
        gaps = [row for row in json.loads(session.get(PlanVersion, plan_id).explanation_json)["unresolved_facts"]
                if row.get("kind") == "ADMISSION_PRICE"]
        claimed = sorted({str(row["place_id"]) for row in gaps})
    accepted = client.post(root + f"/agent/goal-tasks/{task_id}/plans/{plan_id}/accept-unknown-price",
                           headers={**owner, "Idempotency-Key": str(uuid4())},
                           json={"unknown_place_ids": claimed})
    assert accepted.status_code == 200, accepted.text
    answer = accepted.json()
    assert answer["unknown_cost_included"] is False and answer["authority_state"] == "COST_UNKNOWN_ACCEPTED", answer
    # The same set of places, not the same sequence: the server lists them in the order the candidate
    # walks them, and what the receipt has to match is which places the traveller accepted for.
    assert sorted(answer["unknown_place_ids"]) == claimed and answer["mobility_snapshot_id"], answer
    assert answer["selectable_after"] is True, answer

    selected = client.post(f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select", headers=owner)
    assert selected.status_code == 200, selected.text
    assert selected.json().get("active_plan_version_id") == plan_id or plan_id in json.dumps(selected.json())
    started = client.post(f"/api/v1/journeys/{journey_id}/start", headers=owner)
    assert started.status_code == 200, started.text
    # `/start` answers with the execution projection, not the journey row, so the state the traveller
    # reaches is read the way the screen reads it: the journey itself, and the database behind it.
    readback = client.get(f"/api/v1/journeys/{journey_id}", headers=owner)
    assert readback.status_code == 200, readback.text
    assert readback.json().get("status") == "ACTIVE", {"status": readback.json().get("status"),
                                                       "projection_keys": sorted(started.json())}
    with SessionLocal() as session:
        assert session.get(Journey, journey_id).status == "ACTIVE"
        assert session.get(PlanVersion, plan_id).status == "ACTIVE"


def test_accepting_a_price_that_is_not_unknown_is_refused(signed_place, monkeypatch):
    client, owner, outsider, journey_id, *_ = signed_place
    _no_live_answer(monkeypatch)
    task_id = _task(client, owner, journey_id)
    root, plan_id, ids = _draft_with_canonical_places(client, owner, journey_id, task_id)
    refused = client.post(root + f"/agent/goal-tasks/{task_id}/plans/{plan_id}/accept-unknown-price",
                          headers={**owner, "Idempotency-Key": str(uuid4())},
                          json={"unknown_place_ids": [ids[TOWER["id"]], "not-a-place-on-this-plan"]})
    assert refused.status_code in {409, 422}, refused.text
    with SessionLocal() as session:
        assert json.loads(session.get(PlanVersion, plan_id).explanation_json).get("authority_state") ==             "PROVISIONAL_UNRESOLVED_FACTS"


def test_a_stranger_cannot_free_evidence_onto_another_travelers_plan(signed_place, monkeypatch):
    client, owner, outsider, journey_id, *_ = signed_place
    _no_live_answer(monkeypatch)
    task_id = _task(client, owner, journey_id)
    root, plan_id, _ = _draft_with_canonical_places(client, owner, journey_id, task_id)
    refused = _freeze(client, outsider, root, task_id, plan_id)
    assert refused.status_code in {401, 403}, refused.text
    with SessionLocal() as session:
        assert session.get(PlanVersion, plan_id).mobility_snapshot_id is None


GATE = {"id": "amap:TESTFIX-FREEZE-GATE", "provider": "amap", "provider_object_id": "TESTFIX-FREEZE-GATE",
        "name": "TEST_FIXTURE 城门", "category": "landmark", "latitude": 39.95, "longitude": 116.40,
        "coordinate_system": "GCJ02", "provider_provenance": "LIVE_PROVIDER", "region_status": "MATCHED"}
RESTO = {"id": "amap:TESTFIX-FREEZE-RESTO", "provider": "amap", "provider_object_id": "TESTFIX-FREEZE-RESTO",
         "name": "TEST_FIXTURE 小馆", "category": "restaurant", "latitude": 39.925, "longitude": 116.395,
         "coordinate_system": "GCJ02", "provider_provenance": "LIVE_PROVIDER", "region_status": "MATCHED"}


def test_a_two_day_plan_with_a_free_evening_reaches_active(signed_place, monkeypatch):
    """The walked story, in one arm: two days, a band with no venue, and an overnight link.

    Measured on the candidate the screen actually saved (trial/results/20261022_v3_human_chrome/
    selection-gate-replay-1.txt): the gate read the plan as one chain and answered
    ``LOCATION_MISSING`` for each of the three venue-less bands it had been handed as activities, plus
    ``MOBILITY_CONTEXT_MISSING`` for the pairs they sat in -- a refusal no button could act on.  A band
    the traveller confirmed but nobody placed is a note on the day, not a stop to route to.  And the
    first morning stop is checked against the previous day's last one, so an overnight link has to be
    measured like any other hop, and named as one.
    """
    client, owner, outsider, journey_id, *_ = signed_place
    _no_live_answer(monkeypatch)
    task_id = _task(client, owner, journey_id)
    root = f"/api/v1/journeys/{journey_id}"
    with SessionLocal() as session:
        trip = session.get(Journey, journey_id)
        trip.start_at = "2026-11-02T08:00:00+08:00"
        trip.end_at = "2026-11-03T22:00:00+08:00"
        session.commit()
    draft = client.put(root + f"/agent/goal-tasks/{task_id}/draft", headers=owner, json={"expected_revision": 0,
        "days": [{"date": "2026-11-02", "slots": [
            {"title": "TEST_FIXTURE 上午塔", "time_of_day": "morning", "notes": ""},
            {"title": "TEST_FIXTURE 街边午饭", "time_of_day": "flexible", "notes": "还没有定地方"},
            {"title": "TEST_FIXTURE 下午湖", "time_of_day": "afternoon", "notes": ""}]},
            {"date": "2026-11-03", "slots": [{"title": "TEST_FIXTURE 第二天城门", "time_of_day": "morning",
                                             "notes": ""}]}]})
    assert draft.status_code == 200, draft.text
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        mission = session.get(JourneyMission, task_id)
        intent = json.loads(mission.intent_json)
        task = intent["goal_task"]
        leads = [dict(TOWER), dict(PARK), dict(GATE)]
        assert len(attach_canonical_places(session, journey, task, leads)) == 3
        ids = {lead["id"]: lead["canonical_place_id"] for lead in leads}
        days = task["draft_artifact"]["days"]
        days[0]["slots"][0]["place_id"] = TOWER["id"]
        days[0]["slots"][2]["place_id"] = PARK["id"]
        days[1]["slots"][0]["place_id"] = GATE["id"]
        # The lunch band carries no place at all -- that is the shape the traveller's screen leaves it
        # in when the Agent has not found a venue yet (``place_id`` stays None,
        # backend/app/agent/goal_artifacts.py:219).
        days[0]["slots"][1].pop("place_id", None)
        task["research_places"] = leads
        task["candidate_place_ids"] = list(ids.values())
        mission.intent_json = json.dumps(intent, ensure_ascii=False)
        session.commit()
    result = client.post(root + f"/agent/goal-tasks/{task_id}/prepare-plan",
                         headers={**owner, "Idempotency-Key": str(uuid4())},
                         json={"expected_revision": 1, "schedule": [
                             {"day_index": 0, "slot_index": 0, "start_time": "09:00", "end_time": "10:00"},
                             {"day_index": 0, "slot_index": 1, "start_time": "12:00", "end_time": "13:00"},
                             {"day_index": 0, "slot_index": 2, "start_time": "14:00", "end_time": "15:00"},
                             {"day_index": 1, "slot_index": 0, "start_time": "09:00", "end_time": "10:00"}]})
    assert result.status_code == 201, result.text
    plan_id = result.json()["plan_version_id"]
    assert result.json()["slots_count"] == 4 and result.json()["unrouted_count"] == 1, result.json()

    with SessionLocal() as session:
        rows = list(session.scalars(select(Activity).where(Activity.plan_version_id == plan_id)
                                    .order_by(Activity.sequence_no)))
        # Every stretch the traveller confirmed is still on the plan.  The lunch band is a row too -- it
        # is not quietly deleted to make a gate pass -- but it declares itself unroutable, and that
        # declaration is what the feasibility chain reads instead of demanding a location for it.
        assert [row.sequence_no for row in rows] == [1, 2, 3, 4]
        by_title = {row.title: row for row in rows}
        band = by_title["TEST_FIXTURE 街边午饭"]
        assert band.place_id is None and band.activity_type == "FREE_TIME"
        assert json.loads(band.metadata_json)["routing"] == "NOT_ROUTED"
        assert all(row.place_id for row in rows if row.title != band.title)
        explanation = json.loads(session.get(PlanVersion, plan_id).explanation_json)
        # The hop asked about after 下午湖 is the next morning's 城门: the chain runs across the night.
        assert [row.get("kind") for row in explanation["unresolved_facts"]].count("TRANSFER_ROUTE") == 2
        assert [gap["kind"] for gap in explanation["unresolved_facts"] if gap["kind"] == "PLACE_REQUIRED"] ==             ["PLACE_REQUIRED"]

    _store_route(task_id, TOWER["id"], PARK["id"])
    _store_route(task_id, PARK["id"], GATE["id"], minutes=31)
    frozen = _freeze(client, owner, root, task_id, plan_id).json()
    assert frozen["verified"] == 2 and frozen["total"] == 2 and frozen["frozen"] is True, frozen
    assert frozen["overnight"] == 1, frozen
    assert [row["spans_night"] for row in frozen["edges"]] == [False, True], frozen["edges"]

    with SessionLocal() as session:
        for place_id in ids.values():
            place = session.get(Place, place_id)
            place.opening_hours_json = json.dumps({"status": "VERIFIED_PROVIDER",
                                                   "intervals": [{"open": "09:00", "close": "17:00"}]})
            session.commit()
        unknown = sorted({str(row["place_id"]) for row in
                          json.loads(session.get(PlanVersion, plan_id).explanation_json)["unresolved_facts"]
                          if row.get("kind") == "ADMISSION_PRICE"})
    accepted = client.post(root + f"/agent/goal-tasks/{task_id}/plans/{plan_id}/accept-unknown-price",
                           headers={**owner, "Idempotency-Key": str(uuid4())},
                           json={"unknown_place_ids": unknown})
    assert accepted.status_code == 200, accepted.text
    answer = accepted.json()
    # Accepting the price does not place the lunch band: the one thing left is a venue, and the gate
    # says so by name instead of by a routing code nobody can act on.
    assert answer["selectable_after"] is False and answer["blocker_after"] == "UNRESOLVED_ACTIVITY_FACTS", answer
    refused = client.post(f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select", headers=owner)
    assert refused.status_code == 409, refused.text
    details = refused.json()["error"]["details"] or {}
    remaining = [row["kind"] for row in details.get("unresolved_facts") or []]
    # Accepting the price does not pretend the price became known -- those rows stay -- but it is no
    # longer what stands between this plan and departure.  The band with no venue is.
    assert "PLACE_REQUIRED" in remaining and "TRANSFER_ROUTE" not in remaining, refused.text

    # 「让 Agent 找这一处」 -- the Agent comes back with a real place for the band, the traveller
    # confirms the schedule again, and the same three doors run a second time.  This is the whole
    # product loop the walked screens never completed.
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        mission = session.get(JourneyMission, task_id)
        intent = json.loads(mission.intent_json)
        task = intent["goal_task"]
        lead = dict(RESTO)
        assert attach_canonical_places(session, journey, task, [lead])
        ids[lead["id"]] = lead["canonical_place_id"]
        task["research_places"].append(lead)
        task["candidate_place_ids"] = list(ids.values())
        mission.intent_json = json.dumps(intent, ensure_ascii=False)
        session.commit()
    placed = client.put(root + f"/agent/goal-tasks/{task_id}/draft", headers=owner, json={"expected_revision": 1,
        "days": [{"date": "2026-11-02", "slots": [
            {"title": "TEST_FIXTURE 上午塔", "time_of_day": "morning", "notes": "", "place_id": TOWER["id"]},
            {"title": "TEST_FIXTURE 街边午饭", "time_of_day": "flexible", "notes": "", "place_id": RESTO["id"]},
            {"title": "TEST_FIXTURE 下午湖", "time_of_day": "afternoon", "notes": "", "place_id": PARK["id"]}]},
            {"date": "2026-11-03", "slots": [{"title": "TEST_FIXTURE 第二天城门", "time_of_day": "morning",
                                             "notes": "", "place_id": GATE["id"]}]}]})
    assert placed.status_code == 200, placed.text
    with SessionLocal() as session:
        place = session.get(Place, ids[RESTO["id"]])
        place.opening_hours_json = json.dumps({"status": "VERIFIED_PROVIDER",
                                               "intervals": [{"open": "11:00", "close": "21:00"}]})
        session.commit()
    second = client.post(root + f"/agent/goal-tasks/{task_id}/prepare-plan",
                         headers={**owner, "Idempotency-Key": str(uuid4())},
                         json={"expected_revision": 2, "schedule": [
                             {"day_index": 0, "slot_index": 0, "start_time": "09:00", "end_time": "10:00"},
                             {"day_index": 0, "slot_index": 1, "start_time": "12:00", "end_time": "13:00"},
                             {"day_index": 0, "slot_index": 2, "start_time": "14:00", "end_time": "15:00"},
                             {"day_index": 1, "slot_index": 0, "start_time": "09:00", "end_time": "10:00"}]})
    assert second.status_code == 201, second.text
    plan_two = second.json()["plan_version_id"]
    assert second.json()["slots_count"] == 4 and second.json()["unrouted_count"] == 0, second.json()

    # The band became a stop, so it split one hop into two: the chain the gate reads grew with it.
    _store_route(task_id, TOWER["id"], RESTO["id"], minutes=12)
    _store_route(task_id, RESTO["id"], PARK["id"], minutes=9)
    frozen_two = _freeze(client, owner, root, task_id, plan_two).json()
    assert frozen_two["verified"] == 3 and frozen_two["total"] == 3 and frozen_two["overnight"] == 1, frozen_two

    with SessionLocal() as session:
        unknown_two = sorted({str(row["place_id"]) for row in
                              json.loads(session.get(PlanVersion, plan_two).explanation_json)["unresolved_facts"]
                              if row.get("kind") == "ADMISSION_PRICE"})
        assert set(unknown_two) == set(ids.values()), (unknown_two, ids)
    accepted_two = client.post(root + f"/agent/goal-tasks/{task_id}/plans/{plan_two}/accept-unknown-price",
                               headers={**owner, "Idempotency-Key": str(uuid4())},
                               json={"unknown_place_ids": unknown_two})
    assert accepted_two.status_code == 200, accepted_two.text
    assert accepted_two.json()["selectable_after"] is True, accepted_two.json()

    assert client.post(f"/api/v1/journeys/{journey_id}/plans/{plan_two}/select",
                       headers=owner).status_code == 200
    started = client.post(f"/api/v1/journeys/{journey_id}/start", headers=owner)
    assert started.status_code == 200, started.text
    readback = client.get(f"/api/v1/journeys/{journey_id}", headers=owner)
    assert readback.json().get("status") == "ACTIVE", {"status": readback.json().get("status"),
                                                       "start_keys": sorted(started.json())}
    with SessionLocal() as session:
        # The candidate that carried the band keeps it after the traveller departs the one that does
        # not: nothing was quietly rewritten to make the gate pass.
        first = list(session.scalars(select(Activity).where(Activity.plan_version_id == plan_id)))
        assert len(first) == 4 and len([row for row in first if row.place_id is None]) == 1
        second_rows = list(session.scalars(select(Activity).where(Activity.plan_version_id == plan_two)))
        assert len(second_rows) == 4 and all(row.place_id for row in second_rows)
        assert session.get(PlanVersion, plan_two).status == "ACTIVE"
        assert session.get(Journey, journey_id).status == "ACTIVE"


class _TransitAnswersWhenWalkingRefuses:
    """The walking door says it has no route for this pair; the transit door answers.

    Only the provider is faked here.  `_measure_now`, `_transit_leg` and `_arrival_moment` all run for
    real, because the crash this arm pins lived in exactly that code: `Activity.start_at` is a text
    column, the freeze door hands that text straight in, and the first version of the transit arm
    called `strftime` on it -- the traveller's own button answered 500 twice over
    (trial/results/20261022_v3_human_chrome/walk-78-log.txt:41 and, on a backend process that had not
    been restarted onto the fix, walk-108-log.txt:40).  The rest of this file stubs `_measure_now`
    itself (see its module docstring), so no arm here ever reached that line.
    """

    def __init__(self):
        self.transit_calls: list[dict] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def walking(self, start, end):
        return {"status": "error", "reason_code": "AMAP_NO_ROUTE", "http_status": 200, "elapsed_ms": 1}

    def transit(self, start, end, city_code, departure_date=None, departure_time=None):
        self.transit_calls.append({"city_code": city_code, "departure_date": departure_date,
                                   "departure_time": departure_time})
        return {"status": "ok", "http_status": 200, "elapsed_ms": 2, "route": {
            "provider_key": "amap-web-service", "mode": "TRANSIT", "distance_m": 6120,
            "duration_seconds": 2460, "duration_min": 41, "lines": ["地铁8号线"],
            "walking_distance_m": 640, "fare_minor": 300, "nightflag": 0,
            "coordinate_system": "GCJ02", "city_code": city_code}}


def _task_with_a_city(client, owner, journey_id, task_id, citycode="TESTFIX010"):
    """The city code the research leg would have stored, so the transit door has something to ask with."""
    with SessionLocal() as session:
        mission = session.get(JourneyMission, task_id)
        intent = json.loads(mission.intent_json)
        intent["goal_task"]["amap_region"] = {"citycode": citycode, "query": "TEST_FIXTURE", "status": "RESOLVED"}
        mission.intent_json = json.dumps(intent, ensure_ascii=False)
        session.commit()


def _same_day_hop_without_a_stored_receipt(signed_place, monkeypatch, client, owner, journey_id, task_id):
    monkeypatch.setattr(goal_route_freeze, "settings", SimpleNamespace(amap_web_key="TESTFIX"))
    fake = _TransitAnswersWhenWalkingRefuses()
    monkeypatch.setattr(goal_route_freeze, "_client", lambda: fake)
    _task_with_a_city(client, owner, journey_id, task_id)
    root, plan_id, _ids = _draft_with_canonical_places(client, owner, journey_id, task_id)
    return fake, root, plan_id


def test_the_hour_the_plan_stores_as_text_is_asked_of_the_transit_door(signed_place, monkeypatch):
    client, owner, _outsider, journey_id, *_ = signed_place
    task_id = _task(client, owner, journey_id)
    fake, root, plan_id = _same_day_hop_without_a_stored_receipt(
        signed_place, monkeypatch, client, owner, journey_id, task_id)

    with SessionLocal() as session:
        stored = session.scalars(select(Activity).where(Activity.plan_version_id == plan_id)).all()
        hour_row = [row for row in stored if str(row.title).endswith("下午湖")][0]
        assert isinstance(hour_row.start_at, str), type(hour_row.start_at)
        moment = datetime.fromisoformat(hour_row.start_at)

    answer = _freeze(client, owner, root, task_id, plan_id)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert [row["status"] for row in body["edges"]] == [goal_route_freeze.MEASURED], body["edges"]
    assert body["edges"][0]["mode"] == "TRANSIT", body["edges"]
    assert body["edges"][0]["lines"] == ["地铁8号线"], body["edges"]
    assert body["frozen"] is True, body
    assert fake.transit_calls == [{"city_code": "TESTFIX010",
                                   "departure_date": moment.strftime("%Y-%m-%d"),
                                   "departure_time": moment.strftime("%H:%M")}], fake.transit_calls


def test_an_hour_nobody_wrote_down_is_asked_as_no_hour_at_all(signed_place, monkeypatch):
    """A slot with no hour written down is asked of the provider with no hour, not with an invented one."""
    client, owner, _outsider, journey_id, *_ = signed_place
    task_id = _task(client, owner, journey_id)
    fake, root, plan_id = _same_day_hop_without_a_stored_receipt(
        signed_place, monkeypatch, client, owner, journey_id, task_id)

    with SessionLocal() as session:
        for row in session.scalars(select(Activity).where(Activity.plan_version_id == plan_id)):
            if str(row.title).endswith("下午湖"):
                row.start_at = ""
        session.commit()

    answer = _freeze(client, owner, root, task_id, plan_id)
    assert answer.status_code == 200, answer.text
    assert fake.transit_calls == [{"city_code": "TESTFIX010", "departure_date": None,
                                   "departure_time": None}], fake.transit_calls
    assert answer.json()["edges"][0]["mode"] == "TRANSIT", answer.json()["edges"]


def _freeze_reason(client, owner, root, task_id, plan_id):
    answer = _freeze(client, owner, root, task_id, plan_id)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert (body["total"], body["frozen"]) == (0, False), body
    return body


def _set_places(plan_id, values):
    """Arrange the row state the phone had reached; the door's reading, not the drafting, is the subject.

    On the walk the six saved arrangements carried no canonical place at all
    (trial/human_walk/candidate_place_binding_probe_r1.py over
    trial/results/20261022_v3_human_chrome/replan-probe-2-log.txt), which the test fixture cannot reach
    through the drafting door -- there the title is resolved to a ``real-place-`` row.  So the state is
    written here, and what is asserted is only which of the two empty answers the door gives.
    """
    with SessionLocal() as session:
        rows = list(session.scalars(select(Activity).where(Activity.plan_version_id == plan_id)
                                    .order_by(Activity.sequence_no)))
        assert len(rows) >= len(values)
        for row, value in zip(rows, values):
            row.place_id = value
        session.commit()


def test_a_candidate_whose_stops_are_not_places_says_that_instead_of_denying_hops(signed_place, monkeypatch):
    client, owner, _outsider, journey_id, *_ = signed_place
    _no_live_answer(monkeypatch)
    task_id = _task(client, owner, journey_id)
    root, plan_id, _ids = _draft_with_canonical_places(client, owner, journey_id, task_id)
    _set_places(plan_id, [None, None, None])

    body = _freeze_reason(client, owner, root, task_id, plan_id)
    assert body["reason_code"] == "NO_PLACED_STOPS", body
    assert body["verified"] == 0, body

    # The other empty answer keeps its own word: two consecutive stops at one venue are not a routing
    # question at all, and the door already says so elsewhere (app/agent/goal_route_freeze.py:used_edges).
    same_place = _ids
    second_task = _task(client, owner, journey_id)
    _root2, plan2, ids2 = _draft_with_canonical_places(client, owner, journey_id, second_task)
    assert len(set(same_place.values())) == 2 and len(set(ids2.values())) == 2
    _set_places(plan2, [ids2[TOWER["id"]], ids2[TOWER["id"]], ids2[TOWER["id"]]])
    assert _freeze_reason(client, owner, root, second_task, plan2)["reason_code"] == "NO_ROUTED_EDGES"


class _LongWalkAndShortTransit:
    """The walking door answers -- with a hop further than the traveller said they would walk.

    Only the provider is faked.  `_measure_now`, `_over_cap_walk`, `_replace_long_walk` and `_transit_leg`
    run for real, so what is under test is the substitution itself, not a stub's return value.
    """

    def __init__(self, walk_m=16200, transit_answers=True):
        self.walk_m = walk_m
        self.transit_answers = transit_answers
        self.walking_calls = 0
        self.transit_calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def walking(self, start, end):
        self.walking_calls += 1
        return {"status": "ok", "http_status": 200, "elapsed_ms": 2, "route": {
            "provider_key": "amap-web-service", "mode": "WALK", "distance_m": self.walk_m,
            "duration_seconds": 12960, "duration_min": 216, "lines": [], "coordinate_system": "GCJ02"}}

    def transit(self, start, end, city_code, departure_date=None, departure_time=None):
        self.transit_calls.append({"city_code": city_code, "departure_date": departure_date,
                                   "departure_time": departure_time})
        if not self.transit_answers:
            return {"status": "error", "reason_code": "AMAP_NO_TRANSIT_ROUTE", "http_status": 200, "elapsed_ms": 1}
        return {"status": "ok", "http_status": 200, "elapsed_ms": 2, "route": {
            "provider_key": "amap-web-service", "mode": "TRANSIT", "distance_m": 6120,
            "duration_seconds": 2460, "duration_min": 41, "lines": ["地铁8号线"],
            "walking_distance_m": 640, "fare_minor": 300, "nightflag": 0,
            "coordinate_system": "GCJ02", "city_code": city_code}}


def _words_of_the_traveller(task_id, goal, *, where="intent"):
    """Put the traveller's own sentence where a real traveller's sentence actually lands.

    `where="intent"` is the first-screen goal: `journey_intents.source_text`, which is the only column of
    the walked database that held the cap sentence (its `capabilities_json` was still `[]`).
    `where="conversation"` is a message typed into the dock on the same task.
    """
    with SessionLocal() as session:
        mission = session.get(JourneyMission, task_id)
        if where == "intent":
            row = session.scalars(select(JourneyIntent).where(
                JourneyIntent.journey_id == mission.journey_id)).first()
            if row is None:
                journey = session.get(Journey, mission.journey_id)
                session.add(JourneyIntent(id=str(uuid4()), journey_id=journey.id,
                                          created_by_traveler_id=journey.traveler_id,
                                          source_text=goal, intent_kind="TRIP_GOAL",
                                          semantic_fingerprint=str(uuid4()),
                                          created_at=datetime.now(timezone.utc).isoformat(),
                                          updated_at=datetime.now(timezone.utc).isoformat()))
            else:
                row.source_text = goal
        else:
            intent = json.loads(mission.intent_json)
            intent["goal_task"].setdefault("conversation", []).append({"role": "user", "text": goal})
            mission.intent_json = json.dumps(intent, ensure_ascii=False)
            session.add(mission)
        session.commit()


def _cap_arm(signed_place, monkeypatch, client, owner, journey_id, task_id, goal, *,
             where="intent", **fake_kwargs):
    monkeypatch.setattr(goal_route_freeze, "settings", SimpleNamespace(amap_web_key="TESTFIX"))
    fake = _LongWalkAndShortTransit(**fake_kwargs)
    monkeypatch.setattr(goal_route_freeze, "_client", lambda: fake)
    _task_with_a_city(client, owner, journey_id, task_id)
    root, plan_id, _ids = _draft_with_canonical_places(client, owner, journey_id, task_id)
    _words_of_the_traveller(task_id, goal, where=where)
    return fake, root, plan_id


def test_the_travellers_walking_limit_moves_a_long_hop_to_the_transit_door(signed_place, monkeypatch):
    """「每段步行不超过1公里」 is a cap the product already knows how to read; the freeze door just never asked.

    Measured on the phone: the drawer carried 16.2 公里 and 17.6 公里 hops as 步行 with the traveller having
    asked to walk less (trial/results/20261022_v3_human_chrome/walk-111-log.txt, STEP_12D_PANE_HEADLINE),
    and the phrasings that do carry a number are in
    trial/results/20261022_v3_human_chrome/caps_walk_extract-1.txt.
    """
    client, owner, _outsider, journey_id, *_ = signed_place
    task_id = _task(client, owner, journey_id)
    fake, root, plan_id = _cap_arm(signed_place, monkeypatch, client, owner, journey_id, task_id,
                                  "TEST_FIXTURE 塔与湖两日，每段步行不超过1公里")

    body = _freeze(client, owner, root, task_id, plan_id).json()
    edge = body["edges"][0]
    assert fake.walking_calls == 1 and len(fake.transit_calls) == 1, (fake.walking_calls, fake.transit_calls)
    assert (edge["mode"], edge["status"]) == ("TRANSIT", goal_route_freeze.MEASURED), edge
    assert (edge["replaced_walk_m"], edge["walking_cap_m"], edge["over_cap_m"]) == (16200, 1000, None), edge
    assert edge["minutes"] == 41 and edge["lines"] == ["地铁8号线"], edge
    assert (body["frozen"], body["transit"], body["replaced_long_walks"], body["over_cap_walks"]) == (
        True, 1, 1, 0), body
    with SessionLocal() as session:
        evidence = json.loads(session.get(PlanVersion, plan_id).mobility_evidence_json)
        # What got frozen is the transport answer, not the walk it replaced: 41 minutes on the bus,
        # not the 216 the walking door measured, and the fact itself says it was ridden with 640 m of
        # footsteps in it.  Those last fields are what let the traveller's own limit be judged at the
        # feasibility door instead of answered with NEEDS_LIVE_EVIDENCE
        # (app/replanning/feasibility.py:497 reads exactly these three).
        assert [fact["minutes"] for fact in evidence["facts"]] == [41], evidence["facts"]
        assert [(fact["mode"], fact["distance_m"], fact["walking_distance_m"])
                for fact in evidence["facts"]] == [("TRANSIT", 6120, 640)], evidence["facts"]
    # The drawer lists what the walking door measured, so the replacement has to be written on that row
    # too -- otherwise the same hop reads 步行 16.2 公里 under 「高德转场路线」 while the band above it says
    # 已换成公共交通核实 (measured on the real screen: walk-113-log.txt:68 against the band at :57).
    hop = [row for row in _research_rows(task_id) if row.get("from_name") == "TEST_FIXTURE 塔"]
    assert len(hop) == 1, _research_rows(task_id)
    assert (hop[0]["mode"], hop[0]["frozen_mode"], hop[0]["walking_cap_m"]) == ("WALK", "TRANSIT", 1000), hop[0]
    assert (hop[0]["frozen_minutes"], hop[0]["frozen_lines"]) == (41, ["地铁8号线"]), hop[0]


def test_a_preference_with_no_number_invents_no_cap_and_sends_no_second_call(signed_place, monkeypatch):
    """「少走路」 has no metres in it, so the hop stays the walk the provider measured -- no extra spend."""
    client, owner, _outsider, journey_id, *_ = signed_place
    task_id = _task(client, owner, journey_id)
    fake, root, plan_id = _cap_arm(signed_place, monkeypatch, client, owner, journey_id, task_id,
                                  "TEST_FIXTURE 塔与湖两日，少走路", where="conversation")

    body = _freeze(client, owner, root, task_id, plan_id).json()
    edge = body["edges"][0]
    assert fake.walking_calls == 1 and fake.transit_calls == [], (fake.walking_calls, fake.transit_calls)
    assert edge["mode"] == "WALK" and edge["replaced_walk_m"] is None, edge
    assert (body["replaced_long_walks"], body["walking_cap_m"]) == (0, None), body
    with SessionLocal() as session:
        stored = json.loads(session.get(PlanVersion, plan_id).mobility_evidence_json)
    # A walk stays a walk in the frozen fact.  The provider answers a walk with one distance and no
    # separate footstep count, and the reader's rule is that a WALK leg's own distance *is* the walking
    # distance (app/replanning/feasibility.py:499) -- so what the fact has to carry is the mode and that
    # distance, which is exactly what the traveller's limit then judges.
    assert [(fact["mode"], fact["walking_distance_m"], fact["distance_m"])
            for fact in stored["facts"]] == [("WALK", None, 16200)], stored["facts"]
    # And the drawer's row is left exactly as the provider answered it: no limit, no frozen marker.
    hop = [row for row in _research_rows(task_id) if row.get("from_name") == "TEST_FIXTURE 塔"]
    assert "walking_cap_m" not in hop[0] and "frozen_mode" not in hop[0], hop[0]


def test_when_the_transport_door_has_no_answer_the_walk_stays_and_says_it_was_too_far(
        signed_place, monkeypatch):
    """Evidence the provider gave is not thrown away to satisfy a limit; the card has to say it was exceeded."""
    client, owner, _outsider, journey_id, *_ = signed_place
    task_id = _task(client, owner, journey_id)
    fake, root, plan_id = _cap_arm(signed_place, monkeypatch, client, owner, journey_id, task_id,
                                   "TEST_FIXTURE 塔与湖两日，每段步行不超过1公里", transit_answers=False)

    body = _freeze(client, owner, root, task_id, plan_id).json()
    edge = body["edges"][0]
    assert len(fake.transit_calls) == 1 and edge["mode"] == "WALK", (fake.transit_calls, edge)
    assert (edge["distance_m"], edge["over_cap_m"], edge["replaced_walk_m"]) == (16200, 16200, None), edge
    assert (body["frozen"], body["replaced_long_walks"], body["over_cap_walks"]) == (True, 0, 1), body
    # The walk is still on the card, and the card says it went over the limit the traveller wrote.
    hop = [row for row in _research_rows(task_id) if row.get("from_name") == "TEST_FIXTURE 塔"]
    assert (hop[0]["mode"], hop[0]["frozen_mode"], hop[0]["walking_cap_m"]) == ("WALK", "WALK", 1000), hop[0]
