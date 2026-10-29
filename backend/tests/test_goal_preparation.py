"""Signed draft-to-candidate integration; isolated SQLite TEST_FIXTURE only."""
import json
from uuid import uuid4
import pytest
from sqlalchemy import select
from test_bootstrap_place_facts import enabled_settings, signed_place
from app.db.models import Activity, Journey, JourneyMission, PlanVersion, Place, ProviderCall
from app.db.session import SessionLocal

@pytest.fixture
def prepared_scope(signed_place):
    client, owner, outsider, jid, *_ = signed_place
    root = f"/api/v1/journeys/{jid}"
    created = client.post(root + "/agent/goal-tasks", headers=owner, json={"goal":"TEST_FIXTURE 下午慢逛", "model_consent": False,"online_research_consent":False}).json()
    tid = created["task_id"]
    draft = client.put(root + f"/agent/goal-tasks/{tid}/draft", headers=owner, json={"expected_revision":0,"days":[{"date":"2026-11-01","slots":[{"title":"TEST_FIXTURE 自选午后", "time_of_day":"afternoon", "notes":"先保留这项"}]}]})
    assert draft.status_code == 200, draft.text
    path = root + f"/agent/goal-tasks/{tid}/prepare-plan"
    body = {"expected_revision":1,"schedule":[{"day_index":0,"slot_index":0,"start_time":"14:00","end_time":"15:00"}]}
    return client, {**owner,"Idempotency-Key":str(uuid4())}, outsider, jid, tid, path, body


def test_preserves_task_dates_and_slots_without_promoting_unknowns(prepared_scope):
    client, headers, _, jid, tid, path, body = prepared_scope
    with SessionLocal() as s:
        before_places = len(s.scalars(select(Place)).all()); before_calls = len(s.scalars(select(ProviderCall)).all())
    result = client.post(path, headers=headers, json=body)
    assert result.status_code == 201, result.text
    data = result.json()
    assert data["draft_revision"] == 1 and data["selected"] is False and data["activated"] is False
    # One ask per row.  A band with no venue has no opening window and no ticket to check, so the
    # 营业时间/门票价格 lines it used to carry asked the traveller about a place that does not exist yet;
    # they come back as their own rows once a place is bound (goal_preparation.py, the `missing` block).
    assert {gap["kind"] for gap in data["gaps"]} == {"PLACE_REQUIRED"}
    replay = client.post(path,headers=headers,json=body)
    assert replay.json()["plan_version_id"] == data["plan_version_id"] and replay.json()["idempotency_replay"] is True
    plans = client.get(f"/api/v1/journeys/{jid}/plans",headers=headers).json()
    plan = next(p for p in plans if p["id"] == data["plan_version_id"])
    assert plan["status"] == "CANDIDATE" and plan["selectable"] is False
    assert plan["total_cost_status"] == "PARTIAL_UNKNOWN"
    assert plan["activities"][0]["start_at"] == "2026-11-01T14:00:00+08:00"
    assert plan["activities"][0]["title"] == "TEST_FIXTURE 自选午后"
    assert plan["activities"][0]["cost_status"] == "UNKNOWN"
    with SessionLocal() as s:
        journey=s.get(Journey,jid)
        assert journey.status == "DRAFT" and journey.active_plan_version_id is None
        assert len(s.scalars(select(Place)).all()) == before_places
        assert len(s.scalars(select(ProviderCall)).all()) == before_calls
        assert s.get(JourneyMission,tid) is not None
        assert len(s.scalars(select(PlanVersion).where(PlanVersion.journey_id==jid)).all()) == 1


def test_signed_scope_and_revision(prepared_scope):
    client, headers, outsider, jid, tid, path, body = prepared_scope
    assert client.post(path,headers={"Idempotency-Key":"fixture"},json=body).status_code == 401
    assert client.post(path,headers={**outsider,"Idempotency-Key":"fixture"},json=body).status_code == 403
    assert client.post(path,headers=headers,json={**body,"expected_revision":0}).status_code == 409
    assert client.post(path.replace(tid,str(uuid4())),headers=headers,json=body).status_code == 404
    with SessionLocal() as s:
        assert s.scalar(select(PlanVersion).where(PlanVersion.journey_id==jid)) is None


@pytest.mark.parametrize("schedule", [[],[{"day_index":0,"slot_index":0,"start_time":"15:00","end_time":"14:00"}], [{"day_index":0,"slot_index":0,"start_time":"08:00","end_time":"09:00"}], [{"day_index":0,"slot_index":3,"start_time":"14:00","end_time":"15:00"}], [{"day_index":0,"slot_index":0,"start_time":"14:00","end_time":"15:00"}]*2])
def test_rejects_invalid_schedule_without_partial_plan(prepared_scope,schedule):
    client, headers, _, jid, _, path, body = prepared_scope
    result=client.post(path,headers=headers,json={**body,"schedule":schedule})
    assert result.status_code == 422, result.text
    with SessionLocal() as s:
        assert s.scalar(select(PlanVersion).where(PlanVersion.journey_id==jid)) is None


