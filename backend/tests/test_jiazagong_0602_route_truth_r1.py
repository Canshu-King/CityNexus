"""ORD-0602 甲半: the recovery door now says where the route timing came from.

One door call per source class, in the same run, against the line's own demo fixtures:
  · the leg's TRANSIT fact left as the demo wrote it;
  · the same row re-stamped with the provider layer's own live-capture provenance;
  · the same row re-stamped as SYNTHETIC_FIXTURE.
The two contract readings must differ across those cases while every decision field stays identical --
that is what "report the source, do not change the outcome" has to mean in code.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.models import MobilityFact
from app.db.session import SessionLocal
from app.main import app
from app.replanning.provider_snapshots import LIVE_PROVIDER_CAPTURE
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(app)

DECISION_KEYS = ("decision", "executed", "after_mode", "post_action_gate",
                 "protected_commitments_preserved", "reason_codes")


def _journey_with_option(title: str) -> tuple[str, str]:
    ids = client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()
    create = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": ids["traveler_id"],
            "title": title,
            "city_code": "CN-TIANJIN",
            "timezone": "Asia/Shanghai",
            "start_at": "2026-10-09T18:00:00+08:00",
            "end_at": "2026-10-11T15:00:00+08:00",
            "budget": {"amount_minor": 120000, "currency": "CNY"},
            "stay_budget": {"amount_minor": 70000, "currency": "CNY"},
            "party_size": 2,
            "occupancy": {"adults": 2, "rooms": 1},
            "arrival_anchor": {"at": "2026-10-09T18:00:00+08:00", "location": "Tianjin West Station"},
            "departure_anchor": {
                "at": "2026-10-11T15:00:00+08:00",
                "location": "Tianjin Binhai Airport",
            },
        },
    )
    journey_id = create.json()["id"]
    policy = client.put(
        f"/api/v1/travelers/{ids['traveler_id']}/agent-policy",
        json={
            "mode": "AUTONOMOUS",
            "auto_accept_replan": True,
            "max_auto_replan_cost_delta_minor": 5000,
            "max_auto_loss_minor": 0,
            "max_auto_schedule_drift_min": 20,
            "allowed_activity_types": ["transport"],
            "allowed_booking_types": [],
            "protected_commitment_levels": ["C3_Guaranteed", "C4_Anchored"],
            "allow_auto_commitment_management": False,
            "allow_auto_when_provider_degraded": False,
            "allow_auto_on_critical_event": False,
        },
    )
    assert policy.status_code == 200, policy.text
    generated = client.post(f"/api/v1/journeys/{journey_id}/stay-options/generate")
    return journey_id, generated.json()["top_k"][0]["id"]


def _restamp(journey_id: str, provenance: str, provider_key: str) -> int:
    with SessionLocal() as session:
        rows = session.scalars(
            select(MobilityFact).where(
                MobilityFact.journey_id == journey_id, MobilityFact.mode == "TRANSIT"
            )
        ).all()
        for row in rows:
            row.provenance = provenance
            row.provider_key = provider_key
        session.commit()
        return len(rows)


def _recover(journey_id: str, option_id: str) -> dict:
    answer = client.post(
        f"/api/v1/journeys/{journey_id}/stay-options/{option_id}/autopilot/recover",
        json={"state": "RAIN"},
    )
    assert answer.status_code == 200, answer.text
    return answer.json()


def _decisions(body: dict) -> dict:
    return {key: body[key] for key in DECISION_KEYS}


def test_the_recovery_door_reports_the_route_source_and_changes_no_decision() -> None:
    journey_id, option_id = _journey_with_option("ORD-0602 route truth, live provider")
    stamped = _restamp(journey_id, LIVE_PROVIDER_CAPTURE, "jiazagong-0602-live")
    assert stamped > 0, "SETUP 失败：这趟没有 TRANSIT 事实可改，这条门测不到东西"
    live = _recover(journey_id, option_id)

    journey_id2, option_id2 = _journey_with_option("ORD-0602 route truth, synthetic")
    assert _restamp(journey_id2, "SYNTHETIC_FIXTURE", "jiazagong-0602-synthetic") > 0
    synthetic = _recover(journey_id2, option_id2)

    print("\nJZ0602 live      :", live["route_truth"])
    print("JZ0602 synthetic   :", synthetic["route_truth"])
    print("JZ0602 decisions equal:", _decisions(live) == _decisions(synthetic), _decisions(live))

    for body in (live, synthetic):
        truth = body.get("route_truth")
        assert truth, "响应里没有 route_truth：甲半没接上"
        assert truth["capture_status"] == "COMPLETED", truth
        assert truth["policy_version"] == "r41-route-truth-v1", truth

    assert live["route_truth"]["eligible_for_live_readiness"] is True, live["route_truth"]
    assert live["route_truth"]["capture_outcome"] == "ROUTE_READY", live["route_truth"]
    assert synthetic["route_truth"]["eligible_for_live_readiness"] is False, synthetic["route_truth"]
    assert synthetic["route_truth"]["capture_outcome"] == "ROUTE_PROVIDER_DEGRADED", synthetic["route_truth"]

    # 甲半的硬要求：来源说明不得改这次的结果。同一道门、同一种天气、只差事实的出处。
    assert _decisions(live) == _decisions(synthetic), (
        "接上来源说明之后放行结果变了：\nlive=%s\nsynthetic=%s" % (_decisions(live), _decisions(synthetic))
    )
    assert live["executed"] is True and synthetic["executed"] is True


def test_the_recovery_door_still_refuses_without_a_fact_for_the_mode() -> None:
    """The 422 path is untouched: with no TRANSIT fact at all the door still refuses the same way."""
    journey_id, option_id = _journey_with_option("ORD-0602 route truth, no fact")
    with SessionLocal() as session:
        session.execute(
            delete(MobilityFact).where(
                MobilityFact.journey_id == journey_id, MobilityFact.mode == "TRANSIT"
            )
        )
        session.commit()
    answer = client.post(
        f"/api/v1/journeys/{journey_id}/stay-options/{option_id}/autopilot/recover",
        json={"state": "RAIN"},
    )
    print("\nJZ0602 no-fact door answer:", answer.status_code, answer.json())
    assert answer.status_code == 422, answer.text
    envelope = answer.json()["error"]
    assert "TRANSIT is unavailable for this captured leg" in envelope["message"], envelope
