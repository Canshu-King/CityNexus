"""Signed HTTP editing and reload of date-scoped travel requirements."""

import json
from copy import deepcopy
from datetime import datetime, timezone

from sqlalchemy import select
from test_issue47_private_reads import stack  # noqa: F401

from app import main, traveler_principal
from app.agent import goal_tasks
from app.db.models import Journey, JourneyMember, JourneyMission, JourneyRoleCapability
from app.db.session import get_session


def test_signed_full_save_preserves_requirements_on_reload_and_conflict(stack):
    client, ids, _ = stack
    factory = client.app.dependency_overrides[get_session]
    db = factory()
    session = next(db)
    journey = session.get(Journey, ids["journey"])
    journey.start_at = "2026-11-01T09:00:00+08:00"
    journey.end_at = "2026-11-02T20:00:00+08:00"
    day = journey.start_at[:10]
    member = session.scalar(select(JourneyMember).where(
        JourneyMember.journey_id == journey.id, JourneyMember.traveler_id == ids["owner"],
    ))
    session.add(JourneyRoleCapability(role="OWNER", capability="JOURNEY_UPDATE",
        scope_message_key="TEST_FIXTURE", created_at=datetime.now(timezone.utc).isoformat()))
    session.commit()
    task = goal_tasks.create_goal_task(session, journey, member, goal="TEST_FIXTURE 晚起且保留预约",
        model_consent=False, online_research_consent=False, max_model_turns=3, max_tool_calls=4)
    task_id = task["task_id"]
    mission = session.get(JourneyMission, task_id)
    intent = json.loads(mission.intent_json)
    booked = {"title": "TEST_FIXTURE 已订午间活动", "time_of_day": "afternoon",
              "reservation_id": "TEST_FIXTURE-reservation", "locked": True, "start_time": "13:00"}
    artifact = {"revision": 4, "status": "DRAFT",
        "date_constraints": {day: {"morning": {"start_not_before": "11:00"}}},
        "days": [{"date": day, "slots": [deepcopy(booked),
            {"title": "TEST_FIXTURE 自由活动", "time_of_day": "evening"}]}]}
    intent["goal_task"]["draft_artifact"] = artifact
    mission.intent_json = json.dumps(intent, ensure_ascii=False)
    session.commit()
    db.close()

    draft_path = "/api/v1/journeys/{journey_id}/agent/goal-tasks/{task_id}/draft"
    task_path = draft_path.removesuffix("/draft")
    for route in main.app.routes:
        if getattr(route, "path", None) in {draft_path, task_path}:
            client.app.add_api_route(route.path, route.endpoint, methods=list(route.methods))
    url = draft_path.format(journey_id=ids["journey"], task_id=task_id)
    read_url = url.removesuffix("/draft")
    edited = deepcopy(artifact["days"])
    edited[0]["slots"][1]["title"] = "TEST_FIXTURE 改成晚餐后散步"
    body = {"days": edited, "expected_revision": 4}
    assert client.put(url, json=body).status_code == 401
    stranger = {"Authorization": "Bearer " + traveler_principal.issue_traveler_token(ids["stranger"])}
    assert client.put(url, headers=stranger, json=body).status_code == 403
    owner = {"Authorization": "Bearer " + traveler_principal.issue_traveler_token(ids["owner"])}
    response = client.put(url, headers=owner, json=body)
    assert response.status_code == 200, response.text
    assert "no-store" in response.headers["Cache-Control"]
    reloaded = client.get(read_url, headers=owner)
    assert reloaded.status_code == 200, reloaded.text
    saved = reloaded.json()["draft_artifact"]
    assert saved["date_constraints"] == artifact["date_constraints"]
    assert saved["revision"] == 5
    assert saved["days"][0]["slots"][0] == booked
    assert saved["days"][0]["slots"][1]["title"] == "TEST_FIXTURE 改成晚餐后散步"

    conflicting = deepcopy(saved["days"])
    conflicting[0]["slots"][0]["time_of_day"] = "morning"
    refused = client.put(url, headers=owner, json={"days": conflicting, "expected_revision": 5})
    assert refused.status_code == 409, refused.text
    assert "DRAFT_PROTECTED_ACTIVITY_REQUIRES_USER_CHOICE" in refused.text
    assert client.get(read_url, headers=owner).json()["draft_artifact"] == saved
