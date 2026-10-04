from __future__ import annotations

from fastapi.testclient import TestClient

import app.main as main_module
from app.agent.autorun import stop_autorun
from demo_stage import demo_reset_headers


client = TestClient(main_module.app)


def test_r27_member_projection_keeps_owner_and_collaborator_context_separate() -> None:
    stop_autorun()
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    second = client.post(
        "/api/v1/travelers",
        json={"display_name": "R27 collaborator", "email": None, "locale": "en-US", "timezone": "UTC"},
    ).json()
    member = client.post(
        f"/api/v1/journeys/{ids['journey_id']}/members",
        json={"traveler_id": second["id"], "role": "COLLABORATOR", "invited_by": ids["traveler_id"]},
    ).json()
    preferences = client.put(
        f"/api/v1/journeys/{ids['journey_id']}/members/{member['id']}/preferences",
        json={"preferences": [{"category": "interest", "key": "craft", "value": True, "weight": 1.0}]},
    )
    assert preferences.status_code == 200, preferences.text

    response = client.post(
        "/api/v1/agent/tools/v2/inspect_journey",
        json={"request_id": "r27-member-surface-001", "journey_id": ids["journey_id"]},
    )
    assert response.status_code == 200, response.text
    members = response.json()["collective_journey"]["members"]
    assert {item["traveler_id"] for item in members} == {ids["traveler_id"], second["id"]}
    by_traveler = {item["traveler_id"]: item for item in members}
    assert by_traveler[ids["traveler_id"]]["role"] == "OWNER"
    assert by_traveler[second["id"]]["role"] == "COLLABORATOR"
    assert by_traveler[second["id"]]["journey_scoped_explicit_preferences"] == [
        {"category": "interest", "key": "craft", "value": True, "weight": 1.0}
    ]
    assert by_traveler[ids["traveler_id"]]["journey_scoped_explicit_preferences"] == []
    assert by_traveler[ids["traveler_id"]]["capabilities"] != by_traveler[second["id"]]["capabilities"]

    withdrawn = client.post(
        f"/api/v1/journeys/{ids['journey_id']}/members/{member['id']}/withdraw"
    )
    assert withdrawn.status_code == 200, withdrawn.text
    response = client.post(
        "/api/v1/agent/tools/v2/inspect_journey",
        json={"request_id": "r27-member-surface-002", "journey_id": ids["journey_id"]},
    )
    assert [item["traveler_id"] for item in response.json()["collective_journey"]["members"]] == [
        ids["traveler_id"]
    ]
