"""ORD-0504 follow-on (lane 6a150e1e) -- build the same two spend worlds on MY store, for the day24 screen reading.

The world is theirs by recipe, not by editing their instrument: the landed seed
`review/ord0504/spend_seed_r1.py` is the shape this order is judged on (`priced` carries one fact of
every class the two read routes answer, `bare` carries a single unpriced leg), and I keep every amount
identical so my screen readings are comparable with the numbers already in the ledger. Only three things
change here: the tree on `sys.path` is THIS lane's worktree, the sqlite file is this hand's own fresh
store, and the report lands next to my other receipts.

Amounts carried over verbatim: priced trip = one KNOWN CNY leg 4500, one UNKNOWN leg (no amount), a
CONFIRMED CNY reservation 23000, a CONFIRMED USD reservation 9900, one CNY commitment 9900; bare trip =
one UNKNOWN leg only. Declared budget on both trips is 300000 CNY.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

TREE = Path("D:/moodle/_qoder_n2b_ord0466_20260929/wt")
DB = Path("D:/moodle/_qoder_6a_ord0531_20261001/spend_day24.db")
BACKEND = os.environ.get("LANE_BACKEND", "http://127.0.0.1:8021/api/v1")
OUT = Path("D:/moodle/_qoder_6a_ord0531_20261001/spend_seed_day24_report.json")
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{DB.as_posix()}"
os.environ["CITYNEXUS_DEMO_MODE"] = "true"
sys.path.insert(0, str(TREE / "backend"))
sys.path.insert(0, str(TREE))


def call(method: str, path: str, payload: dict | None = None):
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(BACKEND + path, data=body, method=method)
    if body:
        request.add_header("Content-Type", "application/json")
    with OPENER.open(request, timeout=90) as answer:
        return answer.status, json.loads(answer.read() or b"null")


def trip(title: str, marker: str, moment: str):
    from app.db.models import Activity, Journey, Place, PlanVersion
    from app.db.session import SessionLocal

    _, traveler = call("POST", "/travelers", {
        "display_name": f"ORD-0504 6a150e1e {marker}", "email": None,
        "locale": "zh-CN", "timezone": "Asia/Shanghai",
    })
    start = datetime.now(timezone.utc) + timedelta(days=14)
    status, journey = call("POST", "/journeys", {
        "traveler_id": traveler["id"], "title": title, "city_code": "CN-XIAMEN",
        "timezone": "Asia/Shanghai", "start_at": start.isoformat(),
        "end_at": (start + timedelta(days=2)).isoformat(),
        "budget": {"amount_minor": 300000, "currency": "CNY"},
    })
    assert status == 201, (status, journey)

    batch = str(uuid4())
    with SessionLocal() as session:
        row = session.get(Journey, journey["id"])
        plan = PlanVersion(
            id=str(uuid4()), journey_id=journey["id"], version_no=1, planning_mode="balanced",
            status="ACTIVE", source="INITIAL", total_cost_minor=20000, currency="CNY",
            estimated_duration_min=600, created_at=moment,
        )
        session.add(plan)
        activity_ids = []
        for index in (1, 2):
            place = Place(
                id=str(uuid4()), provider_key="ord0504-6a150e1e",
                external_id=f"ord0504-{marker}-{batch[:8]}-{index}",
                city_code="CN-XIAMEN", name=f"花费探针地点 {index}", category="attraction",
                latitude=24.44 + index / 100, longitude=118.06 + index / 100,
                opening_hours_json="{}", tags_json="[]", metadata_json="{}", updated_at=moment,
            )
            session.add(place)
            session.flush()
            activity = Activity(
                id=str(uuid4()), plan_version_id=plan.id, sequence_no=index, activity_type="visit",
                title=f"stop-{index}", place_id=place.id, city_service_id=None,
                start_at=(start + timedelta(hours=9 + index)).isoformat(),
                end_at=(start + timedelta(hours=10 + index)).isoformat(),
                travel_from_prev_min=15, estimated_cost_minor=12000 * index, currency="CNY",
                status="PLANNED", locked=False, metadata_json="{}", created_at=moment, updated_at=moment,
            )
            session.add(activity)
            activity_ids.append(activity.id)
        row.active_plan_version_id = plan.id
        row.status = "PLANNED"
        session.commit()
        return journey["id"], plan.id, activity_ids


def main() -> int:
    from app.db.models import Commitment, JourneyLeg, TransportReservation
    from app.db.session import SessionLocal

    moment = datetime.now(timezone.utc).isoformat()
    bare_id, bare_plan, bare_activities = trip("什么价都没有的那一趟", "bare", moment)
    priced_id, priced_plan, priced_activities = trip("花费这一屏的那一趟", "priced", moment)
    start = datetime.now(timezone.utc) + timedelta(days=14)

    with SessionLocal() as session:
        session.add(JourneyLeg(
            id=str(uuid4()), journey_id=bare_id, plan_version_id=bare_plan, sequence_no=1,
            from_activity_id=bare_activities[0], to_activity_id=bare_activities[1],
            from_key="stop-1", to_key="stop-2", mode="TRANSIT",
            depart_at=(start + timedelta(hours=12)).isoformat(),
            arrive_at=(start + timedelta(hours=13)).isoformat(),
            duration_min=25, distance_m=4000, cost_amount_minor=None, currency=None,
            cost_status="UNKNOWN", walking_min=6, transfers=0, reliability_score=0.6,
            weather_exposure="LOW", geometry_json="{}", crs="WGS84", provider_key="ord0504-6a150e1e",
            provenance="LANE_SEED", captured_at=moment,
        ))
        session.add(JourneyLeg(
            id=str(uuid4()), journey_id=priced_id, plan_version_id=priced_plan, sequence_no=1,
            from_activity_id=priced_activities[0], to_activity_id=priced_activities[1],
            from_key="stop-1", to_key="stop-2", mode="TRANSIT",
            depart_at=(start + timedelta(hours=11)).isoformat(),
            arrive_at=(start + timedelta(hours=12)).isoformat(),
            duration_min=30, distance_m=5000, cost_amount_minor=4500, currency="CNY",
            cost_status="KNOWN", walking_min=8, transfers=0, reliability_score=0.8,
            weather_exposure="LOW", geometry_json="{}", crs="WGS84", provider_key="ord0504-6a150e1e",
            provenance="LANE_SEED", captured_at=moment,
        ))
        session.add(JourneyLeg(
            id=str(uuid4()), journey_id=priced_id, plan_version_id=priced_plan, sequence_no=2,
            from_activity_id=priced_activities[1], to_activity_id=None,
            from_key="stop-2", to_key="hotel", mode="TRANSIT",
            depart_at=(start + timedelta(days=1, hours=9)).isoformat(),
            arrive_at=(start + timedelta(days=1, hours=10)).isoformat(),
            duration_min=40, distance_m=9000, cost_amount_minor=None, currency=None,
            cost_status="UNKNOWN", walking_min=10, transfers=1, reliability_score=0.7,
            weather_exposure="LOW", geometry_json="{}", crs="WGS84", provider_key="ord0504-6a150e1e",
            provenance="LANE_SEED", captured_at=moment,
        ))
        session.add(TransportReservation(
            id=str(uuid4()), journey_id=priced_id, draft_id=None, reservation_type="TRAIN",
            provider_key="ord0504-6a150e1e", confirmation_ref="ORD0504-CNY",
            origin_json="{}", destination_json="{}",
            scheduled_departure_at=(start + timedelta(hours=8)).isoformat(),
            scheduled_arrival_at=(start + timedelta(hours=10)).isoformat(),
            status="CONFIRMED", realtime_status="SCHEDULED", passenger_scope_json="{}",
            change_policy_json="{}", price_amount_minor=23000, currency="CNY", price_status="KNOWN",
            source_provenance="LANE_SEED", captured_at=moment,
        ))
        session.add(TransportReservation(
            id=str(uuid4()), journey_id=priced_id, draft_id=None, reservation_type="FLIGHT",
            provider_key="ord0504-6a150e1e", confirmation_ref="ORD0504-USD",
            origin_json="{}", destination_json="{}",
            scheduled_departure_at=(start + timedelta(days=2, hours=6)).isoformat(),
            scheduled_arrival_at=(start + timedelta(days=2, hours=9)).isoformat(),
            status="CONFIRMED", realtime_status="SCHEDULED", passenger_scope_json="{}",
            change_policy_json="{}", price_amount_minor=9900, currency="USD", price_status="KNOWN",
            source_provenance="LANE_SEED", captured_at=moment,
        ))
        session.add(Commitment(
            id=str(uuid4()), journey_id=priced_id, activity_id=priced_activities[0],
            kind="BOOKING", level="C3_Guaranteed", status="ACTIVE", monetary_value_minor=9900,
            monetary_value_status="KNOWN", currency="CNY", external_ref="ORD0504-COMMITMENT",
            policy_json="{}", created_at=moment, updated_at=moment,
        ))
        session.commit()

    def doors(journey_id: str) -> dict:
        with OPENER.open(f"{BACKEND}/journeys/{journey_id}/experience", timeout=90) as answer:
            experience = json.loads(answer.read())
        with OPENER.open(f"{BACKEND}/journeys/{journey_id}/wallet", timeout=90) as answer:
            wallet = json.loads(answer.read())
        return {"experience": experience, "wallet": wallet}

    report = {
        "backend": BACKEND,
        "lane_db": os.environ["CITYNEXUS_DATABASE_URL"],
        "journeys": {"bare": bare_id, "priced": priced_id},
        "answers": {key: doors(value) for key, value in (("bare", bare_id), ("priced", priced_id))},
        "recipe_source": "review/ord0504/spend_seed_r1.py (amounts copied verbatim; tree/db/report path are this lane's)",
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(f"bare={bare_id}")
    print(f"priced={priced_id}")
    print(f"report: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
