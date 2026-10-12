"""ORD-0603 wiring probe (scratch tree only): does the landed contract change what the door says?

Two facts are written on the same trip pair -- one with the provider layer's own live-capture
provenance, one synthetic.  The contract's `fact_is_eligible_for_live_readiness` must call the first
eligible and the second not, through the real door, not through a mock.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.models import MobilityFact, Place
from app.db.session import SessionLocal
from app.main import app
from app.replanning.provider_snapshots import LIVE_PROVIDER_CAPTURE
from demo_stage import demo_reset_headers  # noqa: E402  (ORD-0389)

client = TestClient(app)
TZ = timezone(timedelta(hours=8))
CITY_CODE = "CNX-DEMO"
DOOR = "/api/v1/journeys/{journey_id}/mobility"
KEY = "jiazagong-0603-probe"


def _journey() -> str:
    return client.post("/api/v1/demo/reset", headers=demo_reset_headers()).json()["journey_id"]


def _pair() -> tuple[str, str]:
    from sqlalchemy import select

    with SessionLocal() as session:
        ids = list(session.scalars(select(Place.id).where(Place.city_code == CITY_CODE).order_by(Place.id)).all())
    assert len(ids) >= 2, f"SETUP 失败：{CITY_CODE} 在种子里不足 2 行"
    return str(ids[0]), str(ids[1])


def _fact(journey_id: str, origin: str, destination: str, mode: str, *, provenance: str, provider: str) -> None:
    stamp = datetime.now(TZ).isoformat()
    with SessionLocal() as session:
        session.add(
            MobilityFact(
                id=f"{KEY}-{journey_id}-{mode}",
                journey_id=journey_id,
                option_id=None,
                from_key=origin,
                to_key=destination,
                mode=mode,
                duration_min=17,
                distance_m=1400,
                cost_amount_minor=None,
                currency=None,
                cost_status="UNKNOWN",
                walking_min=17,
                transfers=0,
                weather_exposure="NONE",
                reliability_score=0.9,
                provider_key=provider,
                provenance=provenance,
                geometry_json="{}",
                crs="WGS84",
                paid_mode=False,
                evidence_json="{}",
                captured_at=stamp,
                expires_at=None,
            )
        )
        session.commit()


def test_the_door_now_says_which_route_truth_may_drive_a_leave_by():
    with SessionLocal() as session:
        session.execute(delete(MobilityFact).where(MobilityFact.provider_key.like(f"{KEY}%")))
        session.commit()
    journey_id = _journey()
    first, second = _pair()
    _fact(journey_id, first, second, "WALK", provenance=LIVE_PROVIDER_CAPTURE, provider="jiazagong-0603-live")
    _fact(journey_id, first, second, "AUTO", provenance="SYNTHETIC_FIXTURE", provider="jiazagong-0603-live")
    _fact(journey_id, first, second, "TRANSIT", provenance=LIVE_PROVIDER_CAPTURE, provider="mock-emulator")
    answer = client.get(DOOR.format(journey_id=journey_id))
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert "live_readiness_eligible" in body["modes"][0], "候选接线没生效：这一枚键没出现在响应里"
    by = {item["mode"]: item for item in body["modes"]}
    print("\nJZ0603-PROBE  door keys:", sorted(body))
    for mode in ("WALK", "AUTO", "TRANSIT"):
        item = by[mode]
        print("JZ0603-PROBE  %-8s provenance=%-28s provider=%-22s duration=%s eligible=%s"
              % (mode, item["provenance"], item["provider_key"], item["duration_min"],
                 item["live_readiness_eligible"]))
    assert by["WALK"]["live_readiness_eligible"] is True
    assert by["AUTO"]["live_readiness_eligible"] is False       # synthetic provenance
    assert by["TRANSIT"]["live_readiness_eligible"] is False    # mock provider, same duration
    with SessionLocal() as session:
        session.execute(delete(MobilityFact).where(MobilityFact.provider_key.like(f"{KEY}%")))
        session.commit()