def test_same_key_conflict_and_body_cannot_override_place(prepared_scope):
    client, headers, _, _, _, path, body = prepared_scope
    assert client.post(path,headers=headers,json={**body,"status":"ACTIVE"}).status_code==422
    assert client.post(path,headers=headers,json=body).status_code==201
    body["schedule"][0]["end_time"]="16:00"
    assert client.post(path,headers=headers,json=body).status_code==409


def test_source_lead_keeps_identity_without_creating_place(prepared_scope):
    client, headers, _, jid, tid, path, body = prepared_scope
    with SessionLocal() as s:
        m=s.get(JourneyMission,tid); intent=json.loads(m.intent_json); task=intent["goal_task"]
        task["draft_artifact"]["days"][0]["slots"][0]["place_id"]="amap:fixture-tower"
        task["research_places"]=[{"id":"amap:fixture-tower","name":"TEST_FIXTURE tower","provider":"amap","provider_provenance":"LIVE_PROVIDER", "region_status":"MATCHED", "source_url":"https://uri.amap.com/marker?fixture=1"}]
        m.intent_json=json.dumps(intent); s.commit()
    result=client.post(path,headers=headers,json=body)
    assert result.status_code==201,result.text
    assert "SOURCE_IDENTITY" in {gap["kind"] for gap in result.json()["gaps"]}
    with SessionLocal() as s:
        a=s.scalar(select(Activity).where(Activity.plan_version_id==result.json()["plan_version_id"]))
        assert a.place_id is None
        assert json.loads(a.metadata_json)["source_candidate_id"]=="amap:fixture-tower"
        assert json.loads(a.metadata_json)["source_urls"]==["https://uri.amap.com/marker?fixture=1"]


def test_two_days_keep_slot_order_and_restore_schedule(prepared_scope):
    client, headers, _, jid, tid, path, body = prepared_scope
    with SessionLocal() as s:
        s.get(Journey,jid).end_at="2026-11-02T18:00:00+08:00"
        s.commit()
    draft_path=path.removesuffix("/prepare-plan")+"/draft"
    days=[{"date":"2026-11-01","slots":[{"title":"TEST_FIXTURE 第一天午后","time_of_day":"afternoon","notes":""}]},
          {"date":"2026-11-02","slots":[{"title":"TEST_FIXTURE 第二天上午","time_of_day":"morning","notes":""},{"title":"TEST_FIXTURE 第二天下午","time_of_day":"afternoon","notes":""}]}]
    updated=client.put(draft_path,headers=headers,json={"expected_revision":1,"days":days})
    assert updated.status_code==200,updated.text
    schedule=[{"day_index":0,"slot_index":0,"start_time":"14:00","end_time":"15:00"},
              {"day_index":1,"slot_index":0,"start_time":"09:00","end_time":"10:00"},
              {"day_index":1,"slot_index":1,"start_time":"14:00","end_time":"15:00"}]
    result=client.post(path,headers=headers,json={"expected_revision":2,"schedule":schedule})
    assert result.status_code==201,result.text
    restored=client.get(path.removesuffix("/prepare-plan"),headers=headers).json()
    assert restored["prepared_plan"]["schedule"]==schedule
    assert restored["prepared_plan"]["result"]["plan_version_id"]==result.json()["plan_version_id"]
    assert restored["draft_artifact"]["revision"]==2
    with SessionLocal() as s:
        rows=s.scalars(select(Activity).where(Activity.plan_version_id==result.json()["plan_version_id"]).order_by(Activity.sequence_no)).all()
        assert [row.start_at[:10] for row in rows]==["2026-11-01","2026-11-02","2026-11-02"]
        assert [row.title for row in rows]==[slot["title"] for day in days for slot in day["slots"]]


