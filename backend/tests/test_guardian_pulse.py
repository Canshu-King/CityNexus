from fastapi.testclient import TestClient
from datetime import datetime, timezone
import json

import app.main as main_module
from app.db.models import GuardianPulse
from demo_stage import demo_reset_headers


client = TestClient(main_module.app)


def test_bounded_guardian_pulse_persists_and_reads_latest(monkeypatch):
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    journey_id = ids["journey_id"]
    generated = client.post(
        f"/api/v1/journeys/{journey_id}/plans/generate", json={"candidate_count": 1}
    )
    assert generated.status_code == 201, generated.text
    plan_id = generated.json()[0]["id"]
    assert client.post(f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select").status_code == 200
    assert client.post(f"/api/v1/journeys/{journey_id}/start").status_code == 200

    called = {"count": 0}

    def one_pulse(session, journey):
        called["count"] += 1
        now = datetime.now(timezone.utc).isoformat()
        session.add(
            GuardianPulse(
                id="pulse-test-1",
                journey_id=journey.id,
                status="COMPLETED",
                provider_key="composite-provider-mesh",
                observation_ids_json="[]",
                result_json=json.dumps({"context_watch": {"status": "NO_MATERIAL_CHANGE"}}),
                started_at=now,
                completed_at=now,
            )
        )
        session.commit()
        return {
            "pulse_id": "pulse-test-1",
            "context_watch": {"status": "NO_MATERIAL_CHANGE"},
            "guardian": {"status": "NO_ACTION"},
            "journey_id": journey.id,
        }

    monkeypatch.setattr(main_module, "pulse_journey", one_pulse)
    response = client.post(f"/api/v1/journeys/{journey_id}/guardian/pulse")
    assert response.status_code == 200, response.text
    assert response.json()["pulse_id"] == "pulse-test-1"
    assert called["count"] == 1

    # The bounded route delegates one cycle only; the persisted read remains a
    # separate server-owned projection when the real pulse implementation is used.
    latest = client.get(f"/api/v1/journeys/{journey_id}/guardian/pulse/latest")
    assert latest.status_code == 200
    assert latest.json()["journey_id"] == journey_id
    assert latest.json()["pulse"]["id"] == "pulse-test-1"
    assert latest.json()["pulse"]["result"]["context_watch"]["status"] == "NO_MATERIAL_CHANGE"
