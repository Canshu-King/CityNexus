"""Probe: why did prepare-plan refuse this journey with PLACE_NOT_IN_JOURNEY_CITY, and not the one before it?

Measured, not guessed.  bf110 (trial/results/20261026_gozero/bf110-replan-apply-full-chain-430-r2.txt:35)
walked a real traveller chain on the clean generation -- send the goal sentence, let the round finish, enter
the trip, tick 「按以上时间准备方案」, press 「保存为正式候选方案」 -- and the door answered
409 PLACE_NOT_IN_JOURNEY_CITY, while the card said 「这次未能保存，时间仍留在这里，可以重试。」.  bd106
(bd-confirm-then-press-430-r106.txt) pressed the same key on the same stack and got 201 twice.  The screen
cannot tell the two apart, so the probe reads the rows the two code paths touch:
backend/app/agent/goal_preparation.py:257-278 binds a slot to a Place either by the task's own
candidate_place_ids, or through the research lead's canonical_place_id, and only the second site compares
city codes without a city filter first.

Read-only by design: the DB is opened with mode=ro, nothing is written, and no key is read or printed.
Usage: python _bg_probe_city_refusal_r111.py <journey_id_prefix> [<journey_id_prefix> ...]
"""
import json
import sqlite3
import sys

DB = "file:///E:/_cmdr_clean_1028_data/citynexus_v3_clean_1028.db?mode=ro"


def rows(con, sql, args=()):
    cur = con.execute(sql, args)
    return [dict(r) for r in cur.fetchall()]


def probe(prefix: str) -> None:
    con = sqlite3.connect(DB, uri=True)
    con.row_factory = sqlite3.Row
    journey = rows(con, "select id, title, city_code, status from journeys where id like ?", (prefix + "%",))
    if not journey:
        print("JOURNEY_NOT_FOUND prefix=" + prefix)
        return
    journey = journey[0]
    print("JOURNEY " + journey["id"][:13] + " title=" + json.dumps(journey["title"], ensure_ascii=False)
          + " city_code=" + str(journey["city_code"]) + " status=" + str(journey["status"]))
    missions = rows(con, "select id, intent_json, status from journey_missions where journey_id = ?",
                   (journey["id"],))
    for mission in missions:
        task = (json.loads(mission["intent_json"] or "{}") or {}).get("goal_task") or {}
        known = [str(k) for k in (task.get("candidate_place_ids") or [])]
        leads = task.get("research_places") or []
        lead_by_id = {}
        for lead in leads:
            for key in ("place_id", "id", "external_id", "amap_id"):
                value = lead.get(key)
                if value:
                    lead_by_id.setdefault(str(value), lead)
        print("  MISSION " + mission["id"][:13] + " status=" + str(mission["status"])
              + " candidate_place_ids=" + str(len(known)) + " research_leads=" + str(len(leads)))
        slots = [(day_i, slot_i, slot)
                 for day_i, day in enumerate((task.get("draft_artifact") or {}).get("days", []))
                 for slot_i, slot in enumerate(day.get("slots", [])) if str(slot.get("title") or "").strip()]
        for day_i, slot_i, slot in slots:
            source = str(slot.get("place_id") or "")
            by_id = rows(con, "select id, city_code, name from places where id = ?", (source,))
            provider, _, external = source.partition(":")
            by_key = rows(con, "select id, city_code, name from places where provider_key = ? and external_id = ?",
                          (provider, source)) or rows(
                              con, "select id, city_code, name from places where provider_key = ? and external_id = ?",
                              (provider, external))
            lead = lead_by_id.get(source)
            canonical = str((lead or {}).get("canonical_place_id") or "")
            by_canonical = rows(con, "select id, city_code, name from places where id = ?", (canonical,)) if canonical else []
            path = []
            if source in known and by_id:
                path.append("site_258_candidate_id")
            if not by_id and not by_key and lead is None:
                path.append("no_binding_at_all")
            if by_canonical:
                path.append("site_268_lead_canonical")
            if by_key:
                path.append("site_274_provider_key_with_city_filter")
            bound = (by_id or by_key or by_canonical or [{}])[0]
            mismatch = bool(bound.get("city_code")) and str(bound.get("city_code")) != str(journey["city_code"])
            print("   slot " + str(day_i) + ":" + str(slot_i) + " title=" + json.dumps(str(slot.get("title"))[:14], ensure_ascii=False)
                  + " place_id=" + source[:26]
                  + " in_known=" + str(source in known)
                  + " by_id=" + str(len(by_id)) + " by_key=" + str(len(by_key))
                  + " lead=" + str(bool(lead)) + " lead_region=" + str((lead or {}).get("region_status"))
                  + " canonical_rows=" + str(len(by_canonical))
                  + " bound_city=" + str(bound.get("city_code")) + " MISMATCH=" + str(mismatch)
                  + " via " + ",".join(path))
        pool = rows(con, "select count(*) as n from places where city_code = ?", (journey["city_code"],))
        print("  PLACES_IN_THIS_CITY_POOL " + str(pool[0]["n"]))
    con.close()


def main() -> int:
    prefixes = sys.argv[1:]
    if not prefixes:
        print("NO_ARG usage: _bg_probe_city_refusal_r111.py <journey_id_prefix> ...")
        return 4
    for prefix in prefixes:
        probe(prefix)
    return 0


if __name__ == "__main__":
    sys.exit(main())
