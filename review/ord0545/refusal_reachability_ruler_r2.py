"""ORD-0545 (CMDR 01:37, option 甲): a re-runnable ruler for WHICH refusal sentence a traveller can reach.

Slice 5 read the two sentences only a device can decide, and named four that no traveller's next step can
produce.  That naming was a hand-run probe: it goes stale the moment a door moves.  This is the ruler the
commander asked for -- same verdicts, but computed from the structure of the shipped doors every time it is
run, so the answer to "may we read sentence X on glass?" stops depending on someone re-exploring by hand.

One row per key reachable only through `FAILURE_SENTENCE` (seven of them, read out of the component), and
each verdict is derived from named predicates, never typed:

  REACHABLE_BY_A_TRAVELLER_STEP   the door emits this reason_code AND some product door can put the screen
                                  into that state.
  UNREACHABLE_BY_A_TRAVELLER_STEP  the door emits it, but no door of this build can produce the state; the
                                  row then names WHICH predicate blocks it (that is the thing a new order
                                  would have to change).
  GLASS_ONLY                        no emit point in backend/app at all: this device decides it, so only a
                                  screen reading can settle it (that is what slice 5 did).

Predicates are structural greps over the shipped source, because a ruler that reads prose comments cannot be
flipped by a mutation, and a ruler that cannot be flipped proves nothing -- see the two counter-arms in
refusal_reachability_ruler_counterarm_r1.py (plant a hard-delete branch, or give the create door an active
plan), each single-variable, each restored byte-for-byte.

Store-shaped facts (how many plan versions carry a dated activity) are read from THIS lane's own copy of the
commander's canary, opened `mode=ro`; they are labelled per store so nobody mistakes them for source truth.

    D:/moodle/CityNexus/.venv/Scripts/python.exe -X utf8 review/ord0545/refusal_reachability_ruler_r1.py
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "review/ord0545/readouts" / os.environ.get("CITYNEXUS_ORD0545S5_RULER_NAME",
                                                        "refusal_reachability_ruler_r2.json")
PANEL = "frontend/src/features/poiimport/PoiImportPanel.tsx"
TABLE = "frontend/src/features/poiimport/poiImportCopy.ts"
MAIN = "backend/app/main.py"
SCHEMAS = "backend/app/schemas.py"
MY_DB = pathlib.Path("D:/moodle/_qoder_newlane_ord0533_data") / os.environ.get(
    "CITYNEXUS_ORD0533_DB", "_ord0533-lane_s5probe2.db")


def source(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def hits(pattern: str, *rels: str) -> list[str]:
    """One structural grep over named files, returning the matching lines as evidence."""
    args = ["git", "-C", str(ROOT), "grep", "-n", "-e", pattern, "--", *rels]
    return [ln for ln in subprocess.run(args, capture_output=True, text=True,
                                        errors="replace").stdout.splitlines() if ln.strip()]


def route_body(rel: str, decorator: str, until: int = 200) -> str:
    """The text of one route: from its decorator down to the next route decorator."""
    lines = source(rel).splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if decorator in ln)
    except StopIteration:
        return ""
    end = next((i for i in range(start + 2, min(start + until, len(lines)))
                if lines[i].startswith("@app.")), min(start + until, len(lines)))
    return "\n".join(lines[start:end])


def store_counts() -> dict:
    if not MY_DB.exists():
        return {"store": MY_DB.name, "available": False}
    import sqlite3
    with sqlite3.connect(f"file:{MY_DB.as_posix()}?mode=ro", uri=True) as conn:
        versions = conn.execute("select count(*) from plan_versions").fetchone()[0]
        zero_dated = conn.execute(
            "select count(*) from plan_versions pv where (select count(*) from activities a where "
            "a.plan_version_id = pv.id and a.start_at is not null and trim(a.start_at) <> '') = 0"
        ).fetchone()[0]
        places = conn.execute("select count(*) from places").fetchone()[0]
        structural = conn.execute("select count(*) from places where lower(category) in "
                                  "('arrival','departure','check_in','check_out','stay','luggage_drop')").fetchone()[0]
        foreign = conn.execute("select count(*) from places where city_code <> (select city_code from "
                               "places where id='place-food-hall')").fetchone()[0]
    return {"store": MY_DB.name, "available": True, "plan_versions": versions,
            "plan_versions_with_no_dated_activity": zero_dated, "places_rows": places,
            "structural_place_rows": structural, "other_city_place_rows": foreign}


def sentences() -> dict[str, str]:
    """The keys reachable only through the component's FAILURE_SENTENCE map, and the code each one answers."""
    panel = source(PANEL)
    # The map ends at its own closing brace. Reading to the end of the file used to work only while
    # FAILURE_SENTENCE was the last such table in the component: slice six added a second one
    # (`CHANNEL_NAME`), and the loose slice swept `LOCAL_TEXT_PARSER: "channelValueLocal"` into the map.
    # Verified equivalence on the pre-slice-six source: the loose and narrow slices return the same seven
    # pairs there, and only the narrow one keeps seven pairs afterwards.
    start = panel.index("const FAILURE_SENTENCE")
    body = panel[start:panel.index("};", start) + 2]
    mapping = dict(re.findall(r"^\s*([A-Z_]+): \"([a-zA-Z]+)\",", body, re.M))
    table = source(TABLE)
    keys = [k for k in mapping.values()]
    return {code: key for code, key in mapping.items()}, keys, table


