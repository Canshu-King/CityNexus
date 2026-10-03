"""ORD-0545 slice 5, step 1 -- can a traveller's own next step produce each remaining refusal sentence?

Six of the seven table-only refusal sentences have never been read off glass (slice 3 read
`errNoActivePlan`, and slice 4 read the success family).  Before writing a glass spec, this probe walks
each remaining condition through PRODUCT DOORS on this lane's private stack and records what comes back --
and where a door cannot produce it, it names the door and the filter that blocks it instead of inventing
a state to paint.

Nothing here writes to the commander's canary: the store is my own copy, opened `mode=ro` for the census
queries, and every write goes through the API on my own port.  Reads of the source canary happen inside
`review/ord0533/lane_stack_r1.py`, which opened it read-only before making the copy.

    D:/moodle/CityNexus/.venv/Scripts/python.exe -X utf8 review/ord0545/refusal_reachability_probe_r1.py
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sqlite3
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "review/ord0545/readouts" / os.environ.get("CITYNEXUS_ORD0545S5_PROBE_NAME",
                                               "refusal_reachability_probe_r1.json")
BACKEND_PORT = int(os.environ.get("CITYNEXUS_ORD0533_BACKEND_PORT", "4921"))
API = f"http://127.0.0.1:{BACKEND_PORT}/api/v1"
MY_DB = pathlib.Path("D:/moodle/_qoder_newlane_ord0533_data") / os.environ.get(
    "CITYNEXUS_ORD0533_DB", "_ord0533-lane_s5probe.db")
TRAVELER = "11111111-1111-4111-8111-111111111111"
CANARY_JOURNEY = "22222222-2222-4222-8222-222222222222"
BASE_TIP = os.environ.get("CITYNEXUS_ORD0545_BASE_TIP", "bf4f776b0ba943b88817dfcc0cb3442d75fd9e21")
CREATES: list[dict] = []
UUID_RE = re.compile(r"\"id\"\s*:\s*\"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\"")
PLAN_POINTER_RE = re.compile(r"\"active_plan_version_id\"\s*:\s*(null|\"[0-9a-f-]{36}\")")


def api(method: str, path: str, body: dict | None = None) -> dict:
    """One product door, answered exactly as it arrived: status, its own reason_code, byte count."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            raw, status = res.read(), res.status
    except urllib.error.HTTPError as exp:
        raw, status = exp.read(), exp.code
    except Exception as exp:
        return {"status": "NO_ANSWER", "kind": type(exp).__name__, "bytes": 0, "text": ""}
    text = raw.decode("utf-8", "replace")
    reason = None
    try:
        parsed = json.loads(text) if raw else None
        if isinstance(parsed, dict):
            err = parsed.get("error")
            if isinstance(err, dict):
                reason = err.get("reason_code") or err.get("code")
    except Exception:
        parsed = None
    return {"status": status, "reason_code": reason, "bytes": len(raw), "text": text}


def field(pattern: re.Pattern, text: str) -> str | None:
    m = pattern.search(text or "")
    return m.group(1) if m else None


def ro(query: str, args: tuple = ()) -> list[tuple]:
    with sqlite3.connect(f"file:{MY_DB.as_posix()}?mode=ro", uri=True) as conn:
        return list(conn.execute(query, args))


def new_journey(label: str) -> str | None:
    """Create a trip through the product's own create door, copying the shape the canary trip carries.

    Every answer is kept in CREATES, including a refusal: a walk that cannot even make a trip is a reading
    about this build, not a detail to swallow.
    """
    canary = api("GET", f"/journeys/{CANARY_JOURNEY}")
    shape = json.loads(canary["text"]) if canary["status"] == 200 else {}
    if not shape:
        return None
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    made = api("POST", "/journeys", {
        "traveler_id": shape.get("traveler_id") or TRAVELER,
        "title": f"CNX s5 {label}",
        "city_code": shape.get("city_code", "CNX-DEMO"),
        "timezone": shape.get("timezone", "Asia/Shanghai"),
        "start_at": (now + timedelta(days=40)).isoformat(),
        "end_at": (now + timedelta(days=42)).isoformat(),
        "budget": {"amount_minor": 90000, "currency": (shape.get("budget") or {}).get("currency", "CNY")},
        "planning_mode": "balanced",
        "party_size": 2,
    })
    if made["status"] not in (200, 201):
        CREATES.append({"label": label, "status": made["status"], "reason_code": made.get("reason_code"),
                        "head": made["text"][:200]})
        return None
    CREATES.append({"label": label, "status": made["status"]})
    return field(UUID_RE, made["text"])


