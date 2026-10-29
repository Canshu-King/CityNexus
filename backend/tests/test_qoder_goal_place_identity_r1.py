"""The Agent's own research has to leave a canonical place row, or the traveller cannot select it.

Measured on a real screen with real Amap places (2026-10-22, walk-34): a formal candidate saved from
the Agent's draft came back with `SOURCE_IDENTITY` on every item that carried a provider id, the
button 「选用这份方案」 never rendered, and the same database held no rows in `places` at all. The
schedule was grounded; the identity behind it was never promoted out of the task. These arms pin the
promotion door and what it must and must not claim.
"""

from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import select
from test_bootstrap_place_facts import enabled_settings, signed_place  # noqa: F401  (fixtures are imported on purpose)
from app.agent.goal_place_identity import attach_canonical_places
from app.db.models import Journey, JourneyMission, Place
from app.db.session import SessionLocal

AMAP_LEAD = {
    "id": "amap:TESTFIXTURE01", "provider": "amap", "provider_object_id": "TESTFIXTURE01",
    "name": "TEST_FIXTURE 什刹海边咖啡馆", "category": "cafe",
    "latitude": 39.9380, "longitude": 116.3830, "coordinate_system": "GCJ02",
    "source_url": "https://uri.amap.com/marker?position=116.3830,39.9380",
    "provider_provenance": "LIVE_PROVIDER", "region_status": "MATCHED",
    "public_address": "北京市西城区", "opening_status": "UNKNOWN", "cost_status": "UNKNOWN",
}

PHOTON_LEAD = {
    "id": "node:999000001", "provider": "photon", "name": "TEST_FIXTURE 胡同小吃街",
    "category": "food", "latitude": 39.9370, "longitude": 116.4030,
    "source_url": "https://www.openstreetmap.org/node/999000001",
    "provider_provenance": "LIVE_PROVIDER", "region_status": "MATCHED",
    "opening_status": "UNKNOWN", "cost_status": "UNKNOWN",
}


def _attach(journey_id, leads, task=None):
    with SessionLocal() as session:
        journey = session.get(Journey, journey_id)
        attached = attach_canonical_places(session, journey, task if task is not None else {}, leads)
        session.commit()
        return attached


def test_a_live_amap_lead_becomes_one_canonical_row_and_the_lead_says_which(signed_place):
    client, owner, outsider, journey_id, *_ = signed_place
    lead = dict(AMAP_LEAD)
    attached = _attach(journey_id, [lead])

    assert list(attached) == ["amap:TESTFIXTURE01"]
    assert lead.get("canonical_place_id") == attached["amap:TESTFIXTURE01"]
    with SessionLocal() as session:
        # Count this provider object, not every Amap row in a shared test database: another fixture
        # legitimately holds one, and "rows for this object" is the claim actually being made.
        rows = session.scalars(select(Place).where(Place.provider_key == "amap",
            Place.external_id.in_(["amap:TESTFIXTURE01", "TESTFIXTURE01"]))).all()
        assert [row.external_id for row in rows] == ["amap:TESTFIXTURE01"], [row.external_id for row in rows]
        row = rows[0]
        # The shared table's own convention: the provider key is kept and the object id is prefixed
        # with it, so the same provider object cannot be filed twice under two spellings.
        assert row.external_id == "amap:TESTFIXTURE01"
        assert row.city_code == session.get(Journey, journey_id).city_code
        assert row.name == "TEST_FIXTURE 什刹海边咖啡馆"
        assert row.coordinate_system == "WGS84"
        assert row.source_coordinate_system == "GCJ02"
        # The number stored here is the converted one, not a second copy of what Amap handed over.
        assert abs(row.latitude - lead["latitude"]) > 0.0001
        assert abs(row.latitude - lead["latitude"]) < 0.02
        # Identity was promoted; nobody checked a price or an opening window, so neither is claimed.
        opening = json.loads(row.opening_hours_json)
        assert str(opening.get("status", "")).upper() == "UNKNOWN" and opening.get("intervals") == []
        cost = json.loads(row.metadata_json).get("cost_evidence") or {}
        assert str(cost.get("status", "UNKNOWN")).upper() == "UNKNOWN"
        assert not cost.get("amount_minor"), cost