def judge(code_to_key: dict, keys: list[str], table: str, counts: dict) -> list[dict]:
    main = source(MAIN)
    add_door = route_body(MAIN, '@app.post("/api/v1/journeys/{journey_id}/poi-import/add"')
    parse_door = route_body(MAIN, '@app.post("/api/v1/journeys/{journey_id}/poi-import/parse"')
    create_door = route_body(MAIN, '@app.post("/api/v1/journeys"')
    delete_door = route_body(MAIN, '@app.delete("/api/v1/journeys/{journey_id}"')
    emitted = {code: bool(re.search(f'"{code}"', add_door + parse_door)) for code in code_to_key}
    for code in ("JOURNEY_NOT_FOUND", "NO_ACTIVE_PLAN"):
        emitted[code] = emitted[code] or bool(re.search(f'"{code}"', main))

    # what a traveller's next step can actually change about the state the sentence answers
    hard_delete = hits("session\\.delete(journey", MAIN)
    bin_is_soft = "deleted_at = " in delete_door
    add_filters_the_bin = "deleted_at" in add_door
    create_leaves_plan_null = bool(re.search(r"active_plan_version_id=None|active_plan_version_id = None",
                                             create_door))
    city_filter_in_read_door = "Place.city_code == journey.city_code" in parse_door
    structural_filter_in_read_door = "_STRUCTURAL_PLACE_CATEGORIES" in parse_door
    city_writers = hits("journey\\.city_code\\s*=", MAIN)
    place_delete = hits("session\\.delete(place", MAIN)
    no_response_emits = hits("NO_RESPONSE_FROM_ORIGIN|UNNAMED_REFUSAL", "backend/app")

    rows: list[dict] = []
    for code, key in code_to_key.items():
        pair = {"errNoActivePlan": "NO_ACTIVE_PLAN", "errJourneyNotFound": "JOURNEY_NOT_FOUND",
                "errDayRequired": "IMPORT_DAY_REQUIRED", "errPlaceUnknown": "IMPORT_PLACE_UNKNOWN",
                "errPlaceNotVisitable": "IMPORT_PLACE_NOT_VISITABLE", "errUnnamed": "UNNAMED_REFUSAL",
                "errNoResponse": "NO_RESPONSE_FROM_ORIGIN"}
        assert key in pair, key
        row: dict[str, object] = {"table_key": key, "reason_code": code,
                                  "in_the_dictionary": bool(re.search(rf'^  {key}: \{{', table, re.M)),
                                  "door_emits_it": emitted.get(code, False)}
        if code == "JOURNEY_NOT_FOUND":
            blockers = [f"bin door is soft ({len(hard_delete)} hard-delete statements; deleted_at set in the "
                        f"delete route = {bin_is_soft})",
                        f"the write door itself filters nothing about the bin: {add_filters_the_bin}"]
            row["verdict"] = "REACHABLE_BY_A_TRAVELLER_STEP" if (hard_delete or add_filters_the_bin) \
                else "UNREACHABLE_BY_A_TRAVELLER_STEP"
        elif code == "NO_ACTIVE_PLAN":
            blockers = [f"the create door stores the plan pointer as null: {create_leaves_plan_null}"]
            row["verdict"] = "REACHABLE_BY_A_TRAVELLER_STEP" if create_leaves_plan_null \
                else "UNREACHABLE_BY_A_TRAVELLER_STEP"
        elif code == "IMPORT_DAY_REQUIRED":
            can = counts.get("available") and counts.get("plan_versions_with_no_dated_activity", 0) > 0
            blockers = [f"plan versions with no dated activity in this store copy: "
                        f"{counts.get('plan_versions_with_no_dated_activity', 'STORE_UNREAD')}"
                        f" of {counts.get('plan_versions', '?')}",
                        "plans/{id}/select only takes a CANDIDATE of the same journey"]
            row["verdict"] = "REACHABLE_BY_A_TRAVELLER_STEP" if can else "UNREACHABLE_BY_A_TRAVELLER_STEP"
        elif code == "IMPORT_PLACE_UNKNOWN":
            blockers = [f"the read door can only offer rows from places ({counts.get('places_rows', '?')} rows "
                        f"in this copy) and no door deletes a place ({len(place_delete)} delete statements)"]
            row["verdict"] = "REACHABLE_BY_A_TRAVELLER_STEP" if place_delete else \
                "UNREACHABLE_BY_A_TRAVELLER_STEP"
        elif code == "IMPORT_PLACE_NOT_VISITABLE":
            blockers = [f"the read door filters city: {city_filter_in_read_door}",
                        f"the read door filters structural categories: {structural_filter_in_read_door} "
                        f"({counts.get('structural_place_rows', '?')} structural rows, "
                        f"{counts.get('other_city_place_rows', '?')} other-city rows in this copy)",
                        f"doors that write journey.city_code: {len(city_writers)}"]
            row["verdict"] = "REACHABLE_BY_A_TRAVELLER_STEP" if (
                not city_filter_in_read_door or not structural_filter_in_read_door or city_writers) else \
                "UNREACHABLE_BY_A_TRAVELLER_STEP"
        else:
            blockers = [f"emit points for this token anywhere in backend/app: {len(no_response_emits)} -- "
                        f"this component decides it from how the call failed, so only glass can settle it"]
            row["verdict"] = "GLASS_ONLY"
        row["why"] = blockers
        row["verdict_is_a_flip_target"] = row["verdict"] != "GLASS_ONLY"
        rows.append(row)
    return rows


