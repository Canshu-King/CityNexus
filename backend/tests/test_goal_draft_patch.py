from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.agent.goal_draft_patch import draft_patch_definition, replace_draft_slots


@pytest.fixture
def draft_context():
    journey = SimpleNamespace(
        start_at="2026-11-01T09:00:00+08:00",
        end_at="2026-11-02T21:00:00+08:00",
    )
    morning = {
        "title": "TEST_FIXTURE 原样保留早餐",
        "time_of_day": "morning",
        "place_id": "existing-place",
        "notes": "原备注",
        "author": "USER",
        "opening_status": "OPEN",
        "cost_status": "KNOWN_FREE",
        "custom_extension": {"kept": True},
    }
    dinner = {
        "title": "TEST_FIXTURE 原晚餐",
        "time_of_day": "evening",
        "place_id": "old-evening-place",
        "notes": "晚餐安排",
        "author": "USER",
        "custom_extension": ["keep exactly"],
    }
    next_day = {
        "date": "2026-11-02",
        "slots": [{
            "title": "TEST_FIXTURE 第二天晚餐",
            "time_of_day": "evening",
            "place_id": "next-day-place",
            "notes": "第二天不能被重写",
            "author": "USER",
            "custom_extension": {"id": 2},
        }],
        "custom_day_field": "preserve",
    }
    task = {
        "candidate_place_ids": ["existing-place", "old-evening-place", "next-day-place", "new-evening-place"],
        "research_places": [],
        "research_areas": [],
        "draft_artifact": {
            "revision": 7,
            "status": "DRAFT",
            "custom_top_level": {"keep": True},
            "days": [
                {"date": "2026-11-01", "slots": [deepcopy(morning), deepcopy(dinner)], "custom_day_field": "today"},
                deepcopy(next_day),
            ],
        },
    }
    return journey, task, morning, dinner, next_day


def test_replaces_only_selected_time_block_and_preserves_other_data(draft_context):
    journey, task, morning, _dinner, next_day = draft_context
    original = deepcopy(task["draft_artifact"])

    result = replace_draft_slots(
        journey,
        task,
        date="2026-11-01",
        time_of_day="evening",
        slots=[{
            "title": "TEST_FIXTURE 新晚餐",
            "time_of_day": "evening",
            "place_id": "new-evening-place",
            "notes": "只改今晚",
        }],
    )

    assert result["revision"] == 8
    assert result["custom_top_level"] == original["custom_top_level"]
    assert result["days"][0]["custom_day_field"] == "today"
    assert result["days"][0]["slots"] == [
        morning,
        {
            "title": "TEST_FIXTURE 新晚餐",
            "time_of_day": "evening",
            "place_id": "new-evening-place",
            "notes": "只改今晚",
            "author": "MODEL_SUGGESTION",
            "opening_status": "UNKNOWN",
            "cost_status": "UNKNOWN",
            "travel_time_status": "UNKNOWN",
        },
    ]
    assert result["days"][1] == next_day
    assert task["draft_artifact"] == original

    result["days"][1]["slots"][0]["notes"] = "mutated result only"
    assert task["draft_artifact"]["days"][1]["slots"][0]["notes"] == "第二天不能被重写"


def test_can_delete_selected_existing_block(draft_context):
    journey, task, _morning, _dinner, _next_day = draft_context
    deleted = replace_draft_slots(
        journey,
        task,
        date="2026-11-01",
        time_of_day="evening",
        slots=[],
    )
    assert [slot["time_of_day"] for slot in deleted["days"][0]["slots"]] == ["morning"]
    assert deleted["days"][1] == _next_day


@pytest.mark.parametrize(
    ("date", "time_of_day", "slots", "detail"),
    [
        ("2026-11-03", "evening", [], "DRAFT_DATE_NOT_FOUND"),
        ("2026-11-01", "night", [], "DRAFT_TIME_OF_DAY_INVALID"),
        ("2026-11-01", "afternoon", [], "DRAFT_TIME_OF_DAY_NOT_FOUND"),
        ("2026-11-01", "evening", [{"title": "TEST_FIXTURE 错时段", "time_of_day": "morning"}], "DRAFT_SLOT_INVALID"),
    ],
)
def test_rejects_unknown_date_or_time_area(draft_context, date, time_of_day, slots, detail):
    journey, task, *_ = draft_context
    with pytest.raises(HTTPException) as rejected:
        replace_draft_slots(journey, task, date=date, time_of_day=time_of_day, slots=slots)
    assert rejected.value.status_code == 422
    assert rejected.value.detail == detail


