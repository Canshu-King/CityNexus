"""The city door names the item it refused, instead of sending the traveller back to a retry.

Why this file exists.  On the clean generation a real walk -- send the goal sentence, let the Agent's round
finish, enter the trip, tick 「按以上时间准备方案」, press 「保存为正式候选方案」 -- was refused with
409 PLACE_NOT_IN_JOURNEY_CITY whose `details` was null
(trial/results/20261026_gozero/bf110-replan-apply-full-chain-430-r2.txt:35), and the card answered
「这次未能保存，时间仍留在这里，可以重试。」 (frontend/src/trial/mobile/DraftDepartureCard.tsx, the last arm of
that ladder).  The probe over the same rows (trial/results/20261026_gozero/bg111-city-refusal-probe.txt)
shows the refusal is about exactly one item out of six: five places bound inside this journey's own city
list, one -- 北海公园 -- bound to a row filed under another city.  Retrying the same six items cannot change
that, so the traveller needs the item named, not an invitation to press again.

Both raise sites are covered (backend/app/agent/goal_preparation.py:285 -- the candidate-id arm -- and
:303, the research-lead canonical-id arm), and the middle test puts the same row back in the journey's own
city list to show the door discriminates rather than refusing whatever carries a bound place.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from test_bootstrap_place_facts import enabled_settings, signed_place  # noqa: E402,F401  (fixtures are imported on purpose)

ROOT = "/api/v1/journeys"
DATE = "2026-12-03"
TITLE = "TEST_FIXTURE 北海公园"
OTHER_CITY = "TEST_FIXTURE_OTHER_CITY"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _window(journey_id: str) -> None:
    from app.db.models import Journey
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        trip = session.get(Journey, journey_id)
        trip.start_at = f"{DATE}T09:00+08:00"
        trip.end_at = f"{DATE}T18:00+08:00"
        session.commit()


def _journey_city_code(journey_id: str) -> str:
    from app.db.models import Journey
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        return session.get(Journey, journey_id).city_code


def _seed_place(city_code: str) -> str:
    """A formal Place row -- the table the preparation door binds slot ids against (goal_preparation.py:283)."""
    from app.db.models import Place
    from app.db.session import SessionLocal

    ident = str(uuid4())
    with SessionLocal() as session:
        session.add(Place(id=ident, provider_key="amap", external_id="amap:" + ident[:8],
                          city_code=city_code, name="TEST_FIXTURE 北海公园", category="SIGHTSEE",
                          latitude=39.92, longitude=116.39, opening_hours_json=json.dumps({}),
                          tags_json="[]", metadata_json="{}", updated_at=_now()))
        session.commit()
    return ident


def _set_place_city(place_id: str, city_code: str) -> None:
    from app.db.models import Place
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        session.get(Place, place_id).city_code = city_code
        session.commit()


def _task_with_one_bound_slot(client, owner, journey_id, place_id, *, via_lead: str | None = None) -> str:
    _window(journey_id)
    task_id = client.post(f"{ROOT}/{journey_id}/agent/goal-tasks", headers=owner, json={
        "goal": "TEST_FIXTURE 城市对照", "model_consent": False, "online_research_consent": False}).json()["task_id"]
    draft = client.put(f"{ROOT}/{journey_id}/agent/goal-tasks/{task_id}/draft", headers=owner, json={
        "expected_revision": 0,
        "days": [{"date": DATE, "slots": [{"title": TITLE, "time_of_day": "morning", "notes": ""}]}]})
    assert draft.status_code == 200, draft.text
    # Bind the row the way a finished round would, so the door reaches the city comparison instead of the
    # "no identity" arm.  via_lead reproduces the second site: the slot then carries a provider id that is
    # not in the candidate list, and only the research lead points at the Place.
    from app.db.models import JourneyMission
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        mission = session.get(JourneyMission, task_id)
        intent = json.loads(mission.intent_json)
        task = intent["goal_task"]
        source = place_id if via_lead is None else via_lead
        task["candidate_place_ids"] = [] if via_lead else [place_id]
        if via_lead:
            # The lead shape the resolver actually reads: goal_artifacts.py:98-100 keys on ``id`` and
            # requires a live provenance and a live provider name, otherwise the door answers
            # PLACE_NOT_IN_GOAL_TASK_SCOPE before it ever reaches the city comparison.
            task["research_places"] = [{"id": via_lead, "canonical_place_id": place_id,
                                        "provider": "amap", "provider_provenance": "LIVE_PROVIDER",
                                        "region_status": "MATCHED"}]
        task["draft_artifact"]["days"][0]["slots"][0]["place_id"] = source
        mission.intent_json = json.dumps(intent)
        session.commit()
    return task_id


def _prepare(client, owner, journey_id, task_id):
    return client.post(f"{ROOT}/{journey_id}/agent/goal-tasks/{task_id}/prepare-plan",
                       headers={**owner, "Idempotency-Key": str(uuid4())},
                       json={"expected_revision": 1,
                             "schedule": [{"day_index": 0, "slot_index": 0,
                                           "start_time": "09:00", "end_time": "10:00"}]})


def test_the_candidate_id_arm_names_the_item_its_place_and_both_city_codes(signed_place) -> None:
    client, owner, _outsider, journey_id, *_ = signed_place
    place_id = _seed_place(_journey_city_code(journey_id))
    task_id = _task_with_one_bound_slot(client, owner, journey_id, place_id)
    _set_place_city(place_id, OTHER_CITY)
    answer = _prepare(client, owner, journey_id, task_id)
    assert answer.status_code == 409, answer.text
    error = json.loads(answer.text)["error"]
    # The message stays verbatim, so nothing that reads this door by message breaks.
    assert error["message"] == "PLACE_NOT_IN_JOURNEY_CITY"
    assert error["reason_code"] == "PLACE_NOT_IN_JOURNEY_CITY"
    details = error["details"]
    assert details["sequence_no"] == 1 and details["title"] == TITLE
    assert details["place_city_code"] == OTHER_CITY
    assert details["journey_city_code"] == _journey_city_code(journey_id)
    assert details["date"] == DATE and details["place_name"] == "TEST_FIXTURE 北海公园"


def test_the_same_row_back_in_the_journeys_own_city_is_not_refused_as_wrong_city(signed_place) -> None:
    # Control arm: the door has to discriminate, not refuse whatever carries a bound place.
    client, owner, _outsider, journey_id, *_ = signed_place
    city = _journey_city_code(journey_id)
    place_id = _seed_place(city)
    task_id = _task_with_one_bound_slot(client, owner, journey_id, place_id)
    answer = _prepare(client, owner, journey_id, task_id)
    if answer.status_code == 409:
        assert json.loads(answer.text)["error"].get("reason_code") != "PLACE_NOT_IN_JOURNEY_CITY", answer.text
    else:
        assert answer.status_code == 201, answer.text


def test_the_research_lead_arm_names_the_item_too(signed_place) -> None:
    # The second site resolves the place through the lead's canonical id (goal_preparation.py:303); it must
    # carry the same named row, or the traveller gets the old one-word refusal on half the paths.
    client, owner, _outsider, journey_id, *_ = signed_place
    place_id = _seed_place(_journey_city_code(journey_id))
    lead_source = "amap:TEST_FIXTURE_LEAD"
    task_id = _task_with_one_bound_slot(client, owner, journey_id, place_id, via_lead=lead_source)
    _set_place_city(place_id, OTHER_CITY)
    answer = _prepare(client, owner, journey_id, task_id)
    assert answer.status_code == 409, answer.text
    error = json.loads(answer.text)["error"]
    assert error["message"] == "PLACE_NOT_IN_JOURNEY_CITY"
    details = error["details"]
    assert details["sequence_no"] == 1 and details["title"] == TITLE
    assert details["place_city_code"] == OTHER_CITY
