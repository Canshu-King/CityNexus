"""Pick the four targets this hand needs, out of the store this lane is about to serve.

The order (CMDR 19:46) asks for four sentences to be read off a screen where the answer came from the
real door rather than from an instrument. Each of those four refusals is produced by a specific
validation in `backend/app/main.py`, so the ids have to be real facts about the store:

  CHECKIN_JOURNEY_UNKNOWN          a journey id the store does not hold
  CHECKIN_ACTIVITY_UNKNOWN         an activity id the store does not hold
  CHECKIN_ACTIVITY_NOT_IN_JOURNEY  an activity id that exists, under ANOTHER journey's plan version
  CHECKIN_PLACE_UNKNOWN            a place id the store does not hold

Everything here is read with sqlite in `?mode=ro` and each value carries its table and column, so the
receipt names its own store. The unknown ids are chosen, then *proven* absent by a count, not assumed.
"""
import io
import json
import os
import sqlite3
import time
import uuid

STORE = "D:/moodle/_qoder_e766b154_ord0528_20261001/run/day26_real_door.db"
OUT = ("D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/checkin-words-real-door/"
       "receipts/real_door_targets_r1.json")
DEMO_JOURNEY = "22222222-2222-4222-8222-222222222222"


def main():
    conn = sqlite3.connect("file:%s?mode=ro" % STORE.replace("\\", "/"), uri=True)
    conn.row_factory = sqlite3.Row
    journeys = [dict(r) for r in conn.execute(
        "select id, title, active_plan_version_id, deleted_at from journeys "
        "where active_plan_version_id is not null order by id")]
    live = [j for j in journeys if j["deleted_at"] is None]
    if len(live) < 2:
        print("ABORT need two live journeys, found %d" % len(live))
        return 3
    mine = [j for j in live if j["id"] == DEMO_JOURNEY] or live[:1]
    other = [j for j in live if j["id"] != mine[0]["id"]][0]

    def activities(plan_id):
        return [dict(r) for r in conn.execute(
            "select id, title, sequence_no from activities where plan_version_id = ? "
            "order by sequence_no", (plan_id,))]

    mine_acts = activities(mine[0]["active_plan_version_id"])
    other_acts = activities(other["active_plan_version_id"])
    unknown_journey = str(uuid.uuid4())
    unknown_activity = str(uuid.uuid4())
    unknown_place = str(uuid.uuid4())
    counts = {
        "journeys_with_that_id": conn.execute("select count(*) from journeys where id = ?",
                                              (unknown_journey,)).fetchone()[0],
        "activities_with_that_id": conn.execute("select count(*) from activities where id = ?",
                                                (unknown_activity,)).fetchone()[0],
        "places_with_that_id": conn.execute("select count(*) from places where id = ?",
                                            (unknown_place,)).fetchone()[0],
        "foreign_activity_exists": conn.execute("select count(*) from activities where id = ?",
                                                (other_acts[0]["id"],)).fetchone()[0],
    }
    if min(counts[k] for k in ("journeys_with_that_id", "activities_with_that_id",
                              "places_with_that_id")) != 0:
        print("ABORT an id chosen as 'unknown' is actually present: %s" % counts)
        return 4
    if counts["foreign_activity_exists"] != 1:
        print("ABORT the foreign activity is not a real row: %s" % counts)
        return 5

    body = {
        "taken_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "store": STORE.replace("\\", "/"),
        "opened_as": "sqlite uri ?mode=ro (0 writes from this file)",
        "live_journeys": len(live),
        "journey_used": {"id": mine[0]["id"], "title": mine[0]["title"],
                        "plan_version_id": mine[0]["active_plan_version_id"],
                        "activities": len(mine_acts),
                        "provenance": "journeys.id / journeys.active_plan_version_id"},
        "foreign_journey": {"id": other["id"], "title": other["title"],
                            "activities": len(other_acts)},
        "targets": {
            "CHECKIN_JOURNEY_UNKNOWN": {
                "post_journey_id": unknown_journey, "post_activity_id": mine_acts[0]["id"],
                "why": "journeys.id has no such row (count 0)"},
            "CHECKIN_ACTIVITY_UNKNOWN": {
                "post_journey_id": mine[0]["id"], "post_activity_id": unknown_activity,
                "why": "activities.id has no such row (count 0)"},
            "CHECKIN_ACTIVITY_NOT_IN_JOURNEY": {
                "post_journey_id": mine[0]["id"], "post_activity_id": other_acts[0]["id"],
                "why": "activities.id exists and its plan_version_id belongs to %s" % other["id"]},
            "CHECKIN_PLACE_UNKNOWN": {
                "post_journey_id": mine[0]["id"], "post_place_id": unknown_place,
                "why": "places.id has no such row (count 0)"},
            "CONTROL_valid_stamp": {
                "post_journey_id": mine[0]["id"], "post_activity_id": mine_acts[0]["id"],
                "why": "both ids are this journey's own rows: activities.id %s under plan %s"
                       % (mine_acts[0]["id"], mine[0]["active_plan_version_id"])},
        },
        "absence_counts": counts,
        "mine_first_activity": mine_acts[0],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(body, handle, indent=1, ensure_ascii=False)
    print("WROTE %s bytes=%d" % (OUT, len(json.dumps(body, ensure_ascii=False).encode("utf-8"))))
    print("journey=%s acts=%d foreign=%s counts=%s"
          % (mine[0]["id"][:8], len(mine_acts), other_acts[0]["id"][:8], counts))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