def test_a_lead_from_an_openstreetmap_style_source_is_filed_by_its_own_object(signed_place):
    client, owner, outsider, journey_id, *_ = signed_place
    lead = dict(PHOTON_LEAD)
    attached = _attach(journey_id, [lead])
    assert attached == {"node:999000001": lead["canonical_place_id"]}
    with SessionLocal() as session:
        row = session.get(Place, lead["canonical_place_id"])
        assert row.provider_key == "photon"
        assert row.external_id == "photon:node/999000001"
        # No provider coordinate claim on this lead, so nothing is asserted about a conversion.
        assert row.source_coordinate_system in (None, "WGS84")
        assert row.latitude == lead["latitude"]


def test_a_lead_that_is_not_live_evidence_is_left_a_lead(signed_place):
    client, owner, outsider, journey_id, *_ = signed_place
    before = _place_count()
    refusals = [
        {**AMAP_LEAD, "id": "amap:CONFLICTED", "provider_object_id": "CONFLICTED", "region_status": "CONFLICT"},
        {**AMAP_LEAD, "id": "amap:UNVERIFIED", "provider_object_id": "UNVERIFIED",
         "provider_provenance": "MODEL_SUGGESTION"},
        {**AMAP_LEAD, "id": "amap:NOCATEGORY", "provider_object_id": "NOCATEGORY", "category": ""},
        {**AMAP_LEAD, "id": "amap:NOCOORDS", "provider_object_id": "NOCOORDS", "latitude": None},
    ]
    attached = _attach(journey_id, refusals)
    assert attached == {}
    assert all("canonical_place_id" not in lead for lead in refusals)
    assert _place_count() == before


def _place_count() -> int:
    with SessionLocal() as session:
        return len(session.scalars(select(Place)).all())


def test_a_confirmed_schedule_that_holds_a_canonical_row_can_be_selected(signed_place):
    """The door the traveller actually needed: press save, then press 选用这份方案.

    Same fixture journey, one draft slot whose place id is a live Amap lead. Before this slice the
    candidate came back with `SOURCE_IDENTITY` and `selectable: false` because nothing on this path
    ever wrote the place row; the row now comes from the research step, and the preparation door only
    binds to it.
    """
    client, owner, outsider, journey_id, *_ = signed_place
    root = f"/api/v1/journeys/{journey_id}"
    created = client.post(root + "/agent/goal-tasks", headers=owner, json={
        "goal": "TEST_FIXTURE 下午在湖边咖啡馆坐着", "model_consent": False, "online_research_consent": False}).json()
    task_id = created["task_id"]
    draft = client.put(root + f"/agent/goal-tasks/{task_id}/draft", headers=owner, json={"expected_revision": 0,
        "days": [{"date": "2026-11-01", "slots": [{"title": "TEST_FIXTURE 什刹海边咖啡馆",
                                                  "time_of_day": "afternoon", "notes": "价格待核实"}]}]})
    assert draft.status_code == 200, draft.text

    lead = dict(AMAP_LEAD)
    with SessionLocal() as session:
        mission = session.get(JourneyMission, task_id)
        intent = json.loads(mission.intent_json)
        task = intent["goal_task"]
        task["research_places"] = [lead]
        task["candidate_place_ids"] = [lead["id"]]
        task["draft_artifact"]["days"][0]["slots"][0]["place_id"] = lead["id"]
        assert attach_canonical_places(session, session.get(Journey, journey_id), task, [lead])
        assert lead["canonical_place_id"] in task["candidate_place_ids"]
        mission.intent_json = json.dumps(intent, ensure_ascii=False)
        session.commit()

    result = client.post(root + f"/agent/goal-tasks/{task_id}/prepare-plan",
                         headers={**owner, "Idempotency-Key": str(uuid4())},
                         json={"expected_revision": 1, "schedule": [{"day_index": 0, "slot_index": 0,
                                                                    "start_time": "14:00", "end_time": "15:00"}]})
    assert result.status_code == 201, result.text
    data = result.json()
    kinds = {gap["kind"] for gap in data["gaps"]}
    assert "SOURCE_IDENTITY" not in kinds and "PLACE_REQUIRED" not in kinds, data["gaps"]
    assert kinds == {"OPENING_HOURS", "ADMISSION_PRICE"}, kinds

    plan = next(item for item in client.get(f"{root}/plans", headers=owner).json()
                if item["id"] == data["plan_version_id"])
    # The identity veto is gone: the item now points at a real place row. What keeps this plan
    # unselectable is the *other* rule -- an unchecked opening window is not evidence a venue is open
    # (services.plan_authority_blocker, and the pending ORD-0708 ruling). Stated here so the next
    # change moves a named rule, not a silent expectation.
    assert plan["activities"][0]["place_id"] == lead["canonical_place_id"]
    assert plan["selectable"] is False
    assert "SOURCE_IDENTITY" not in json.dumps(data["gaps"], ensure_ascii=False)


