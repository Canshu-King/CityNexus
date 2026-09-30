#!/usr/bin/env python3
"""ORD-0519 · build the demo board on whichever anchor leg this server can actually answer.

ORD-0489's seeder (`tools/ord0489_demo_seed_r1.py`) is left exactly as it is: its blob is quoted in
the ledger, and its refusal to invent place names is the behaviour this order must keep.  This file
differs in one thing and one thing only - where the city anchor comes from.  The product's live
discovery used to be a single Nominatim hop, and on a host where that hop dies at the TCP layer the
whole board became unbuildable while Photon answered 200 in about a second.

Rules that did not move:
  * places only ever arrive through `POST /real-city/discover` with `mode=live`, and a response whose
    `provenance` is not `LIVE_PROVIDER` is a named stop - a REPLAY fallback is never supply;
  * the script never names a place itself;
  * a city whose anchor legs both fail is recorded as a named cell (which hop, what reason) and the
    journey is still there - the board does not quietly lose a trip.

    python tools/ord0519_demo_seed_r1.py --base-url http://127.0.0.1:4951 \
        --report evidence/ord0519/board.json
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

TIMEOUT = 150
CITIES = (
    {"city_code": "CN-TIANJIN", "role": "supplied", "queries": ("cafe", "museum"), "days": 3},
    {"city_code": "CN-BEIJING", "role": "supplied", "queries": ("museum", "cafe"), "days": 4},
    # Deliberately not asked of any provider: the board needs one city whose catalogue is honestly
    # empty so the empty state has something to be about.
    {"city_code": "CN-FUZHOU", "role": "no_supply_attempt", "queries": (), "days": 2},
)
TRAVELER = {
    "display_name": "演示旅客 · 小林",
    "email": "ord0519.demo@example.invalid",
    "locale": "zh-CN",
    "timezone": "Asia/Shanghai",
}


#: the receipt in flight, so a named stop still lands on disk
IN_FLIGHT: tuple | None = None


class Stop(RuntimeError):
    def __init__(self, reason: str, **facts):
        super().__init__(reason)
        self.reason = reason
        self.facts = facts


def http(base: str, method: str, path: str, body=None, headers=None):
    hdrs = {"Content-Type": "application/json"}
    hdrs.update(headers or {})
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
            return resp.status, len(raw), (json.loads(raw.decode("utf-8")) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, len(raw), json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            return exc.code, len(raw), {"raw": raw.decode("utf-8", "replace")[:400]}
    except Exception as exc:
        return -1, 0, {"error": type(exc).__name__, "msg": str(exc)[:200]}


def legs_of(payload: dict) -> list[dict]:
    return ((payload or {}).get("provider_status") or {}).get("anchor_legs") or []


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base-url", default="http://127.0.0.1:8790")
    ap.add_argument("--report", default="evidence/ord0519/board.json")
    ap.add_argument("--allow-non-empty-store", action="store_true")
    ap.add_argument(
        "--anchor-leg-order",
        default=None,
        help="informational only: the server decides the order from CITYNEXUS_ANCHOR_LEG_ORDER. "
        "Passed through into the report so a reader can compare what was configured with what answered.",
    )
    args = ap.parse_args()
    base = args.base_url.rstrip("/")
    started = datetime.now(timezone.utc)
    global IN_FLIGHT
    report: dict = {
        "order": "ORD-0519",
        "script": Path(__file__).name,
        "started_at": started.isoformat(),
        "base_url": base,
        "requested_anchor_leg_order": args.anchor_leg_order,
        "supply_readings": [],
        "cells": [],
    }

    IN_FLIGHT = (report, args.report)
    st, _, health = http(base, "GET", "/api/v1/health")
    report["health"] = {"status": st, "body": health}
    if st != 200:
        report["stop"] = {"reason": "BACKEND_NOT_REACHABLE"}
        _write(report, args.report)
        return 2

    st, _, journeys_before = http(base, "GET", "/api/v1/journeys")
    if isinstance(journeys_before, list) and journeys_before and not args.allow_non_empty_store:
        report["stop"] = {
            "reason": "STORE_NOT_EMPTY_REFUSING_TO_DOUBLE_THE_BOARD",
            "journeys_already_visible": len(journeys_before),
        }
        _write(report, args.report)
        return 3

    st, _, traveler = http(base, "POST", "/api/v1/travelers", TRAVELER)
    if st != 201:
        raise Stop("TRAVELER_DOOR_REFUSED", status=st, body=traveler)

    journeys: dict[str, dict] = {}
    day0 = started + timedelta(days=7)
    for spec in CITIES:
        start = day0.replace(hour=9, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=spec["days"] - 1, hours=9)
        st, _, created = http(
            base,
            "POST",
            "/api/v1/journeys",
            {
                "traveler_id": traveler["id"],
                "title": f"{_city_zh(spec['city_code'])} · {spec['days']} 天",
                "city_code": spec["city_code"],
                "timezone": "Asia/Shanghai",
                "start_at": start.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                "end_at": end.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                "budget": {"currency": "CNY", "amount_minor": 300_000 * spec["days"]},
                "planning_mode": "balanced",
                "party_size": 2,
                "arrival_anchor": {"at": start.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                                   "location": _anchor_words(spec["city_code"])},
            },
        )
        if st != 201:
            raise Stop("JOURNEY_DOOR_REFUSED", city_code=spec["city_code"], status=st, body=created)
        journeys[spec["city_code"]] = created

    for spec in CITIES:
        if not spec["queries"]:
            report["cells"].append(
                {
                    "city_code": spec["city_code"],
                    "cell": "no_supply_attempt_by_design",
                    "why": "盘面需要一枚目录诚实为空的城市；对它发供能请求正是会给它造出地点的那一步",
                    "journey_id": journeys[spec["city_code"]]["id"],
                }
            )
            continue
        journey_id = journeys[spec["city_code"]]["id"]
        for query in spec["queries"]:
            # One bounded retry: this machine's Overpass mirror answered one board minutes ago and
            # returned `RESOLVER_UNREACHABLE` on the next, so a single attempt measures the mirror,
            # not the product. The retry never accepts a fallback - only `LIVE_PROVIDER` passes.
            for attempt in range(2):
                st, nbytes, body = http(
                    base,
                    "POST",
                    f"/api/v1/journeys/{journey_id}/real-city/discover",
                    {"query": query, "radius_m": 2500, "limit": 8, "mode": "live"},
                )
                if (body or {}).get("provenance") == "LIVE_PROVIDER" or attempt == 1:
                    break
                print(f"retry {spec['city_code']}/{query}: provenance={(body or {}).get('provenance')}", file=sys.stderr)
                import time as _t; _t.sleep(25)
            ps = (body or {}).get("provider_status") or {}
            reading = {
                "city_code": spec["city_code"],
                "query": query,
                "door_status": st,
                "response_bytes": nbytes,
                "provenance": (body or {}).get("provenance"),
                "runtime_provenance": (body or {}).get("runtime_provenance"),
                "anchor_source": (ps.get("anchor") or {}).get("source"),
                "anchor_legs": legs_of(body),
                "nominatim_state": ps.get("nominatim"),
                "photon_state": ps.get("photon"),
                "overpass_state": ps.get("overpass"),
                "candidates": len((body or {}).get("candidates") or []),
                "counts_as_supply": ps.get("counts_as_supply"),
                "fallback_reason": ps.get("fallback_reason"),
                "failure_stage": ps.get("failure_stage"),
            }
            report["supply_readings"].append(reading)
            if reading["provenance"] != "LIVE_PROVIDER":
                report["cells"].append(
                    {
                        "city_code": spec["city_code"],
                        "cell": "NO_REAL_PLACES_ON_THIS_SERVER",
                        "which_hop": reading["failure_stage"],
                        "reason": reading["fallback_reason"],
                        "anchor_legs": reading["anchor_legs"],
                        "counts_as_supply": False,
                        "journey_id": journey_id,
                        "seen_as": reading["provenance"],
                    }
                )
                # The refusal the board must keep: no supply, no invented names, no half-board.
                raise Stop(
                    "PROVIDER_SUPPLY_ABSENT_NOT_INVENTING_PLACES",
                    city_code=spec["city_code"],
                    query=query,
                    provenance=reading["provenance"],
                    anchor_legs=reading["anchor_legs"],
                    fallback_reason=reading["fallback_reason"],
                    failure_stage=reading["failure_stage"],
                )
            if reading["anchor_source"] and not reading["anchor_source"].startswith(
                tuple(str(item.get("leg")) for item in reading["anchor_legs"] if item.get("attempted"))
            ):
                raise Stop(
                    "ANCHOR_SOURCE_NOT_CREDITED_TO_A_LEG_THAT_ANSWERED",
                    city_code=spec["city_code"],
                    anchor_source=reading["anchor_source"],
                    anchor_legs=reading["anchor_legs"],
                )

        st, _, rows = http(base, "GET", f"/api/v1/places?city_code={spec['city_code']}")
        count = len(rows) if isinstance(rows, list) else None
        cell = {
            "city_code": spec["city_code"],
            "door": "GET /api/v1/places?city_code=",
            "place_rows": count,
            "journey_id": journey_id,
        }
        if not count:
            cell["cell"] = "NO_REAL_PLACES_ON_THIS_SERVER"
            last = report["supply_readings"][-1]
            cell["which_hop"] = last["failure_stage"]
            cell["reason"] = last["fallback_reason"] or last["photon_state"]
            cell["anchor_legs"] = last["anchor_legs"]
        else:
            cell["cell"] = "supplied"
            cell["anchor_sources"] = sorted(
                {
                    r["anchor_source"]
                    for r in report["supply_readings"]
                    if r["city_code"] == spec["city_code"] and r["anchor_source"]
                }
            )
            composed = http(
                base,
                "POST",
                f"/api/v1/journeys/{journey_id}/authoritative-compose",
                {"place_ids": [row["id"] for row in rows[:4]], "candidate_count": 2},
            )
            st_c, _, cbody = composed
            cell["compose_status"] = st_c
            cell["optimizer"] = (cbody or {}).get("optimizer")
            chosen = ((cbody or {}).get("top_k") or [{}])[0]
            if chosen.get("id"):
                st_s, _, _ = http(
                    base, "POST", f"/api/v1/journeys/{journey_id}/plans/{chosen['id']}/select", {}
                )
                st_p, _, plans = http(base, "GET", f"/api/v1/journeys/{journey_id}/plans")
                current = [p for p in (plans or []) if p.get("is_current")]
                cell["select_status"] = st_s
                cell["activities_on_current_plan"] = len((current[0].get("activities") or [])) if current else 0
        report["cells"].append(cell)

    st, _, visible = http(base, "GET", "/api/v1/journeys")
    report["board_after"] = {
        "journeys_visible": len(visible) if isinstance(visible, list) else None,
        "titles_in_server_order": [j["title"] for j in visible] if isinstance(visible, list) else None,
        "city_codes": sorted({j["city_code"] for j in visible}) if isinstance(visible, list) else None,
    }
    report["invariants"] = {
        "three_journeys_visible": report["board_after"]["journeys_visible"] == 3,
        "one_city_without_supply_attempt": any(
            c.get("cell") == "no_supply_attempt_by_design" for c in report["cells"]
        ),
        "every_live_call_credited_to_an_answered_leg": all(
            r["provenance"] == "LIVE_PROVIDER" for r in report["supply_readings"]
        ),
        "no_replay_counted_as_supply": all(
            r["provenance"] != "REPLAY" for r in report["supply_readings"]
        ),
    }
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    _write(report, args.report)
    failed = [k for k, v in report["invariants"].items() if v is not True]
    print(json.dumps({"report": args.report, "invariants_failed": failed,
                      "board_after": report["board_after"]}, ensure_ascii=False, indent=1))
    return 0 if not failed else 1


def _city_zh(code: str) -> str:
    return {"CN-TIANJIN": "天津", "CN-BEIJING": "北京", "CN-FUZHOU": "福州"}.get(code, code)


def _anchor_words(code: str) -> str:
    return {"CN-TIANJIN": "Tianjin Station", "CN-BEIJING": "Beijing South Railway Station",
            "CN-FUZHOU": "Fuzhou Railway Station"}.get(code, code)


def _write(report: dict, target: str) -> None:
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Stop as exc:
        payload = {"reason": exc.reason, **exc.facts}
        if IN_FLIGHT:
            report, target = IN_FLIGHT
            report["stop"] = payload
            report["finished_at"] = datetime.now(timezone.utc).isoformat()
            _write(report, target)
        print(json.dumps({"stop": payload, "report_written": bool(IN_FLIGHT)}, ensure_ascii=False, indent=1))
        sys.exit(4)
