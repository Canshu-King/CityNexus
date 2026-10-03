"""Fold the real-door readings into one receipt, and count what the store ended up holding.

The judgement this hand has to support is narrow: for each of the four sentences, did the DOOR name the
code and did the SCREEN then say the table's own words. Both halves are read out of the arm files; the
store count is taken from the same sqlite file with `?mode=ro` after the run, so "the two control arms
wrote the only stamps" is a number and not a hope.
"""
import glob
import io
import json
import os
import sqlite3
import time

EVID = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/checkin-words-real-door"
OUT = "%s/receipts/day26_real_door_summary_r1.json" % EVID
STORE = "D:/moodle/_qoder_e766b154_ord0528_20261001/run/day26_real_door.db"
PAIRS = [("journeyUnknown", "CHECKIN_JOURNEY_UNKNOWN"), ("activityUnknown", "CHECKIN_ACTIVITY_UNKNOWN"),
         ("activityNotInJourney", "CHECKIN_ACTIVITY_NOT_IN_JOURNEY"),
         ("placeUnknown", "CHECKIN_PLACE_UNKNOWN")]


def main():
    rows = []
    for name in sorted(glob.glob("%s/readings/r-*.json" % EVID)):
        body = json.load(io.open(name, encoding="utf-8"))
        rows.append({
            "file": os.path.basename(name), "kind": body["kind"], "locale": body["locale"],
            "copy_key": body.get("copy_key"), "code_expected": body.get("code_expected"),
            "door_reason_code": body.get("door_reason_code"), "door_status": body.get("door_status"),
            "door_message": body.get("door_message"),
            "door_details_keys": body.get("door_details_keys"),
            "painted_notice": body.get("painted_notice"),
            "notices_count": body.get("notices_count"),
            "door_rows_before": body.get("door_rows_before"),
            "door_rows_after": body.get("door_rows_after"),
            "checks_failed": sorted(k for k, v in (body.get("checks") or {}).items() if v is False),
            "scan_visual_leaves": body.get("scan_visual_leaves"),
            "answered_by": body.get("answered_by"),
        })
    refusals = [r for r in rows if r["kind"] == "real_door"]
    controls = [r for r in rows if r["kind"] == "control"]
    wanted = {c: [r for r in refusals if r["copy_key"] == c and r["door_reason_code"] == code]
              for c, code in PAIRS}
    conn = sqlite3.connect("file:%s?mode=ro" % STORE.replace("\\", "/"), uri=True)
    store_rows = conn.execute("select count(*) from journey_checkins").fetchone()[0]
    stamped = conn.execute("select journey_id, target_key, stamped_at from journey_checkins "
                           "order by stamped_at").fetchall()
    conn.close()

    body = {
        "taken_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "arms": len(rows), "refusal_arms": len(refusals), "control_arms": len(controls),
        "arms_with_failed_check": sorted(r["file"] for r in rows if r["checks_failed"]),
        "every_refusal_named_by_the_door": all(len(v) == 2 for v in wanted.values()),
        "codes_named_by_the_door": {c: [r["door_reason_code"] for r in v] for c, v in wanted.items()},
        "statuses_seen": sorted({str(r["door_status"]) for r in refusals}),
        "painted_non_empty_arms": len([r for r in refusals if r["painted_notice"]
                                       and len(r["painted_notice"]) > 8]),
        "one_notice_in_every_refusal": all(r["notices_count"] == 1 for r in refusals),
        "controls_added_one_row_each": [
            {"locale": r["locale"], "before": r["door_rows_before"], "after": r["door_rows_after"],
             "refusal_painted": r["notices_count"]} for r in controls],
        "store_after_the_run": {
            "file": STORE.replace("\\", "/"), "opened_as": "sqlite uri ?mode=ro",
            "journey_checkins_rows": store_rows,
            "rows": [{"journey_id": s[0], "target_key": s[1], "stamped_at": s[2]} for s in stamped],
            "provenance": "journey_checkins.journey_id / .target_key / .stamped_at",
        },
        "rows": rows,
    }
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(body, handle, indent=1, ensure_ascii=False)
    printable = json.dumps({k: v for k, v in body.items() if k != "rows"},
                           ensure_ascii=False, indent=1)
    print(printable.encode("ascii", "replace").decode("ascii")[:1500])
    print("WROTE %s bytes=%d" % (OUT, len(json.dumps(body, ensure_ascii=False).encode("utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
