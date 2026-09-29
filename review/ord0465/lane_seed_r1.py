"""ORD-0465 lane stack - put the five states this screen reports onto this lane's own database.

Every row below arrives through a door the product already has open (`POST /travelers`,
`POST /journeys`, `POST .../share-grants`, `POST .../revoke`, `DELETE /journeys/{id}`), so the states
the screen reports are states a real owner could produce, not shapes this file drew. Two exceptions,
both named where they are used and both because ORD-0460 was right:

  * a grant whose deadline has passed cannot be minted (the write door refuses it with
    `SHARE_GRANT_EXPIRY_IN_PAST`), so the expired link is minted with a future deadline and the row is
    then aged in place -- which is the only way that state occurs on a line at all;
  * a plan with stops in it is created by this file rather than by the solver, because the solver
    needs a city catalog this fresh database does not hold. The `places` rows carry coordinates
    because the map's whole question is "does this stop have a position", and the plan is attached
    through `journeys.active_plan_version_id` the same way plan selection does.

The marker row is the ownership proof: it is a journey id nothing else on this machine has, and the
probe below asks the listening server for it and for one that does not exist.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import sqlite3

LANE = Path("D:/moodle/_qoder_r_ord0465_20260929")
TREE = LANE / os.environ.get("LANE_TREE", "wt")
sys.path.insert(0, str(TREE / "backend"))
sys.path.insert(0, str(TREE))

BACKEND = os.environ.get("LANE_BACKEND", "http://127.0.0.1:8731/api/v1")
DB = LANE / "run" / os.environ.get("LANE_DB", "ord0465_lane.db")
OPENERS = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(method, path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(BACKEND + path, data=body, method=method)
    if body:
        request.add_header("Content-Type", "application/json")
    try:
        with OPENERS.open(request, timeout=60) as answer:
            return answer.status, json.loads(answer.read() or b"null")
    except urllib.error.HTTPError as error:
        raw = error.read()
        try:
            return error.code, json.loads(raw or b"null")
        except Exception:
            return error.code, {"unparsed": raw[:200].decode("utf-8", "replace")}


def now():
    return datetime.now(timezone.utc).isoformat()


def journey_with_plan(title, marker):
    """A trip, a plan of three stops across two days, and the places those stops name."""
    status, traveler = call("POST", "/travelers", {
        "display_name": f"ORD-0465 {marker}", "email": None,
        "locale": "zh-CN", "timezone": "Asia/Shanghai",
    })
    assert status in (200, 201), (status, traveler)
    start = datetime.now(timezone.utc) + timedelta(days=30)
    status, created = call("POST", "/journeys", {
        "traveler_id": traveler["id"], "title": title, "city_code": "CN-XIAMEN",
        "timezone": "Asia/Shanghai",
        "start_at": start.isoformat(),
        "end_at": (start + timedelta(days=1, hours=6)).isoformat(),
        "budget": {"amount_minor": 120000, "currency": "CNY"},
    })
    assert status == 201, (status, created)
    journey_id = created["id"]

    # The plan rows. Attached exactly as a selection would attach them.
    from app.db.models import Activity, Place, PlanVersion
    from app.db.session import SessionLocal

    moment = now()
    with SessionLocal() as session:
        from app.db.models import Journey

        row = session.get(Journey, journey_id)
        plan_id = str(uuid4())
        session.add(PlanVersion(
            id=plan_id, journey_id=journey_id, version_no=2, planning_mode="balanced",
            status="ACTIVE", source="REPLAN", total_cost_minor=40000, currency="CNY",
            estimated_duration_min=540, created_at=moment,
        ))
        places = []
        for index in range(3):
            place = Place(
                id=str(uuid4()), provider_key="ord0465-lane", external_id=f"{marker}-{index}",
                city_code="CN-XIAMEN",
                name=["鼓浪屿轮渡码头", "厦门大学", "沙坡尾艺术西区"][index],
                category="attraction", latitude=24.44 + index * 0.02, longitude=118.06 + index * 0.03,
                opening_hours_json="{}", tags_json="[]", metadata_json="{}", updated_at=moment,
            )
            session.add(place)
            places.append(place)
        session.flush()
        for index, place in enumerate(places, start=1):
            day = 0 if index < 3 else 1
            session.add(Activity(
                id=str(uuid4()), plan_version_id=plan_id, sequence_no=index,
                activity_type="sightseeing", title=f"stop-{index}", place_id=place.id,
                city_service_id=None,
                start_at=(start + timedelta(days=day, hours=9 + index)).isoformat(),
                end_at=(start + timedelta(days=day, hours=10 + index)).isoformat(),
                travel_from_prev_min=15, estimated_cost_minor=0, currency="CNY",
                status="PLANNED", locked=index == 3, metadata_json="{}",
                created_at=moment, updated_at=moment,
            ))
        row.active_plan_version_id = plan_id
        row.status = "PLANNED"
        session.commit()
    return journey_id


def main():
    report = {"lane_db": DB.as_posix(), "backend": BACKEND}

    good_journey = journey_with_plan("厦门两日 · 别人分享给我的那一趟", "good")
    binned_journey = journey_with_plan("会被丢进回收站的那一趟", "binned")
    no_plan_status, no_plan_traveler = call("POST", "/travelers", {
        "display_name": "ORD-0465 no-plan", "email": None,
        "locale": "zh-CN", "timezone": "Asia/Shanghai",
    })
    assert no_plan_status in (200, 201), no_plan_traveler
    edge = datetime.now(timezone.utc) + timedelta(days=40)
    status, no_plan_row = call("POST", "/journeys", {
        "traveler_id": no_plan_traveler["id"], "title": "还没有排定的那一趟",
        "city_code": "CN-XIAMEN", "timezone": "Asia/Shanghai",
        "start_at": edge.isoformat(), "end_at": (edge + timedelta(days=1)).isoformat(),
        "budget": {"amount_minor": 50000, "currency": "CNY"},
    })
    assert status == 201, no_plan_row
    no_plan_journey = no_plan_row["id"]

    def mint(journey_id, expires_in=None):
        payload = {"visibility": "LINK_READ", "created_by": "ord0465-lane"}
        if expires_in is not None:
            payload["expires_at"] = (datetime.now(timezone.utc) + expires_in).isoformat()
        code, answer = call("POST", f"/journeys/{journey_id}/share-grants", payload)
        assert code == 201, (code, answer)
        return answer["token"], answer["id"]

    tokens = {}
    tokens["valid"], tokens["valid_grant"] = mint(good_journey)
    tokens["revoked"], tokens["revoked_grant"] = mint(good_journey)
    tokens["expired"], _ = mint(good_journey, expires_in=timedelta(days=1))
    tokens["binned"], _ = mint(binned_journey)
    tokens["no_plan"], _ = mint(no_plan_journey)
    private_code, private_row = call(
        "POST", f"/journeys/{good_journey}/share-grants",
        {"visibility": "PRIVATE", "created_by": "ord0465-lane"},
    )
    assert private_code == 201, (private_code, private_row)
    tokens["private"] = private_row["token"]

    # The one door this file cannot walk: a deadline already passed cannot be minted (ORD-0460), so
    # the grant is minted alive and aged afterwards. Named as a direct store write, not a door.
    aged = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    with sqlite3.connect(DB) as store:
        store.execute(
            "UPDATE journey_share_grants SET expires_at = ? WHERE token = ?",
            (aged, tokens["expired"]),
        )
        store.commit()

    code, revoked = call("POST",
                         f"/journeys/{good_journey}/share-grants/{tokens['revoked_grant']}/revoke")
    assert code == 200, (code, revoked)
    code, binned = call("DELETE", f"/journeys/{binned_journey}")
    assert code == 204, (code, binned)

    # Ownership marker: an id no other store on this machine holds, asked for both ways.
    marker = str(uuid4())
    with sqlite3.connect(DB) as store:
        store.execute("INSERT INTO travelers (id, display_name, email, locale, timezone, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                      (marker, "ORD-0465-OWNERSHIP-MARKER", None, "zh-CN", "Asia/Shanghai", now(), now()))
        store.commit()

    hit_status, hit = call("GET", f"/travelers/{marker}")
    miss_status, _ = call("GET", f"/travelers/{str(uuid4())}")

    report.update({
        "journeys": {"with_plan": good_journey, "binned": binned_journey, "no_plan": no_plan_journey},
        "tokens": {key: (value if isinstance(value, str) else "n/a") for key, value in tokens.items()},
        "ownership_marker": marker,
        "marker_probe": {"present_status": hit_status, "present_echoes_id": hit.get("id") == marker,
                         "absent_status": miss_status},
        "urls": {
            "valid": f"/v8/shared/{tokens['valid']}",
            "revoked": f"/v8/shared/{tokens['revoked']}",
            "expired": f"/v8/shared/{tokens['expired']}",
            "binned": f"/v8/shared/{tokens['binned']}",
            "no_plan": f"/v8/shared/{tokens['no_plan']}",
            "private": f"/v8/shared/{tokens['private']}",
            "unknown": "/v8/shared/" + "z" * 32,
            "bare": "/v8/shared/",
        },
    })
    out = LANE / "run" / os.environ.get("LANE_SEED_OUT", "seed_report.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
