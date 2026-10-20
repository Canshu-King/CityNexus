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
    assert {gap["kind"] for gap in data["gaps"]} == {"PLACE_REQUIRED","OPENING_HOURS","ADMISSION_PRICE"}
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
