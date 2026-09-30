"""ORD-0504 lane seed -- two trips whose spend this lane can be judged on.

`priced` carries one fact of every class the two read routes actually answer, at amounts chosen so a
wrong sum cannot pass unnoticed: a plan leg with a known cost, a second leg the server itself calls
UNKNOWN (no amount at all), a selected-stay-free trip, a CNY transport reservation, a USD one (so a
screen that merged currencies would produce a number no door ever sent), and a commitment.

`bare` has a plan and two stops and nothing priced. It exists for the order's first counterexample:
the face must say "nothing to add up" without producing a total, because a total of 0.00 is a number
and a traveller reads a number as an answer.

Rows are made through the product's doors where a door exists (traveler, journey) and by a direct
write to THIS LANE'S OWN store where none does -- legs, reservations and commitments have no journey-
scoped write door on this tree (measured: `review/ord0504/spend_surface_r1.json` records the 404s).
That is named here because the same fact is what makes the screen's missing-class list true.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

LANE = Path("D:/moodle/_qoder_r_ord0465_20260929")
TREE = LANE / "wt"
sys.path.insert(0, str(TREE / "backend"))
sys.path.insert(0, str(TREE))

BACKEND = os.environ.get("LANE_BACKEND", "http://127.0.0.1:8731/api/v1")
OUT = LANE / "run" / "spend_seed_report.json"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(method: str, path: str, payload: dict | None = None):
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(BACKEND + path, data=body, method=method)
    if body:
        request.add_header("Content-Type", "application/json")
    with OPENER.open(request, timeout=60) as answer:
        return answer.status, json.loads(answer.read() or b"null")


def trip(title: str, marker: str, moment: str) -> tuple[str, str, list[str]]:
    """A trip with a two-stop plan attached. Returns (journey_id, plan_id, activity_ids)."""
    _, traveler = call("POST", "/travelers", {
        "display_name": f"ORD-0504 {marker}", "email": None,
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

    from app.db.models import Activity, Journey, Place, PlanVersion
    from app.db.session import SessionLocal

    # `places` carries UNIQUE(provider_key, external_id), and this file can be run twice against the
    # same store -- a per-run suffix is what keeps the second run testing the seed instead of dying on
    # that constraint (the same trap ORD-0465's seed records).
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
                id=str(uuid4()), provider_key="ord0504-lane",
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
    # Named so the arms can point their lever at the same store this file wrote, rather than guessing
    # which of this lane's databases the server is actually serving.
    report: dict[str, object] = {
        "backend": BACKEND,
        "lane_db": os.environ.get("CITYNEXUS_DATABASE_URL", ""),
    }

    bare_id, bare_plan, bare_activities = trip("什么价都没有的那一趟", "bare", moment)
    priced_id, priced_plan, priced_activities = trip("花费这一屏的那一趟", "priced", moment)
    start = datetime.now(timezone.utc) + timedelta(days=14)

    with SessionLocal() as session:
        # The bare trip gets one leg the server cannot price. Without it the empty-state arm would
        # pass on a trip with no spend row at all, and a face that turned a missing price into "0.00"
        # could still show zero lines -- the arm needs an unpriced line to be lying about.
        session.add(JourneyLeg(
            id=str(uuid4()), journey_id=bare_id, plan_version_id=bare_plan, sequence_no=1,
            from_activity_id=bare_activities[0], to_activity_id=bare_activities[1],
            from_key="stop-1", to_key="stop-2", mode="TRANSIT",
            depart_at=(start + timedelta(hours=12)).isoformat(),
            arrive_at=(start + timedelta(hours=13)).isoformat(),
            duration_min=25, distance_m=4000, cost_amount_minor=None, currency=None,
            cost_status="UNKNOWN", walking_min=6, transfers=0, reliability_score=0.6,
            weather_exposure="LOW", geometry_json="{}", crs="WGS84", provider_key="ord0504-lane",
            provenance="LANE_SEED", captured_at=moment,
        ))
        # Two legs: one the server can price, one it explicitly cannot.
        session.add(JourneyLeg(
            id=str(uuid4()), journey_id=priced_id, plan_version_id=priced_plan, sequence_no=1,
            from_activity_id=priced_activities[0], to_activity_id=priced_activities[1],
            from_key="stop-1", to_key="stop-2", mode="TRANSIT",
            depart_at=(start + timedelta(hours=11)).isoformat(),
            arrive_at=(start + timedelta(hours=12)).isoformat(),
            duration_min=30, distance_m=5000, cost_amount_minor=4500, currency="CNY",
            cost_status="KNOWN", walking_min=8, transfers=0, reliability_score=0.8,
            weather_exposure="LOW", geometry_json="{}", crs="WGS84", provider_key="ord0504-lane",
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
            weather_exposure="LOW", geometry_json="{}", crs="WGS84", provider_key="ord0504-lane",
            provenance="LANE_SEED", captured_at=moment,
        ))
        # A CNY reservation the provider confirmed at a known price...
        session.add(TransportReservation(
            id=str(uuid4()), journey_id=priced_id, draft_id=None, reservation_type="TRAIN",
            provider_key="ord0504-lane", confirmation_ref="ORD0504-CNY",
            origin_json="{}", destination_json="{}",
            scheduled_departure_at=(start + timedelta(hours=8)).isoformat(),
            scheduled_arrival_at=(start + timedelta(hours=10)).isoformat(),
            status="CONFIRMED", realtime_status="SCHEDULED", passenger_scope_json="{}",
            change_policy_json="{}", price_amount_minor=23000, currency="CNY", price_status="KNOWN",
            source_provenance="LANE_SEED", captured_at=moment,
        ))
        # ...and a USD one. A screen that added these two into one total would print a figure that
        # exists in no column of this store.
        session.add(TransportReservation(
            id=str(uuid4()), journey_id=priced_id, draft_id=None, reservation_type="FLIGHT",
            provider_key="ord0504-lane", confirmation_ref="ORD0504-USD",
            origin_json="{}", destination_json="{}",
            scheduled_departure_at=(start + timedelta(days=2, hours=6)).isoformat(),
            scheduled_arrival_at=(start + timedelta(days=2, hours=9)).isoformat(),
            status="CONFIRMED", realtime_status="SCHEDULED", passenger_scope_json="{}",
            change_policy_json="{}", price_amount_minor=9900, currency="USD", price_status="KNOWN",
            source_provenance="LANE_SEED", captured_at=moment,
        ))
        # A commitment with no reservation behind it: its own promise, its own money.
        session.add(Commitment(
            id=str(uuid4()), journey_id=priced_id, activity_id=priced_activities[0],
            kind="BOOKING", level="C3_Guaranteed", status="ACTIVE", monetary_value_minor=9900,
            monetary_value_status="KNOWN", currency="CNY", external_ref="ORD0504-COMMITMENT",
            policy_json="{}", created_at=moment, updated_at=moment,
        ))
        session.commit()

    def doors(journey_id: str) -> dict:
        """The two answers the screen is allowed to read, fetched back so the judge can be checked
        against the server rather than against this file's own arithmetic."""
        with OPENER.open(f"{BACKEND}/journeys/{journey_id}/experience", timeout=60) as answer:
            experience = json.loads(answer.read())
        with OPENER.open(f"{BACKEND}/journeys/{journey_id}/wallet", timeout=60) as answer:
            wallet = json.loads(answer.read())
        return {"experience": experience, "wallet": wallet}

    report["journeys"] = {"bare": bare_id, "priced": priced_id}
    report["answers"] = {key: doors(value) for key, value in
                         (("bare", bare_id), ("priced", priced_id))}
    report["how"] = ("traveler/journey through their doors; plan, places, activities, legs, "
                     "reservations and commitment by a direct write to this lane's own sqlite file "
                     "(no journey-scoped write door exists for those three on this tree)")
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(f"bare={bare_id} priced={priced_id}")
    print(f"report: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