def test_exact_existing_source_identity_only_not_name_matching(prepared_scope):
    client, headers, _, jid, tid, path, body = prepared_scope
    with SessionLocal() as s:
        journey=s.get(Journey,jid);m=s.get(JourneyMission,tid);intent=json.loads(m.intent_json);task=intent["goal_task"]
        task["draft_artifact"]["days"][0]["slots"][0]["place_id"]="amap:fixture-tower"
        task["research_places"]=[{"id":"amap:fixture-tower","name":"TEST_FIXTURE tower","provider":"amap","provider_provenance":"LIVE_PROVIDER", "region_status":"MATCHED"}]
        pid=str(uuid4());s.add(Place(id=pid,provider_key="amap",external_id="fixture-tower",city_code=journey.city_code,
            name="TEST_FIXTURE canonical tower",category="landmark",latitude=23.1,longitude=113.3,
            opening_hours_json=json.dumps({"status":"UNKNOWN"}),tags_json="[]",metadata_json=json.dumps({"cost_evidence":{"status":"KNOWN","amount_minor":0}}),updated_at=journey.updated_at))
        m.intent_json=json.dumps(intent);s.commit()
    result=client.post(path,headers=headers,json=body)
    assert result.status_code==201,result.text
    assert "SOURCE_IDENTITY" not in {gap["kind"] for gap in result.json()["gaps"]}
    with SessionLocal() as s:
        row=s.scalar(select(Activity).where(Activity.plan_version_id==result.json()["plan_version_id"]))
        assert row.place_id==pid
        assert json.loads(row.metadata_json)["source_candidate_id"]=="amap:fixture-tower"

    plans=client.get(f"/api/v1/journeys/{jid}/plans",headers=headers).json()
    plan=next(p for p in plans if p["id"]==result.json()["plan_version_id"])
    assert plan["activities"][0]["cost_status"]=="KNOWN_FREE"
    assert "ADMISSION_PRICE" not in {gap["kind"] for gap in result.json()["gaps"]}


def test_a_hop_the_agent_already_routed_is_not_listed_as_missing(prepared_scope):
    """The departure to-do used to name every same-day hop as missing, evidence or not.

    Measured on the walked journey: five same-day hops, four of them carrying a real AMap walking
    route the Agent had fetched (3385 m / 2708 s and friends,
    trial/results/20261022_v3_human_chrome/research-routes-in-walked-journey-1.txt), and the screen
    still said 转场路线 for all five.  A to-do that cannot be satisfied by evidence is not a to-do.  The
    hop nobody fetched must still be named, and naming the routed one must not make the candidate any
    more selectable than the authority rules already allow.
    """
    client, headers, _, jid, tid, path, body = prepared_scope
    with SessionLocal() as s:
        s.get(Journey, jid).end_at = "2026-11-01T22:00:00+08:00"
        s.commit()
    draft_path = path.removesuffix("/prepare-plan") + "/draft"
    days = [{"date": "2026-11-01", "slots": [
        {"title": "TEST_FIXTURE 第一站", "time_of_day": "morning", "notes": ""},
        {"title": "TEST_FIXTURE 第二站", "time_of_day": "afternoon", "notes": ""},
        {"title": "TEST_FIXTURE 第三站", "time_of_day": "evening", "notes": ""}]}]
    assert client.put(draft_path, headers=headers, json={"expected_revision": 1, "days": days}).status_code == 200
    with SessionLocal() as s:
        mission = s.get(JourneyMission, tid)
        intent = json.loads(mission.intent_json)
        task = intent["goal_task"]
        for index, place in enumerate(("a", "b", "c")):
            task["draft_artifact"]["days"][0]["slots"][index]["place_id"] = f"amap:fixture-{place}"
        # A slot that names a place has to name one this task actually researched -- the same door the
        # traveller's screen goes through, so the fixture cannot skip it.
        task["research_places"] = [{"id": f"amap:fixture-{place}", "name": f"TEST_FIXTURE 第{index}站",
            "provider": "amap", "provider_object_id": f"fixture-{place}", "provider_provenance": "LIVE_PROVIDER",
            "latitude": 39.9 + index * 0.01, "longitude": 116.4, "coordinate_system": "GCJ02",
            "region_status": "MATCHED", "category": "景点"}
            for index, place in enumerate(("a", "b", "c"))]
        task["research_routes"] = [{"from_place_id": "amap:fixture-a", "to_place_id": "amap:fixture-b",
            "from_name": "TEST_FIXTURE 第一站", "to_name": "TEST_FIXTURE 第二站", "provider": "amap",
            "distance_m": 1445, "duration_seconds": 1156, "captured_at": "2026-10-22T16:00:00+00:00",
            "source_url": "https://uri.amap.com/navigation?fixture=1"}]
        mission.intent_json = json.dumps(intent)
        s.commit()
    schedule = [{"day_index": 0, "slot_index": 0, "start_time": "09:00", "end_time": "10:00"},
                {"day_index": 0, "slot_index": 1, "start_time": "14:00", "end_time": "15:00"},
                {"day_index": 0, "slot_index": 2, "start_time": "19:00", "end_time": "20:00"}]
    result = client.post(path, headers=headers, json={"expected_revision": 2, "schedule": schedule})
    assert result.status_code == 201, result.text
    by_sequence: dict[int, set[str]] = {}
    for gap in result.json()["gaps"]:
        by_sequence.setdefault(gap["sequence_no"], set()).add(gap["kind"])
    assert "TRANSFER_ROUTE" not in by_sequence.get(2, set()), by_sequence
    assert "TRANSFER_ROUTE" in by_sequence.get(3, set()), by_sequence
    with SessionLocal() as s:
        rows = s.scalars(select(Activity).where(Activity.plan_version_id == result.json()["plan_version_id"])
            .order_by(Activity.sequence_no)).all()
        hop = json.loads(rows[1].metadata_json).get("transfer_route") or {}
        assert hop.get("distance_m") == 1445 and hop.get("provider") == "amap", hop
        assert json.loads(rows[2].metadata_json).get("transfer_route") is None
    plans = client.get(f"/api/v1/journeys/{jid}/plans", headers=headers).json()
    plan = next(item for item in plans if item["id"] == result.json()["plan_version_id"])
    assert plan["selectable"] is False, "a routed hop must not by itself open the selection door"


