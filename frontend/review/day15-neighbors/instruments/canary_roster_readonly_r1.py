"""前置单 -- write one read-only receipt of the day15 canary's journey roster, exactly as it stands now.

This file exists because the delivery has to say what my run left behind without making the commander
take my word for it, and without me writing anything to his store. Three readings, all reads:

  * the door a traveller uses (`GET /api/v1/journeys`) -- how many trips are listed;
  * the product's own recycle-bin door (`GET /api/v1/recycle-bin/journeys`) -- whether the missing trip is
    listed there, which is what distinguishes "deleted" from "withdrawn by a door the product still has";
  * the file itself, opened `?mode=ro` -- the row, its `deleted_at`, and the fact that it is still a row.

The sqlite copy is read, never written. No door that writes was called by this instrument, and the
undelete door (`backend/app/main.py:3305`) is named below as a coordinate, not exercised.
"""
import io
import json
import sqlite3
import urllib.request

API = "http://127.0.0.1:4787/api/v1"
DB = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_cmdr_canary_day15.db"
DEMO = "22222222-2222-4222-8222-222222222222"
OUT = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/day15-neighbors/receipts/canary_roster_r1.json"


def get(path):
    request = urllib.request.Request(API + path)
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.status, json.loads(response.read())


def main():
    listed_status, listed = get("/journeys")
    bin_status, binned = get("/recycle-bin/journeys")
    scene_status, scene = get("/demo/scene")

    read_only = sqlite3.connect("file:%s?mode=ro" % DB.replace("\\", "/"), uri=True)
    rows = read_only.execute(
        "select id, city_code, status, deleted_at, active_plan_version_id from journeys order by created_at"
    ).fetchall()
    read_only.close()

    out = {
        "taken_at_local": time_text(),
        "api_listed": {
            "route": "GET /api/v1/journeys",
            "http_status": listed_status,
            "rows": len(listed),
            "ids": [row.get("id") for row in listed],
        },
        "api_recycle_bin": {
            "route": "GET /api/v1/recycle-bin/journeys",
            "http_status": bin_status,
            "rows": len(binned),
            "ids": [row.get("journey_id") or row.get("id") for row in binned],
        },
        "demo_scene": {
            "route": "GET /api/v1/demo/scene",
            "http_status": scene_status,
            "journey_id": scene.get("journey_id"),
            "journey_status": scene.get("journey_status"),
        },
        "file_read_only": {
            "path": DB,
            "opened": "?mode=ro",
            "journey_rows": len(rows),
            "rows": [
                {
                    "id": row[0],
                    "city_code": row[1],
                    "status": row[2],
                    "deleted_at": row[3],
                    "has_active_plan": bool(row[4]),
                }
                for row in rows
            ],
        },
        "the_trip_my_run_left_behind": {
            "id": DEMO,
            "in_the_list_door": DEMO in [row.get("id") for row in listed],
            "in_the_recycle_bin_door": DEMO in [row.get("journey_id") or row.get("id") for row in binned],
            "deleted_at_in_the_file": next(
                (row[3] for row in rows if row[0] == DEMO), "ROW_ABSENT_FROM_FILE"
            ),
            "door_that_can_undo_it": "POST /api/v1/journeys/{journey_id}/undelete (backend/app/main.py:3305) -- NOT called by this lane",
        },
    }
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(out, handle, indent=1, ensure_ascii=False)
    print("CANARY_ROSTER %s listed=%d binned=%d scene=%s"
          % (OUT, out["api_listed"]["rows"], out["api_recycle_bin"]["rows"], out["demo_scene"]["journey_status"]))
    return 0


def time_text():
    import time

    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


if __name__ == "__main__":
    raise SystemExit(main())