def main() -> int:
    walks: dict[str, object] = {}
    meta = {"measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "base_tip": BASE_TIP,
            "backend_port": BACKEND_PORT, "my_store": MY_DB.name,
            "store_queries_opened": "mode=ro over my own copy",
            "health": api("GET", "/health")["status"],
            "canary_journey_readable": api("GET", f"/journeys/{CANARY_JOURNEY}")["status"]}

    # ---------- the condition behind IMPORT_DAY_REQUIRED, straight from the table
    per_plan = ro("select pv.id, pv.journey_id, pv.status, count(a.id), "
                  "sum(case when a.start_at is not null and trim(a.start_at) <> '' then 1 else 0 end) "
                  "from plan_versions pv left join activities a on a.plan_version_id = pv.id group by pv.id")
    zero_dated = [r for r in per_plan if (r[4] or 0) == 0]
    walks["plan_versions_and_days"] = {
        "plan_versions": len(per_plan),
        "with_dated_activities": len(per_plan) - len(zero_dated),
        "with_zero_dated_activities": len(zero_dated),
        "statuses_of_zero_dated": sorted({r[2] for r in zero_dated}),
        "journeys_owning_a_zero_dated_version": sorted({r[1] for r in zero_dated}),
    }

    # ---------- control for this generation: the sentence slice 3 already owns
    j_no_plan = new_journey("control")
    control = {"journey_created": bool(j_no_plan)}
    if j_no_plan:
        p = api("POST", f"/journeys/{j_no_plan}/poi-import/parse", {"text": "Central Food Hall"})
        control.update({"parse_status": p["status"],
                        "parse_statuses": re.findall(r"\"status\"\s*:\s*\"([A-Z_]+)\"", p["text"])[:3],
                        "addable_flags": re.findall(r"\"addable\"\s*:\s*(true|false)", p["text"])[:3]})
        a = api("POST", f"/journeys/{j_no_plan}/poi-import/add", {"place_ids": ["place-food-hall"]})
        control.update({"add_status": a["status"], "add_reason_code": a["reason_code"]})
        # ---------- JOURNEY_NOT_FOUND: does any of the traveller's own steps make the row unreadable to the write door?
        d = api("DELETE", f"/journeys/{j_no_plan}")
        after_read = api("GET", f"/journeys/{j_no_plan}")
        after_add = api("POST", f"/journeys/{j_no_plan}/poi-import/add", {"place_ids": ["place-food-hall"]})
        walks["journey_not_found"] = {
            "delete_status": d["status"],
            "read_status_after_delete": after_read["status"],
            "read_reason_code_after_delete": after_read["reason_code"],
            "add_status_after_delete": after_add["status"],
            "add_reason_code_after_delete": after_add["reason_code"],
            "row_still_in_the_table": ro("select count(*) from journeys where id = ?", (j_no_plan,))[0][0],
            "deleted_at_value": ro("select deleted_at from journeys where id = ?", (j_no_plan,))[0][0],
            "hard_delete_doors_over_journeys": subprocess.run(
                ["git", "-C", str(ROOT), "grep", "-n", "session.delete(journey", "--", "backend/app"],
                capture_output=True, text=True).stdout.strip() or "0 hits in backend/app",
        }
        walks["no_active_plan_control"] = control

    # ---------- IMPORT_PLACE_UNKNOWN: does the read door ever hand out an id the write door cannot find?
    j_probe = new_journey("probeC")
    known = {r[0] for r in ro("select id from places")}
    offered = []
    for t in ("Central Food Hall", "Nexus City Park", "Design Library", "Rainforest Skywalk",
              "a place that exists nowhere at all", "..", "https://example.com/x"):
        p = api("POST", f"/journeys/{j_probe}/poi-import/parse", {"text": t})
        ids = re.findall(r"\"place_id\"\s*:\s*\"([^\"]*)\"", p["text"])
        offered.append({"text": t, "status": p["status"],
                        "item_statuses": re.findall(r"\"status\"\s*:\s*\"([A-Z_]+)\"", p["text"]),
                        "addable": re.findall(r"\"addable\"\s*:\s*(true|false)", p["text"]),
                        "place_ids": ids,
                        "ids_missing_from_the_places_table": [i for i in ids if i and i not in known]})
    walks["place_unknown"] = {
        "places_rows_in_my_copy": len(known),
        "offerings": offered,
        "read_door_ever_offered_an_unknown_id": any(o["ids_missing_from_the_places_table"] for o in offered),
        "doors_that_delete_a_place": subprocess.run(
            ["git", "-C", str(ROOT), "grep", "-n", "-e", "delete(place", "-e", "delete(Place", "--", "backend/app"],
            capture_output=True, text=True).stdout.strip() or "0 hits in backend/app",
    }

    # ---------- IMPORT_PLACE_NOT_VISITABLE: the write refuses a foreign-city or structural row; can the read door offer one?
    structural = ro("select id, city_code, category from places where lower(category) in "
                    "('arrival','departure','check_in','check_out','stay','luggage_drop')")
    foreign = ro("select id, city_code from places where city_code <> 'CNX-DEMO'")
    walks["place_not_visitable"] = {
        "structural_rows_in_my_copy": len(structural),
        "structural_sample": [{"id": r[0], "city": r[1], "category": r[2]} for r in structural[:6]],
        "rows_in_another_city": len(foreign),
        "another_city_sample": [{"id": r[0], "city": r[1]} for r in foreign[:6]],
        "journey_city_code_writers_in_the_backend": subprocess.run(
            ["git", "-C", str(ROOT), "grep", "-n", "journey\\.city_code\\s*=", "--", "backend/app"],
            capture_output=True, text=True).stdout.strip() or "0 assignments in backend/app",
        "read_door_filter": "poi-import/parse selects on Place.city_code == journey.city_code and "
                            "category notin _STRUCTURAL_PLACE_CATEGORIES",
    }

    # ---------- the two the browser decides for itself -- no door can emit them
    walks["browser_decided"] = {
        "emit_points_in_the_backend": subprocess.run(
            ["git", "-C", str(ROOT), "grep", "-rn", "-e", "NO_RESPONSE_FROM_ORIGIN", "-e", "UNNAMED_REFUSAL",
             "--", "backend/app"], capture_output=True, text=True).stdout.strip() or "0 hits in backend/app",
        "decided_in_the_panel": [ln.split(":", 2)[:2] for ln in subprocess.run(
            ["git", "-C", str(ROOT), "grep", "-n", "-e", "NO_RESPONSE_FROM_ORIGIN", "-e", "UNNAMED_REFUSAL",
             "--", "frontend/src/features/poiimport/PoiImportPanel.tsx"],
            capture_output=True, text=True).stdout.strip().splitlines()],
    }

    # verdicts are computed from the rows above, never typed in
    jnf = walks["journey_not_found"]
    jnf["verdict"] = ("NOT_REACHABLE_BY_A_TRAVELLER_STEP -- the row survives the bin door and the write door "
                      "still reads it" if jnf["row_still_in_the_table"] == 1 and
                      jnf["add_status_after_delete"] != 404 else "REACHABLE_THROUGH_A_DOOR")
    walks["plan_versions_and_days"]["verdict"] = (
        "REACHABLE_THROUGH_A_DOOR -- a version with zero dated activities exists"
        if walks["plan_versions_and_days"]["with_zero_dated_activities"] else
        "NOT_REACHABLE_IN_MY_COPY -- every plan version carries dated activities, so the day condition "
        "cannot be met by selecting one")
    pu = walks["place_unknown"]
    pu["verdict"] = "REACHABLE_THROUGH_A_DOOR" if pu["read_door_ever_offered_an_unknown_id"] else \
        "NOT_REACHABLE_BY_A_TRAVELLER_STEP -- the read door only offers ids that exist in places, and no " \
        "door deletes a place"
    pnv = walks["place_not_visitable"]
    pnv["verdict"] = ("NOT_REACHABLE_BY_A_TRAVELLER_STEP -- the read door filters both kinds and no door "
                      "moves a journey's city" if pnv["journey_city_code_writers_in_the_backend"].startswith("0 assignments")
                      else "CHECK_BY_HAND -- a city-writing door exists")

    out = {"meta": meta, "create_door_answers": CREATES, "walks": walks}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    for k, v in walks.items():
        print(k, "->", str(v.get("verdict", ""))[:96])
    print("wrote", OUT.as_posix(), OUT.stat().st_size, "B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
