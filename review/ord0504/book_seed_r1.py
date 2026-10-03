"""ORD-0504 book-screen hand -- put the fact shapes the 预订 tab answers for, into THIS LANE'S store.

Same store the spend hand reads (`run/ord0465_lane.db`), same disclosure the spend seed carries: a
reservation, a booking and a commitment have no journey-scoped WRITE door on this tree, so those rows
are written directly into this lane's sqlite file. Everything the arms then assert is read back out of
the two doors the screen is actually allowed to read (`GET /journeys/{id}/experience` and
`GET /journeys/{id}/wallet`), never out of this script's memory.

Rows deliberately cover the shapes the 预订 tab has to answer for, and the shape nobody has tested:

  * a reservation that the server calls CONFIRMED and that also carries a commitment;
  * a CONFIRMED reservation with no commitment behind it;
  * a reservation whose server status is the draft word PENDING -- the card must not call that 已确认;
  * a reservation with no price at all (`price_amount_minor` NULL, `price_status` UNKNOWN);
  * a JPY reservation: `frontend/src/lib/money.ts:1` gives JPY no minor fraction, so 4800 minor is 4,800 yen,
    and anything that divides every currency by 100 is 100x off on exactly this row;
  * a commitment priced and marked mock- (the 模拟承诺 word), and a commitment whose price is unknown.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

LANE = Path("D:/moodle/_qoder_r_ord0465_20260929")
TREE = LANE / "wt"
sys.path.insert(0, str(TREE / "backend"))
sys.path.insert(0, str(TREE))

BACKEND = os.environ.get("LANE_BACKEND", "http://127.0.0.1:8731/api/v1")
OUT = LANE / "run" / "book_seed_report.json"
import urllib.request  # noqa: E402

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(method: str, path: str, payload: dict | None = None):
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(BACKEND + path, data=body, method=method)
    if body:
        request.add_header("Content-Type", "application/json")
    with OPENER.open(request, timeout=60) as answer:
        return answer.status, json.loads(answer.read() or b"null")


def main() -> int:
    from app.db.session import SessionLocal
    from app.db.models import Commitment, PlanVersion, TransportReservation

    # the product's own doors make the traveler and the journey; only the money rows are written directly
    status, traveler = call("POST", "/travelers", {
        "display_name": "ORD-0504 预订面", "email": None,
        "locale": "zh-CN", "timezone": "Asia/Shanghai",
    })
    status, journey = call("POST", "/journeys", {
        "traveler_id": traveler["id"], "title": "预订面的事实形状", "city_code": "CN-XIAMEN",
        "timezone": "Asia/Shanghai",
        "start_at": "2026-11-05T09:00:00+08:00", "end_at": "2026-11-06T18:00:00+08:00",
        "budget": {"amount_minor": 200000, "currency": "CNY"},
    })
    moment = datetime(2026, 11, 5, 9, 0, tzinfo=timezone(timedelta(hours=8)))

    session = SessionLocal()
    reservations: list[dict] = []
    commitments: list[dict] = []
    try:
        plan = PlanVersion(id=str(uuid4()), journey_id=journey["id"], version_no=1,
                           planning_mode="balanced", status="ACTIVE", source="INITIAL",
                           total_cost_minor=20000, currency="CNY", estimated_duration_min=540, created_at=moment)
        session.add(plan)
        session.flush()
        shapes = [
            {"label": "confirmed_with_commitment", "status": "CONFIRMED", "price": 23000,
             "currency": "CNY", "price_status": "KNOWN", "commit": True, "ref": "CA-9F31"},
            {"label": "confirmed_no_commitment", "status": "CONFIRMED", "price": 9900,
             "currency": "USD", "price_status": "KNOWN", "commit": False, "ref": "MU-2270"},
            # JPY beside CNY on purpose: `frontend/src/lib/money.ts:1` gives it zero decimals, so the two
            # money systems print the same glyph `¥` while the wallet answered two different ISO codes.
            {"label": "yen_row_same_glyph", "status": "CONFIRMED", "price": 4800,
             "currency": "JPY", "price_status": "KNOWN", "commit": False, "ref": "JP-4800"},
            {"label": "pending_row", "status": "PENDING", "price": 1500, "currency": "CNY",
             "price_status": "KNOWN", "commit": False, "ref": None},
            {"label": "unpriced_row", "status": "CONFIRMED", "price": None, "currency": None,
             "price_status": "UNKNOWN", "commit": False, "ref": "NO-PRICE"},
        ]
        for offset, shape in enumerate(shapes):
            reservation = TransportReservation(
                id=str(uuid4()), journey_id=journey["id"], draft_id=None,
                reservation_type="FLIGHT" if offset % 2 == 0 else "TRAIN",
                provider_key="ord0504-book-lane", confirmation_ref=shape["ref"],
                origin_json='{"name":"厦门高崎"}', destination_json='{"name":"上海虹桥"}',
                scheduled_departure_at=(moment + timedelta(hours=2 + offset)).isoformat(),
                scheduled_arrival_at=(moment + timedelta(hours=4 + offset)).isoformat(),
                status=shape["status"], realtime_status="SCHEDULED", passenger_scope_json="{}",
                change_policy_json="{}", price_amount_minor=shape["price"],
                currency=shape["currency"], price_status=shape["price_status"],
                source_provenance="lane-seed", captured_at=moment.isoformat(),
            )
            session.add(reservation)
            session.flush()
            item = {"label": shape["label"], "id": reservation.id, "status": reservation.status,
                    "price_amount_minor": reservation.price_amount_minor,
                    "currency": reservation.currency, "price_status": reservation.price_status,
                    "confirmation_ref": reservation.confirmation_ref, "commitment_id": None}
            if shape["commit"]:
                commitment = Commitment(
                    id=str(uuid4()), journey_id=journey["id"], activity_id=None, kind="BOOKING",
                    level="C3_Guaranteed", status="ACTIVE",
                    monetary_value_minor=shape["price"], monetary_value_status="KNOWN",
                    currency=shape["currency"], created_at=moment, updated_at=moment,
                    external_ref="mock-booking:" + reservation.id[:8],
                    policy_json=json.dumps({"fixed_schedule": True,
                                            "scheduled_start_at": reservation.scheduled_departure_at,
                                            "scheduled_end_at": reservation.scheduled_arrival_at,
                                            "semantic_key": "lane-mock"}),
                )
                session.add(commitment)
                session.flush()
                reservation.commitment_id = commitment.id
                item["commitment_id"] = commitment.id
                commitments.append({"id": commitment.id, "status": commitment.status,
                                    "monetary_value_minor": commitment.monetary_value_minor,
                                    "monetary_value_status": commitment.monetary_value_status,
                                    "external_ref": commitment.external_ref, "currency": commitment.currency})
            reservations.append(item)

        # a commitment whose price the server never learned: the card must say so, not print 0.00
        unknown = Commitment(
            id=str(uuid4()), journey_id=journey["id"], activity_id=None, kind="BOOKING",
            level="C2_Reserved", status="ACTIVE", monetary_value_minor=None,
            monetary_value_status="UNKNOWN", currency="CNY", external_ref="lane-plain-ref",
            created_at=moment, updated_at=moment,
            policy_json=json.dumps({"fixed_schedule": False}),
        )
        session.add(unknown)
        session.flush()
        commitments.append({"id": unknown.id, "status": unknown.status,
                            "monetary_value_minor": None, "monetary_value_status": "UNKNOWN",
                            "external_ref": unknown.external_ref, "currency": None})
        session.commit()
    finally:
        session.close()

    doors = {}
    for door in ("experience", "wallet"):
        code, body = call("GET", "/%s/%s/%s" % ("journeys", journey["id"], door))
        doors[door] = {"http_status": code, "body": body}

    OUT.write_text(json.dumps({
        "backend": BACKEND,
        "lane_db": os.environ.get("CITYNEXUS_DATABASE_URL", ""),
        "journey_id": journey["id"],
        "written": {"reservations": reservations, "commitments": commitments},
        "doors": doors,
        "how": "journey and traveler through the product's own doors; reservations and commitments by "
               "a direct write to this lane's store, because no journey-scoped write door exists for "
               "them (measured in review/ord0504/spend_surface_r1.json)",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("journey=%s" % journey["id"])
    print("reservations=%d commitments=%d" % (len(reservations), len(commitments)))
    print("report: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
