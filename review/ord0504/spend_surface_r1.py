"""ORD-0504 step 1 -- what spend facts does this server actually have, and which read carries them?

The order's first clause is a measurement, not a design step: before deciding where a trip's spend
comes from, count what the store holds and what the doors answer.  Everything below is therefore a
reading, and the script writes its own report so the claim can be re-checked without re-typing it.

Three things are separated deliberately, because conflating them is how a screen ends up inventing a
number:

  * **what the store holds** -- the money columns are inventoried from `backend/app/db/models.py`
    (14 of them, listed in the report), and each one that has a companion status column
    (`amount_status`, `cost_status`, `price_status`, `monetary_value_status`) already carries the
    server's own word for "confirmed" versus "estimated".  That vocabulary is the product's, not
    something this file invents -- `backend/app/schemas.py:776` freezes it to
    FREE_KNOWN / KNOWN / ESTIMATED / UNKNOWN.
  * **what a read route answers** -- `GET /journeys/{id}/experience` is walked key by key and every
    money-shaped path is printed with the value that came back.  A field the store holds but the
    answer does not carry is not available to a screen, and no amount of client code changes that.
  * **what no door answers at all** -- candidate journey-scoped aggregate paths are probed and their
    status codes recorded.  A 404 here is the evidence for the order's clause 2 (a named empty state
    plus a backend order) rather than an opinion about it.

Rows are created through the product's write doors wherever one exists (traveler, journey, booking)
and by a direct store write where none does (plan rows, legs, reservations, commitments -- the same
honest labelling ORD-0465's seed uses).  Nothing here reads or writes a shared store: the database is
this lane's own file and the port is :8731.

    /d/moodle/CityNexus/.venv/Scripts/python.exe review/ord0504/spend_surface_r1.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

LANE = Path("D:/moodle/_qoder_r_ord0465_20260929")
TREE = LANE / "wt"
sys.path.insert(0, str(TREE / "backend"))
sys.path.insert(0, str(TREE))

BACKEND = os.environ.get("LANE_BACKEND", "http://127.0.0.1:8731/api/v1")
OUT = TREE / "review" / "ord0504" / "spend_surface_r1.json"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

MONEY_KEY = ("cost", "amount", "price", "budget", "money", "total", "value")


def call(method: str, path: str, payload: dict | None = None):
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(BACKEND + path, data=body, method=method)
    if body:
        request.add_header("Content-Type", "application/json")
    try:
        with OPENER.open(request, timeout=60) as answer:
            raw = answer.read()
            return answer.status, json.loads(raw or b"null")
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            return error.code, json.loads(raw or b"null")
        except Exception:
            return error.code, {"unparsed": raw[:160].decode("utf-8", "replace")}


def money_paths(node, prefix="$") -> list[dict]:
    """Every path in the answer whose key says money, with the value that actually came back."""
    found: list[dict] = []
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}"
            if any(word in key.lower() for word in MONEY_KEY):
                found.append({"path": path, "value": value,
                              "kind": type(value).__name__})
            found.extend(money_paths(value, path))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            found.extend(money_paths(item, f"{prefix}[{index}]"))
    return found


def seed_trip(moment: str) -> dict:
    """A trip with one of each kind of spend fact, at amounts that cannot be confused."""
    status, traveler = call("POST", "/travelers", {
        "display_name": "ORD-0504 probe", "email": None,
        "locale": "zh-CN", "timezone": "Asia/Shanghai",
    })
    assert status in (200, 201), (status, traveler)
    start = datetime.now(timezone.utc) + timedelta(days=21)
    status, journey = call("POST", "/journeys", {
        "traveler_id": traveler["id"], "title": "花费这一屏的探针趟", "city_code": "CN-XIAMEN",
        "timezone": "Asia/Shanghai", "start_at": start.isoformat(),
        "end_at": (start + timedelta(days=2)).isoformat(),
        "budget": {"amount_minor": 300000, "currency": "CNY"},
    })
    assert status == 201, (status, journey)
    journey_id = journey["id"]

    from app.db.models import Activity, Commitment, JourneyLeg, Place, PlanVersion
    from app.db.models import TransportReservation
    from app.db.session import SessionLocal

    batch = str(uuid4())
    with SessionLocal() as session:
        from app.db.models import Journey

        row = session.get(Journey, journey_id)
        plan = PlanVersion(
            id=str(uuid4()), journey_id=journey_id, version_no=1, planning_mode="balanced",
            status="ACTIVE", source="INITIAL", total_cost_minor=20000, currency="CNY",
            estimated_duration_min=600, created_at=moment,
        )
        session.add(plan)
        activity_ids = []
        for index in range(1, 4):
            place = Place(
                id=str(uuid4()), provider_key="ord0504-probe", external_id=f"ord0504-{batch}-{index}",
                city_code="CN-XIAMEN", name=f"探针地点 {index}", category="attraction",
                latitude=24.44 + index / 100, longitude=118.06 + index / 100,
                opening_hours_json="{}", tags_json="[]", metadata_json="{}", updated_at=moment,
            )
            session.add(place)
            session.flush()
            activity = Activity(
                id=str(uuid4()), plan_version_id=plan.id, sequence_no=index,
                activity_type="visit", title=f"stop-{index}", place_id=place.id,
                city_service_id=None,
                start_at=(start + timedelta(days=(index - 1) // 2, hours=8 + index)).isoformat(),
                end_at=(start + timedelta(days=(index - 1) // 2, hours=9 + index)).isoformat(),
                travel_from_prev_min=15,
                # Three different amounts on purpose: one ordinary, one free (0), one larger. A
                # screen that prints a number it did not read would show the same figure twice.
                estimated_cost_minor=[12000, 0, 8000][index - 1],
                currency="CNY", status="PLANNED", locked=False, metadata_json="{}",
                created_at=moment, updated_at=moment,
            )
            session.add(activity)
            activity_ids.append(activity.id)
        row.active_plan_version_id = plan.id
        row.status = "PLANNED"
        # Legs: one with a known cost, one the server itself calls UNKNOWN with no amount at all.
        for index, (cost, status_word) in enumerate([(4500, "KNOWN"), (None, "UNKNOWN")], start=1):
            session.add(JourneyLeg(
                id=str(uuid4()), journey_id=journey_id, plan_version_id=plan.id, sequence_no=index,
                from_activity_id=activity_ids[index - 1], to_activity_id=activity_ids[index],
                from_key=f"stop-{index}", to_key=f"stop-{index + 1}", mode="TRANSIT",
                depart_at=(start + timedelta(days=index - 1, hours=10)).isoformat(),
                arrive_at=(start + timedelta(days=index - 1, hours=11)).isoformat(),
                duration_min=30, distance_m=5000, cost_amount_minor=cost,
                currency="CNY" if cost is not None else None, cost_status=status_word,
                walking_min=8, transfers=0, reliability_score=0.8, weather_exposure="LOW",
                geometry_json="{}", crs="WGS84", provider_key="ord0504-probe",
                provenance="STORE_WRITTEN_PROBE", captured_at=moment,
            ))
        # A commitment (the owner's own promise) and a transport reservation (a booked seat).
        # `kind` and `level` are the store's own vocabularies -- `backend/db/schema.sql:232` and :233
        # CHECK them -- so the probe uses a legal value rather than inventing one.
        session.add(Commitment(
            id=str(uuid4()), journey_id=journey_id, activity_id=activity_ids[0], kind="BOOKING",
            level="C3_Guaranteed", status="ACTIVE", monetary_value_minor=9900,
            monetary_value_status="KNOWN", currency="CNY", external_ref=f"ord0504-{batch}",
            policy_json="{}", created_at=moment, updated_at=moment,
        ))
        session.add(TransportReservation(
            id=str(uuid4()), journey_id=journey_id, draft_id=None, reservation_type="TRAIN",
            provider_key="ord0504-probe", confirmation_ref=f"CONF-{batch[:8]}",
            origin_json="{}", destination_json="{}",
            scheduled_departure_at=(start + timedelta(hours=9)).isoformat(),
            scheduled_arrival_at=(start + timedelta(hours=11)).isoformat(),
            status="CONFIRMED", realtime_status="SCHEDULED", passenger_scope_json="{}",
            change_policy_json="{}", price_amount_minor=23000, currency="CNY",
            price_status="KNOWN", source_provenance="STORE_WRITTEN_PROBE", captured_at=moment,
        ))
        session.commit()
    return {"journey_id": journey_id, "plan_id": plan.id, "activity_ids": activity_ids}


def main() -> int:
    moment = datetime.now(timezone.utc).isoformat()
    report: dict[str, object] = {"backend": BACKEND}

    trip = seed_trip(moment)
    report["seed"] = {
        "journey_id": trip["journey_id"],
        "how": "traveler/journey through their doors; plan+places+activities, legs, commitment and "
               "transport reservation by a direct write to this lane's own store (no door exists for "
               "those three -- named, not hidden); booking through POST /journeys/{id}/bookings",
    }

    booking_status, booking = call(
        "POST", f"/journeys/{trip['journey_id']}/bookings",
        {"activity_id": trip["activity_ids"][1], "provider_key": "mock-booking"},
    )
    report["booking_door"] = {
        "http_status": booking_status,
        "answer": booking if booking_status < 300 else str(booking)[:200],
    }

    experience_status, experience = call("GET", f"/journeys/{trip['journey_id']}/experience")
    report["experience"] = {
        "http_status": experience_status,
        "money_paths": money_paths(experience) if experience_status < 300 else [],
    }
    journey_status, journey_body = call("GET", f"/journeys/{trip['journey_id']}")
    report["journey_read"] = {
        "http_status": journey_status,
        "money_paths": money_paths(journey_body) if journey_status < 300 else [],
    }

    # The absence half: is there any journey-scoped door that already answers a trip's spend?
    probes = {}
    for candidate in (
        f"/journeys/{trip['journey_id']}/spend", f"/journeys/{trip['journey_id']}/costs",
        f"/journeys/{trip['journey_id']}/expenses", f"/journeys/{trip['journey_id']}/budget",
        f"/journeys/{trip['journey_id']}/bookings", f"/journeys/{trip['journey_id']}/legs",
        f"/journeys/{trip['journey_id']}/reservations", f"/journeys/{trip['journey_id']}/commitments",
        f"/journeys/{trip['journey_id']}/transactions",
    ):
        probes[candidate] = call("GET", candidate)[0]
    report["aggregate_door_probe_http_status"] = probes

    # What the store holds, read off the model rather than from memory.
    import re

    import app.db.models as models

    columns = []
    for name in dir(models):
        item = getattr(models, name)
        if hasattr(item, "__table__") and getattr(item, "__tablename__", None):
            for column in item.__table__.columns:
                if column.name.endswith("_minor"):
                    columns.append({"table": item.__tablename__, "column": column.name,
                                    "nullable": bool(column.nullable)})
    report["store_money_columns"] = sorted(columns, key=lambda c: (c["table"], c["column"]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({key: value for key, value in report.items() if key != "store_money_columns"},
                     ensure_ascii=False, indent=2)[:3000])
    print(f"\nreport: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
