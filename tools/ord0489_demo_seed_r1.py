#!/usr/bin/env python3
"""ORD-0489 · make the demo surface big enough to demo.

One re-runnable command builds the board this product's screens were never able to show with a
single stored journey: three journeys (two multi-day, one empty), one city whose catalogue is
genuinely empty, and real places taken from the product's own provider channel.

Everything is written through public doors on a running backend.  There is no SQL here, no
`demo/reset`, and no invented place name: `POST /real-city/discover` with `mode=live` is the only
thing that can put a row into `places`, and the run aborts with the provider's own reason if the
live channel did not answer.  A REPLAY fallback is *not* supply - the fallback is what this build
returns when the provider timed out, and shipping it would put names on a screen that no provider
ever said.

Board produced (all counts are read back after the writes, never assumed):

  traveler   1  - one demo traveller
  journeys   3  - CN-TIANJIN 3 days, CN-BEIJING 4 days, CN-FUZHOU 2 days (empty)
  places     >=1 per supplied city, 0 for CN-FUZHOU
  plans      2 selected (one per multi-day journey)
  checkins   3 on the Tianjin trip (2 places + 1 activity) - the footprint rows
  share      1 live grant, 1 revoked grant, 1 recycle-binned trip, plus an unknown-token read

Usage
-----
  # 1. start a private backend on a lane port with a FRESH database (nothing here touches a
  #    shared store; the ports 8000/4781/4782/8693 are this project's shared surfaces):
  #    CITYNEXUS_DATABASE_URL must be absolute, CITYNEXUS_REAL_CITY_ENABLED=true, and
  #    CITYNEXUS_PROVIDER_NETWORK_MODE must honour this machine's proxy (see --provider-note).
  python tools/ord0489_demo_seed_r1.py --base-url http://127.0.0.1:8790 \
      --report evidence/ord0489_board_seed.json

Network note measured on the lane box (2026-09-30): a direct `httpx` call to
nominatim.openstreetmap.org is a 12 s ConnectTimeout, the same call honouring the machine proxy
answers 200 in 1.25 s, and with `CITYNEXUS_PROVIDER_NETWORK_MODE=direct` the product's own live
discovery silently degrades to `REPLAY_FALLBACK`.  That degradation is why this script checks
`provenance` instead of trusting the HTTP status.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import urllib.error
import urllib.request
import uuid as uuidlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

TIMEOUT_SECONDS = 120

#: The board.  Fixed literals on purpose: a re-run must land on the same screen, and a traveller
#: name invented per run would make every reading incomparable.
TRAVELER = {
    "display_name": "演示旅客 · 小林",
    "email": "ord0489.demo@example.invalid",
    "locale": "zh-CN",
    "timezone": "Asia/Shanghai",
}

CITIES = (
    {"city_code": "CN-TIANJIN", "role": "supplied",
     "queries": ("cafe", "museum", "attraction")},
    {"city_code": "CN-BEIJING", "role": "supplied",
     "queries": ("museum", "cafe", "park")},
    # No discovery is run for this one, which is the whole point: the board needs a city whose
    # catalogue is honestly empty so the empty state has something to be about.  Asking the
    # provider here would be the thing that gives it places.
    {"city_code": "CN-FUZHOU", "role": "no_places", "queries": ()},
)

JOURNEYS = (
    {
        "key": "tianjin_multiday",
        "title": "天津 · 三日两晚",
        "city_code": "CN-TIANJIN",
        "start": "2026-10-06T09:00:00+08:00",
        "end": "2026-10-08T18:00:00+08:00",
        "budget_minor": 900_000,
        "party_size": 2,
        "arrival_location": "Tianjin Station",
        "plan": True,
    },
    {
        "key": "beijing_multiday",
        "title": "北京 · 四日三晚",
        "city_code": "CN-BEIJING",
        "start": "2026-10-12T08:30:00+08:00",
        "end": "2026-10-15T20:00:00+08:00",
        "budget_minor": 1_400_000,
        "party_size": 3,
        "arrival_location": "Beijing South Railway Station",
        "plan": True,
    },
    {
        "key": "fuzhou_empty",
        "title": "福州 · 两日一夜（未规划）",
        "city_code": "CN-FUZHOU",
        "start": "2026-10-20T10:00:00+08:00",
        "end": "2026-10-21T16:00:00+08:00",
        "budget_minor": 300_000,
        "party_size": 1,
        "arrival_location": "Fuzhou Railway Station",
        "plan": False,
    },
)


class Abort(RuntimeError):
    """A named stop.  Every raise site says which invariant broke and what was read."""

    def __init__(self, reason: str, **facts):
        super().__init__(reason)
        self.reason = reason
        self.facts = facts


#: The report in flight, so a named stop still lands on disk with its own reason.  An abort that
#: writes nothing would leave the next reader guessing whether the board was ever attempted.
LIVE_REPORT: dict | None = None
LIVE_REPORT_PATH = "evidence/ord0489_board_seed.json"


def http(base: str, method: str, path: str, body=None, headers=None):
    data = None
    hdrs = {"Content-Type": "application/json"}
    hdrs.update(headers or {})
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(base + path, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, {"raw": raw[:400]}
    except Exception as exc:  # transport shape is itself a reading worth naming
        return -1, {"error": type(exc).__name__, "msg": str(exc)[:300]}


def expect(status: int, want: int, where: str, body=None) -> None:
    if status != want:
        raise Abort(
            "UNEXPECTED_HTTP_STATUS",
            where=where,
            wanted=want,
            got=status,
            body=json.dumps(body, ensure_ascii=False)[:600] if body is not None else None,
        )


def read_board(base: str) -> dict:
    """Counts through read doors only, so a claim about the store names its door."""
    st, journeys = http(base, "GET", "/api/v1/journeys")
    per_city = {}
    for spec in CITIES:
        st_p, rows = http(base, "GET", f"/api/v1/places?city_code={spec['city_code']}")
        per_city[spec["city_code"]] = len(rows) if isinstance(rows, list) else {"status": st_p}
    st_r, recycled = http(base, "GET", "/api/v1/recycle-bin/journeys")
    return {
        "journeys_list_status": st,
        "journeys_visible": len(journeys) if isinstance(journeys, list) else None,
        "journey_titles_in_server_order": [j["title"] for j in journeys]
        if isinstance(journeys, list)
        else None,
        "places_by_city": per_city,
        "recycle_bin_status": st_r,
        "recycle_bin_rows": len(recycled) if isinstance(recycled, list) else None,
    }


def discover(base: str, journey_id: str, city: dict, log: list) -> dict:
    """Run the product's live provider channel for one city and keep its own answer."""
    collected = []
    for query in city["queries"]:
        st, body = http(
            base,
            "POST",
            f"/api/v1/journeys/{journey_id}/real-city/discover",
            {"query": query, "radius_m": 2500, "limit": 8, "mode": "live"},
        )
        if st != 200 or not isinstance(body, dict):
            raise Abort(
                "DISCOVER_DOOR_REFUSED",
                city_code=city["city_code"],
                query=query,
                status=st,
                body=json.dumps(body, ensure_ascii=False)[:600],
            )
        provenance = body.get("provenance")
        runtime = body.get("runtime_provenance")
        log.append(
            {
                "city_code": city["city_code"],
                "query": query,
                "status": st,
                "provenance": provenance,
                "runtime_provenance": runtime,
                "provider_status": body.get("provider_status"),
                "candidates": len(body.get("candidates") or []),
            }
        )
        if provenance != "LIVE_PROVIDER":
            # The named failure the order asks for: no supply, and no invented name either.
            raise Abort(
                "PROVIDER_SUPPLY_ABSENT_NOT_INVENTING_PLACES",
                city_code=city["city_code"],
                query=query,
                provenance=provenance,
                runtime_provenance=runtime,
                provider_status=body.get("provider_status"),
                hint="live discovery degraded to a fallback; fix the network mode or the "
                "provider, never the script",
            )
        collected.append({"query": query, "candidates": len(body.get("candidates") or [])})
    return {"queries": collected}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base-url", default="http://127.0.0.1:8790")
    ap.add_argument("--report", default="evidence/ord0489_board_seed.json")
    ap.add_argument(
        "--allow-non-empty-store",
        action="store_true",
        help="seed onto a store that already holds journeys (default refuses, so a re-run "
        "cannot silently double the board)",
    )
    ap.add_argument(
        "--probe-empty-city-supply",
        action="store_true",
        help="also run live discovery for the no-places city and record the provider's answer "
        "as an observation; the board invariant (0 catalogue rows there) is not changed by it",
    )
    args = ap.parse_args()
    global LIVE_REPORT, LIVE_REPORT_PATH
    LIVE_REPORT_PATH = args.report
    base = args.base_url.rstrip("/")
    report: dict = {
        "order": "ORD-0489",
        "script": Path(__file__).name,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base,
        "board_spec": {
            "cities": [c["city_code"] for c in CITIES],
            "journeys": [j["title"] for j in JOURNEYS],
        },
        "discover_log": [],
        "steps": [],
    }
    LIVE_REPORT = report

    host, _, port = base.split("//", 1)[-1].partition(":")
    try:
        socket.create_connection((host, int(port)), timeout=5).close()
    except OSError as exc:
        report["abort"] = {"reason": "BACKEND_NOT_REACHABLE", "error": str(exc)[:200]}
        _write(report, args.report)
        return 2

    st, health = http(base, "GET", "/api/v1/health")
    report["health"] = {"status": st, "body": health}
    if st != 200:
        report["abort"] = {"reason": "HEALTH_DOOR_REFUSED", "status": st}
        _write(report, args.report)
        return 2

    before = read_board(base)
    report["board_before"] = before
    if before["journeys_visible"] and not args.allow_non_empty_store:
        raise Abort("STORE_NOT_EMPTY_REFUSING_TO_DOUBLE_THE_BOARD", **before)

    st, traveler = http(base, "POST", "/api/v1/travelers", TRAVELER)
    expect(st, 201, "POST /api/v1/travelers", traveler)
    report["traveler"] = {"id": traveler["id"], "display_name": traveler["display_name"]}

    journeys: dict[str, dict] = {}
    for spec in JOURNEYS:
        st, created = http(
            base,
            "POST",
            "/api/v1/journeys",
            {
                "traveler_id": traveler["id"],
                "title": spec["title"],
                "city_code": spec["city_code"],
                "timezone": "Asia/Shanghai",
                "start_at": spec["start"],
                "end_at": spec["end"],
                "budget": {"currency": "CNY", "amount_minor": spec["budget_minor"]},
                "planning_mode": "balanced",
                "party_size": spec["party_size"],
                "arrival_anchor": {
                    "at": spec["start"],
                    "location": spec["arrival_location"],
                },
            },
        )
        expect(st, 201, f"POST /api/v1/journeys ({spec['key']})", created)
        journeys[spec["key"]] = created
    report["journeys"] = {
        key: {"id": row["id"], "city_code": row["city_code"], "status": row["status"]}
        for key, row in journeys.items()
    }

    city_journey = {c["city_code"]: None for c in CITIES}
    for spec in JOURNEYS:
        city_journey[spec["city_code"]] = journeys[spec["key"]]["id"]

    for city in CITIES:
        if city["role"] != "supplied":
            continue
        journey_id = city_journey[city["city_code"]]
        if journey_id is None:
            raise Abort("NO_JOURNEY_FOR_CITY", city_code=city["city_code"])
        discover(base, journey_id, city, report["discover_log"])

    # Named fact about the captured catalogue: OSM elements with no `name` tag are stored under
    # the product's own fallback (`OSM <category>`, real_city.py's live parser).  Counting them
    # keeps "16 real places" from quietly meaning "16 names a provider actually said".
    report["catalogue_name_fallbacks"] = {}
    for city in CITIES:
        st_p, rows = http(base, "GET", f"/api/v1/places?city_code={city['city_code']}")
        if isinstance(rows, list):
            unnamed = [r["name"] for r in rows if str(r.get("name") or "").startswith("OSM ")]
            report["catalogue_name_fallbacks"][city["city_code"]] = {
                "rows": len(rows),
                "provider_unnamed_fallback_rows": len(unnamed),
                "fallback_names": unnamed[:6],
            }

    if args.probe_empty_city_supply:
        for city in CITIES:
            if city["role"] == "supplied":
                continue
            probe = {**city, "queries": city["queries"] or ("cafe",)}
            try:
                discover(base, city_journey[city["city_code"]], probe, report["discover_log"])
                report.setdefault("empty_city_supply_probe", {})[city["city_code"]] = "ANSWERED"
            except Abort as exc:
                report.setdefault("empty_city_supply_probe", {})[city["city_code"]] = {
                    "reason": exc.reason,
                    **exc.facts,
                }

    # Plans: multi-day journeys only.
    #
    # Two doors, in this order, because the first one is honest and the second one is what a
    # real OSM catalogue can actually satisfy on this build.  `plans/generate` draws its day
    # sequences from each place's own open/close (`_place_window` in `backend/app/services.py`),
    # and live Overpass stops in these two cities carry no `opening_hours` tag, so it answers
    # 422 `CATALOG_INSUFFICIENT` with `day_sequences_available: 0` while the catalogue itself is
    # full - that refusal is recorded, not hidden.  `authoritative-compose` takes the POIs the
    # traveller picked and schedules the trip around the journey's own anchors, which is the
    # door that works on provider truth; it is a product route, not a substitute dataset.
    for spec in JOURNEYS:
        if not spec["plan"]:
            continue
        journey_id = journeys[spec["key"]]["id"]
        step: dict = {"journey_key": spec["key"]}
        st, plans = http(
            base,
            "POST",
            f"/api/v1/journeys/{journey_id}/plans/generate",
            {"candidate_count": 3},
            headers={"Idempotency-Key": f"ord0489-{spec['key']}-generate"},
        )
        step["generate_status"] = st
        if st in (200, 201) and isinstance(plans, list) and plans:
            step["generate_candidates"] = len(plans)
            chosen = plans[0]
        else:
            step["generate_refusal"] = json.dumps(plans, ensure_ascii=False)[:700]
            step["generate_candidates"] = 0
            st_p, city_places = http(
                base, "GET", f"/api/v1/places?city_code={spec['city_code']}"
            )
            expect(st_p, 200, f"GET /places ({spec['city_code']})", city_places)
            place_ids = [row["id"] for row in (city_places or [])][:4]
            if len(place_ids) < 2:
                raise Abort(
                    "COMPOSE_NEEDS_TWO_LIVE_PLACES_BUT_CATALOGUE_GAVE_FEWER",
                    journey_key=spec["key"],
                    city_code=spec["city_code"],
                    rows=len(place_ids),
                )
            st_c, composed = http(
                base,
                "POST",
                f"/api/v1/journeys/{journey_id}/authoritative-compose",
                {"place_ids": place_ids, "candidate_count": 2},
            )
            if st_c != 201 or not isinstance(composed, dict) or not composed.get("top_k"):
                raise Abort(
                    "AUTHORITATIVE_COMPOSE_DID_NOT_PRODUCE_A_PLAN",
                    journey_key=spec["key"],
                    status=st_c,
                    place_ids=place_ids,
                    body=json.dumps(composed, ensure_ascii=False)[:700],
                )
            step["compose"] = {
                "status": st_c,
                "optimizer": composed.get("optimizer"),
                "candidates": len(composed.get("top_k") or []),
                "place_ids_used": place_ids,
                "stay_offer_id": composed.get("stay_offer_id"),
            }
            chosen = composed["top_k"][0]
        st, selected = http(
            base, "POST", f"/api/v1/journeys/{journey_id}/plans/{chosen['id']}/select", {}
        )
        expect(st, 200, f"select plan ({spec['key']})", selected)
        st, read_back = http(base, "GET", f"/api/v1/journeys/{journey_id}/plans")
        current = (
            [row for row in read_back if row.get("is_current")]
            if isinstance(read_back, list)
            else []
        )
        step.update(
            {
                "selected_plan_version_id": chosen["id"],
                "plans_door_rows": len(read_back) if isinstance(read_back, list) else None,
                "is_current_rows": len(current),
                "activities_on_current_plan": len(current[0].get("activities") or [])
                if current
                else None,
            }
        )
        if not current or not (current[0].get("activities") or []):
            raise Abort(
                "SELECTED_PLAN_CARRIES_NO_ACTIVITIES",
                journey_key=spec["key"],
                plan_version_id=chosen["id"],
                step=step,
            )
        report["steps"].append(step)
        journeys[spec["key"]]["plan"] = current[0] if current else chosen

    # Footprint: three stamps on the Tianjin trip - two places, one activity.
    tj = journeys["tianjin_multiday"]
    st, tj_places = http(base, "GET", "/api/v1/places?city_code=CN-TIANJIN")
    expect(st, 200, "GET /api/v1/places (CN-TIANJIN)", tj_places)
    if not isinstance(tj_places, list) or len(tj_places) < 2:
        raise Abort("TIANJIN_CATALOG_TOO_SMALL_FOR_FOOTPRINT", rows=len(tj_places or []))
    activity_id = None
    if tj.get("plan"):
        acts = [a for a in (tj["plan"].get("activities") or []) if a.get("id")]
        activity_id = acts[0]["id"] if acts else None
    stamps = []
    for place in tj_places[:2]:
        st, body = http(
            base,
            "POST",
            f"/api/v1/journeys/{tj['id']}/checkins",
            {"place_id": place["id"], "note": "ORD-0489 盘面足迹"},
        )
        stamps.append({"target": "place", "status": st, "refusal": (body or {}).get("error")})
    if activity_id:
        st, body = http(
            base,
            "POST",
            f"/api/v1/journeys/{tj['id']}/checkins",
            {"activity_id": activity_id, "note": "ORD-0489 盘面足迹"},
        )
        stamps.append({"target": "activity", "status": st, "refusal": (body or {}).get("error")})
    st, footprint = http(base, "GET", f"/api/v1/journeys/{tj['id']}/checkins")
    report["footprint"] = {
        "stamps_attempted": stamps,
        "door_status": st,
        "rows": len(footprint) if isinstance(footprint, list) else None,
        "rows_sample": json.dumps(footprint[:2], ensure_ascii=False)[:700]
        if isinstance(footprint, list)
        else None,
    }

    # Share: one live grant, one revoked grant, one recycle-binned trip, one unknown token.
    share: dict = {}
    st, grant = http(
        base,
        "POST",
        f"/api/v1/journeys/{tj['id']}/share-grants",
        {
            "visibility": "LINK_READ",
            "created_by": traveler["id"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        },
    )
    expect(st, 201, "create live share grant", grant)
    share["live_grant"] = {"id": grant["id"], "token_len": len(str(grant.get("token") or ""))}
    st, as_guest = http(base, "GET", f"/api/v1/shared/journeys/{grant['token']}")
    share["live_grant"]["guest_read_status"] = st
    share["live_grant"]["guest_plan_state"] = (as_guest or {}).get("plan_state")

    bj = journeys["beijing_multiday"]
    st, grant2 = http(
        base,
        "POST",
        f"/api/v1/journeys/{bj['id']}/share-grants",
        {
            "visibility": "LINK_READ",
            "created_by": traveler["id"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        },
    )
    expect(st, 201, "create grant to revoke", grant2)
    st, revoked = http(
        base, "POST", f"/api/v1/journeys/{bj['id']}/share-grants/{grant2['id']}/revoke", {}
    )
    share["revoked_grant"] = {
        "id": grant2["id"],
        "revoke_status": st,
        "revoke_body": json.dumps(revoked, ensure_ascii=False)[:400],
    }
    st, guest_after = http(base, "GET", f"/api/v1/shared/journeys/{grant2['token']}")
    share["revoked_grant"]["guest_read_status"] = st
    share["revoked_grant"]["guest_refusal"] = json.dumps(guest_after, ensure_ascii=False)[:400]

    st, guest_bad = http(base, "GET", f"/api/v1/shared/journeys/{uuidlib.uuid4().hex}")
    share["unknown_token"] = {
        "status": st,
        "body": json.dumps(guest_bad, ensure_ascii=False)[:400],
    }

    fz = journeys["fuzhou_empty"]
    # The third share state is a key that was cut while the trip was live and is presented after
    # the trip went into the bin.  The grant therefore has to exist *before* the DELETE, which is
    # also why the post-bin grant attempt is recorded rather than skipped: the door refuses it.
    st, grant3 = http(
        base,
        "POST",
        f"/api/v1/journeys/{fz['id']}/share-grants",
        {
            "visibility": "LINK_READ",
            "created_by": traveler["id"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        },
    )
    expect(st, 201, "create grant on the trip that is about to be binned", grant3)
    share["binned_grant"] = {"id": grant3["id"], "token_len": len(str(grant3.get("token") or ""))}
    st, guest_before_bin = http(base, "GET", f"/api/v1/shared/journeys/{grant3['token']}")
    share["binned_grant"]["guest_read_before_bin"] = st

    st, _ = http(base, "DELETE", f"/api/v1/journeys/{fz['id']}")
    share["recycle_bin"] = {"delete_status": st}
    st, guest_after_bin = http(base, "GET", f"/api/v1/shared/journeys/{grant3['token']}")
    share["binned_grant"]["guest_read_after_bin"] = st
    share["binned_grant"]["guest_body_after_bin"] = json.dumps(guest_after_bin, ensure_ascii=False)[:500]
    st, late_grant = http(
        base,
        "POST",
        f"/api/v1/journeys/{fz['id']}/share-grants",
        {
            "visibility": "LINK_READ",
            "created_by": traveler["id"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        },
    )
    share["grant_cut_attempted_after_binning"] = {
        "status": st,
        "body": json.dumps(late_grant, ensure_ascii=False)[:400],
    }
    st, bin_rows = http(base, "GET", "/api/v1/recycle-bin/journeys")
    share["recycle_bin"]["bin_status"] = st
    share["recycle_bin"]["bin_rows"] = len(bin_rows) if isinstance(bin_rows, list) else None
    share["recycle_bin"]["bin_row_ids"] = (
        [row.get("id") for row in bin_rows] if isinstance(bin_rows, list) else None
    )
    report["binned_trip_id"] = fz["id"]
    st, guest_other = http(base, "GET", f"/api/v1/shared/journeys/{grant['token']}")
    share["recycle_bin"]["live_grant_still_readable_after_other_trip_binned"] = st

    report["board_after"] = read_board(base)
    report["share"] = share

    # Invariants the whole exercise was for.  A failing one is reported, never rounded up.
    empty_city = "CN-FUZHOU"
    places_empty_now = report["board_after"]["places_by_city"].get(empty_city)
    invariants = {
        "journeys_visible_is_2_after_binning_one": report["board_after"]["journeys_visible"] == 2,
        "recycle_bin_holds_1": report["board_after"]["recycle_bin_rows"] == 1,
        "supplied_cities_have_places": all(
            isinstance(report["board_after"]["places_by_city"].get(c["city_code"]), int)
            and report["board_after"]["places_by_city"][c["city_code"]] >= 1
            for c in CITIES
            if c["role"] == "supplied"
        ),
        "no_places_city_is_0": places_empty_now == 0,
        "footprint_rows_at_least_1": (report["footprint"]["rows"] or 0) >= 1,
        "all_discoveries_were_live_provider": all(
            row["provenance"] == "LIVE_PROVIDER" for row in report["discover_log"]
        ),
    }
    # This one was MY prediction, not a product promise, and the door measured it false: a fresh
    # key can still be cut for a trip that is in the recycle bin (201), while an old key presented
    # at the guest door answers 409 SHARE_GRANT_JOURNEY_IN_RECYCLE_BIN.  It is recorded as a
    # finding with both readings, not converted into an assertion that flatters the board.
    report["findings"] = [
        {
            "id": "ORD0489-F1_grant_door_does_not_check_the_bin",
            "readings": {
                "grant_cut_after_binning_status": share["grant_cut_attempted_after_binning"]["status"],
                "old_key_after_binning_status": share["binned_grant"]["guest_read_after_bin"],
                "old_key_refusal": share["binned_grant"]["guest_body_after_bin"],
            },
            "statement": "POST share-grants accepts a new key for a binned trip; the guest door "
            "refuses presentation of a key whose trip is binned.",
        },
        {
            "id": "ORD0489-F2_generate_needs_provider_stated_hours",
            "readings": {
                "generate_status_per_multiday_trip": [s.get("generate_status") for s in report["steps"]],
                "generate_refusals": [str(s.get("generate_refusal"))[:240] for s in report["steps"]],
                "compose_status_per_multiday_trip": [
                    (s.get("compose") or {}).get("status") for s in report["steps"]
                ],
            },
            "statement": "plans/generate answers 422 CATALOG_INSUFFICIENT on a live-supplied "
            "catalogue whose stops carry no opening_hours, while the same city has places and "
            "authoritative-compose plans it; the empty-day-sequence count is reported by the door.",
        },
    ]
    report["invariants"] = invariants
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    _write(report, args.report)
    failed = [name for name, ok in invariants.items() if not ok]
    print(json.dumps({"invariants_failed": failed, "report": str(args.report)}, ensure_ascii=False))
    print(
        json.dumps(
            {
                "board_after": report["board_after"],
                "footprint_rows": report["footprint"]["rows"],
                "share": {k: v for k, v in share.items()},
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    return 0 if not failed else 1


def _write(report: dict, target: str) -> None:
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Abort as exc:
        payload = {"reason": exc.reason, **exc.facts}
        if LIVE_REPORT is not None:
            LIVE_REPORT["abort"] = payload
            LIVE_REPORT["finished_at"] = datetime.now(timezone.utc).isoformat()
            _write(LIVE_REPORT, LIVE_REPORT_PATH)
        print(json.dumps({"abort": payload}, ensure_ascii=False, indent=1))
        sys.exit(3)