def test_rejects_a_block_that_would_exceed_day_limit(draft_context):
    journey, task, *_ = draft_context
    task["draft_artifact"]["days"][0]["slots"] = [
        *[
            {"title": f"TEST_FIXTURE retained {index}", "time_of_day": "morning"}
            for index in range(5)
        ],
        {"title": "TEST_FIXTURE existing evening", "time_of_day": "evening"},
    ]
    with pytest.raises(HTTPException) as rejected:
        replace_draft_slots(
            journey,
            task,
            date="2026-11-01",
            time_of_day="evening",
            slots=[{"title": "TEST_FIXTURE extra", "time_of_day": "evening"},
                   {"title": "TEST_FIXTURE extra two", "time_of_day": "evening"}],
        )
    assert rejected.value.status_code == 422
    assert rejected.value.detail == "DRAFT_SLOTS_INVALID"


@pytest.mark.parametrize(
    ("place_id", "research_places", "detail"),
    [
        ("not-in-task", [], "DRAFT_PLACE_NOT_RESEARCHED"),
        ("conflict-place", [{"id": "conflict-place", "region_status": "CONFLICT"}], "DRAFT_PLACE_REGION_CONFLICT"),
    ],
)
def test_delegates_place_scope_and_region_gates_to_normalizer(draft_context, place_id, research_places, detail):
    journey, task, *_ = draft_context
    task["research_places"] = research_places
    with pytest.raises(HTTPException) as rejected:
        replace_draft_slots(
            journey,
            task,
            date="2026-11-01",
            time_of_day="evening",
            slots=[{"title": "TEST_FIXTURE venue", "time_of_day": "evening", "place_id": place_id}],
        )
    assert rejected.value.status_code == 422
    assert rejected.value.detail == detail


def test_tool_schema_exposes_narrow_date_period_patch():
    schema = draft_patch_definition()["function"]
    assert schema["name"] == "replace_draft_slots"
    parameters = schema["parameters"]
    assert parameters["required"] == ["date", "time_of_day", "slots"]
    assert parameters["properties"]["slots"]["maxItems"] == 6
    assert parameters["additionalProperties"] is False


def test_followup_runtime_offers_patch_and_preserves_unrelated_slots(monkeypatch, goal_scope):
    import json
    from uuid import uuid4
    from app.agent import goal_tasks
    from test_goal_tasks import _create
    session,journey,member=goal_scope
    journey.end_at='2026-11-02T21:00:00+08:00';session.commit()
    created=_create(session,journey,member,max_model_turns=4,max_tool_calls=4)
    mission=session.get(goal_tasks.JourneyMission,created['task_id']);intent=json.loads(mission.intent_json)
    original={'revision':3,'status':'DRAFT','days':[
      {'date':'2026-11-01','slots':[{'title':'original morning','time_of_day':'morning','author':'USER','notes':'unchanged'}]},
      {'date':'2026-11-02','slots':[{'title':'old afternoon','time_of_day':'afternoon'}, {'title':'original dinner','time_of_day':'evening','author':'USER','notes':'unchanged dinner'}]}]}
    intent['goal_task']['draft_artifact']=original;mission.intent_json=json.dumps(intent);session.commit()
    class Agent:
        provider_key=model_key='TEST_FIXTURE'
        turn=0
        def _complete(self,messages):
            assert 'replace_draft_slots' in self._tool_allowlist
            assert 'save_draft_itinerary' not in self._tool_allowlist
            self.turn+=1
            if self.turn==1:
                return {'tool_calls':[{'id':'fixture-patch','function':{'name':'replace_draft_slots','arguments':json.dumps({'date':'2026-11-02','time_of_day':'afternoon','slots':[{'title':'easy afternoon','time_of_day':'afternoon','notes':'TEST_FIXTURE'}]})}}]}
            return {'content':'TEST_FIXTURE saved'}
    monkeypatch.setattr(goal_tasks,'_new_goal_agent',lambda *_:Agent())
    result=goal_tasks.resume_goal_task(session,journey,member,created['task_id'],user_message='只改第二天下午',message_id=str(uuid4()))
    draft=result['draft_artifact']
    assert draft['revision']==4
    assert draft['days'][0]==original['days'][0]
    assert draft['days'][1]['slots'][1]==original['days'][1]['slots'][1]
    assert draft['days'][1]['slots'][0]['title']=='easy afternoon'

from test_goal_tasks import goal_scope