def test_every_to_do_line_names_who_holds_the_answer(prepared_scope):
    """A to-do line has to say what the traveller can do, not only what is missing.

    Measured on the walked journey (trial/results/20261022_v3_human_chrome/
    departure-price-evidence-probe-1.txt): the saved candidate listed 票价 for all seven places and
    转场路线 for hops nobody had measured, while the plan screen below it claimed one fixed reason -
    「相邻几站之间还没有可用的转场路线。」 - whatever the server had actually refused for.  The row is
    where the facts are known, so the row carries the answer: identity gaps go to the Agent, a fact a
    held place's source never gave goes to the Agent's next question, an unrouted hop goes to the
    Agent's route tool, and a price no source answered stays with the traveller.
    """
    client, headers, _, jid, tid, path, _ = prepared_scope
    with SessionLocal() as s:
        s.get(Journey, jid).end_at = "2026-11-01T22:00:00+08:00"
        s.commit()
    with SessionLocal() as s:
        journey = s.get(Journey, jid); m = s.get(JourneyMission, tid)
        intent = json.loads(m.intent_json); task = intent["goal_task"]
        task["draft_artifact"]["days"][0]["slots"][0]["place_id"] = "amap:fixture-holder-tower"
        task["draft_artifact"]["days"][0]["slots"].append(
            {"title": "TEST_FIXTURE 第二处", "time_of_day": "evening", "notes": "", "place_id": "amap:fixture-holder-park"})
        task["research_places"] = [
            {"id": "amap:fixture-holder-tower", "name": "TEST_FIXTURE tower", "provider": "amap",
             "provider_provenance": "LIVE_PROVIDER", "region_status": "MATCHED"},
            {"id": "amap:fixture-holder-park", "name": "TEST_FIXTURE park", "provider": "amap",
             "provider_provenance": "LIVE_PROVIDER", "region_status": "MATCHED"}]
        for external, name in (("fixture-holder-tower", "TEST_FIXTURE canonical tower"), ("fixture-holder-park", "TEST_FIXTURE canonical park")):
            s.add(Place(id=str(uuid4()), provider_key="amap", external_id=external, city_code=journey.city_code,
                name=name, category="landmark", latitude=23.1, longitude=113.3,
                opening_hours_json=json.dumps({"status": "UNKNOWN"}), tags_json="[]",
                metadata_json=json.dumps({"cost_evidence": {"status": "UNKNOWN", "amount_minor": None}}),
                updated_at=journey.updated_at))
        m.intent_json = json.dumps(intent); s.commit()
    schedule = [{"day_index": 0, "slot_index": 0, "start_time": "14:00", "end_time": "15:00"},
                {"day_index": 0, "slot_index": 1, "start_time": "19:00", "end_time": "20:00"}]
    result = client.post(path, headers=headers, json={"expected_revision": 1, "schedule": schedule})
    assert result.status_code == 201, result.text
    answers = {(gap["kind"], gap["sequence_no"]): gap["resolution"] for gap in result.json()["gaps"]}
    assert answers[("OPENING_HOURS", 1)] == "ASK_AGENT_FOR_PLACE_FACT", answers
    assert answers[("ADMISSION_PRICE", 1)] == "PRICE_HELD_BY_TRAVELLER", answers
    assert answers[("TRANSFER_ROUTE", 2)] == "ASK_AGENT_TO_MEASURE_HOP", answers
    kinds = {gap["kind"] for gap in result.json()["gaps"]}
    assert "PLACE_REQUIRED" not in kinds and "SOURCE_IDENTITY" not in kinds, kinds
    plans = client.get(f"/api/v1/journeys/{jid}/plans", headers=headers).json()
    plan = next(item for item in plans if item["id"] == result.json()["plan_version_id"])
    carried = {(row["kind"], row["sequence_no"]): row.get("resolution") for row in plan["explanation"]["unresolved_facts"]}
    assert carried[("ADMISSION_PRICE", 1)] == "PRICE_HELD_BY_TRAVELLER", carried
    assert carried[("TRANSFER_ROUTE", 2)] == "ASK_AGENT_TO_MEASURE_HOP", carried