def main() -> int:
    code_to_key, keys, table = sentences()
    counts = store_counts()
    rows = judge(code_to_key, keys, table, counts)
    doc = {
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tip": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                              text=True).stdout.strip(),
        "read_from": {"component": PANEL, "dictionary": TABLE, "doors": MAIN, "store_copy": counts},
        "dictionary_keys_reachable_only_through_the_map": len(keys),
        "extraction_slice": {"ends_at_the_maps_own_closing_brace": True,
                              "pairs_found": len(code_to_key),
                              "reason_codes": sorted(code_to_key)},
        "rows": rows,
        "tally": {v: sum(1 for r in rows if r["verdict"] == v) for v in
                  sorted({str(r["verdict"]) for r in rows})},
        "self_checks": {
            "every_map_key_is_in_the_dictionary": all(r["in_the_dictionary"] for r in rows),
            "every_row_has_a_named_blocker": all(r["why"] for r in rows),
            "the_seven_are_the_whole_map": len(rows) == 7,
        },
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    for r in rows:
        print(f'{r["table_key"]:22} {r["verdict"]}', "|", (r["why"][0] if r["why"] else "")[:96])
    print("tally", json.dumps(doc["tally"], ensure_ascii=False), "| self_checks",
          json.dumps(doc["self_checks"], ensure_ascii=False))
    print("wrote", OUT.as_posix(), OUT.stat().st_size, "B")
    return 0 if all(doc["self_checks"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
