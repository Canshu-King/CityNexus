"""ORD-0504 shared-recipe hand -- what money the day25 shared board actually holds, per journey.

Reads THIS LANE'S consistent copy of the shared board (`ord0504_shared_day25_copy.db`, made by
`copy_shared_board_day25_r1.py` from a `mode=ro` connection) and prints, per journey: which plan
versions exist, which one is active, how many legs / stops / activities it carries, and every money
column with the server's own status word beside it. No judgment here beyond counting rows and reading
the words; the screen judgment is the arms' job.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB = Path("D:/moodle/_qoder_r_ord0465_20260929/run/ord0504_shared_day25_copy.db")
OUT = Path("D:/moodle/_qoder_r_ord0465_20260929/wt/review/ord0504/shared_board_money_census_r1.json")

con = sqlite3.connect("file:%s?mode=ro" % DB.as_posix(), uri=True)
con.execute("PRAGMA query_only=1")
con.row_factory = sqlite3.Row

report = {"source": "consistent sqlite backup of live_checks/_cmdr_canary_day25.db, taken mode=ro",
          "copy": DB.as_posix(), "journeys": [], "money_reality": {}}

for table, column in (("journey_legs", "cost_amount_minor"), ("bookings", "amount_minor"),
                      ("transport_reservations", "price_amount_minor"),
                      ("commitments", "monetary_value_minor")):
    try:
        rows = con.execute("SELECT COUNT(*) AS n, SUM(%s IS NOT NULL) AS with_value FROM %s" % (column, table)).fetchone()
        report["money_reality"][table] = {"rows": rows["n"], "rows_with_" + column: rows["with_value"]}
    except sqlite3.Error as error:
        report["money_reality"][table] = {"error": str(error)}

journeys = con.execute("SELECT id, city_code, status, title, start_at, end_at FROM journeys"
                       " ORDER BY updated_at DESC").fetchall()
for j in journeys:
    entry = dict(j)
    entry["plan_versions"] = [dict(r) for r in con.execute(
        "SELECT id, version_no, status, created_at FROM plan_versions WHERE journey_id=? ORDER BY version_no",
        (j["id"],))]
    active = con.execute("SELECT id, version_no FROM plan_versions WHERE journey_id=? AND status='ACTIVE'"
                         " ORDER BY version_no DESC LIMIT 1", (j["id"],)).fetchone()
    if active is None and entry["plan_versions"]:
        active = con.execute("SELECT id, version_no FROM plan_versions WHERE journey_id=?"
                             " ORDER BY version_no DESC LIMIT 1", (j["id"],)).fetchone()
        entry["active_plan_fallback"] = "no ACTIVE row; newest version_no used"
    entry["active_plan"] = dict(active) if active else None
    plan_id = active["id"] if active else None

    def scalar(sql, args=()):
        row = con.execute(sql, args).fetchone()
        return row[0] if row else None

    entry["counts"] = {
        "activities": scalar("SELECT COUNT(*) FROM activities WHERE plan_version_id=?", (plan_id,)) if plan_id else 0,
        "legs": scalar("SELECT COUNT(*) FROM journey_legs WHERE plan_version_id=?", (plan_id,)) if plan_id else 0,
        "places_in_catalog": scalar("SELECT COUNT(*) FROM places WHERE city_code=?", (j["city_code"],)),
    }
    money = {}
    if plan_id:
        money["legs_of_active_plan"] = [dict(r) for r in con.execute(
            "SELECT sequence_no, mode, cost_amount_minor, currency, cost_status FROM journey_legs"
            " WHERE plan_version_id=? ORDER BY sequence_no", (plan_id,))]
    money["legs_of_this_journey_any_plan"] = [dict(r) for r in con.execute(
        "SELECT plan_version_id, sequence_no, mode, cost_amount_minor, currency, cost_status"
        " FROM journey_legs WHERE journey_id=? ORDER BY sequence_no", (j["id"],))]
    money["bookings_of_this_journey"] = [dict(r) for r in con.execute(
        "SELECT id, status, amount_minor, currency, amount_status FROM bookings"
        " WHERE journey_id=? ORDER BY created_at", (j["id"],))]
    money["commitments_of_this_journey"] = [dict(r) for r in con.execute(
        "SELECT id, kind, status, monetary_value_minor, currency, monetary_value_status"
        " FROM commitments WHERE journey_id=?", (j["id"],))]
    money["reservations_of_this_journey"] = [dict(r) for r in con.execute(
        "SELECT id, status, price_amount_minor, currency, price_status FROM transport_reservations"
        " WHERE journey_id=?", (j["id"],))]
    entry["money"] = money
    report["journeys"].append(entry)

OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
print("money reality across the whole board:", json.dumps(report["money_reality"], ensure_ascii=False))
for e in report["journeys"]:
    print("journey", e["id"][:8], e["city_code"], e["status"], "| plans", len(e["plan_versions"]),
          "| active", (e["active_plan"] or {}).get("version_no"), "| counts", e["counts"],
          "| money rows: legs %d/%d with value, bookings %d, commitments %d, reservations %d" % (len(e["money"]["legs_of_this_journey_any_plan"]), len([m for m in e["money"]["legs_of_this_journey_any_plan"] if m["cost_amount_minor"] is not None]), len(e["money"]["bookings_of_this_journey"]), len(e["money"]["commitments_of_this_journey"]), len(e["money"]["reservations_of_this_journey"])))
print("wrote", OUT)