def test_a_promoted_lead_says_on_the_row_whether_its_region_was_ever_checked(signed_place):
    """The identity door files an unchecked region, so the row has to admit it.

    Asked for by the 2026-10-22 ruling as an UNKNOWN-region cross-region regression on
    `goal_place_identity.attach_canonical_places`.  Measured before choosing the shape of the pin:
    with the door changed to accept only region_status=MATCHED the arm below went red on two leads
    (an explicitly-UNKNOWN one and one with no region field at all) because both were filed with this
    journey's city code -- the hole is real.  The same measurement says the tightening cannot go in
    blind: tonight's 22 canary databases hold 851 amap leads with region_status=MATCHED and 126 photon
    leads with region_status=UNKNOWN (read across D:/moodle/_cmdr_v3_live_1022/citynexus_v3_*.db by
    the probe that wrote trial/results/20261022_v3_human_chrome/region-status-by-provider-1.txt), and
    `public_region_status` answers UNKNOWN whenever a label or an address field is simply absent
    (app/region_matching.py:57, :67) -- so refusing UNKNOWN would strand places a real traveller has
    already been given, which is the opposite of what the ruling asks for.  What ships here is the
    disclosure the authority rules can act on: the promoted row records the region state it came in
    with, so an unconfirmed identity can never be presented as a checked local place.
    """
    client, owner, outsider, journey_id, *_ = signed_place
    unconfirmed = {**AMAP_LEAD, "id": "amap:TESTFIXTURE-NOREGION", "provider_object_id": "TESTFIXTURE-NOREGION",
                   "name": "TEST_FIXTURE 什刹海(没有地区字段)"}
    del unconfirmed["region_status"]
    confirmed = {**AMAP_LEAD, "id": "amap:TESTFIXTURE-REGIONOK", "provider_object_id": "TESTFIXTURE-REGIONOK",
                 "name": "TEST_FIXTURE 什刹海边确认过地区"}
    attached = _attach(journey_id, [unconfirmed, confirmed])
    assert sorted(attached) == ["amap:TESTFIXTURE-NOREGION", "amap:TESTFIXTURE-REGIONOK"], attached
    with SessionLocal() as session:
        rows = {row.external_id: json.loads(row.metadata_json) for row in session.scalars(
            select(Place).where(Place.provider_key == "amap",
                Place.external_id.in_(["amap:TESTFIXTURE-NOREGION", "amap:TESTFIXTURE-REGIONOK"]))).all()}
        assert sorted(rows) == ["amap:TESTFIXTURE-NOREGION", "amap:TESTFIXTURE-REGIONOK"], sorted(rows)
        assert str(rows["amap:TESTFIXTURE-NOREGION"].get("region_status")) == "UNKNOWN", rows
        assert str(rows["amap:TESTFIXTURE-REGIONOK"].get("region_status")) == "MATCHED", rows
        # The city stamp is the journey's own, whatever the coordinates say -- which is exactly why
        # the row has to carry the region state it arrived with.
        assert session.get(Place, attached["amap:TESTFIXTURE-NOREGION"]).city_code ==             session.get(Journey, journey_id).city_code
