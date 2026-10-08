#!/usr/bin/env python3
"""ORD-0415 lane fixture -- put the map's forbidden classes into the words the server sends.

Why this file exists
--------------------
`e2e/_mapLabelRules.ts` (now `src/lib/mapLabelRules.ts`) has said since ORD-0403 that a clock, a
duration, a price and a provider/source string may never be painted on the map glass. ORD-0415's own
measurement (r1) found that nothing on the product path consulted that list, and the reason the finding
was easy to miss is that the acceptance data is clean: every activity title this product seeds
("Old Town Gate", "Riverside Museum", ...) already passes the list, so a gate that counts hits on the
seed reads zero whether the rule is wired or not. A rule with no failing case is not a tested rule.

So the gate needs stop names that DO carry the classes. No public door can produce one: `poi-import/add`
copies `places.name` (the catalog), `catalog-hydrations` takes names from a provider, `plans/generate`
and trip-studio `accept` copy `title` from existing rows, and the inbox path writes reservations, not
plan stops. That leaves the store itself, which is what this helper writes -- against the sqlite file
*this lane's own run created*, never a shared database.

Precedent for a spec moving a row through the store: `e2e/qoder-89f2e2d6-ord0520-abort-on-the-glass-r1.spec.ts`
arm G7 shells out to `CITYNEXUS_PYTHON` with a named helper to move an activity's status mid-test.

Cases
-----
Each case names one *located* stop (a stop the map can put a pin on) and is chosen against the four
patterns in `MAP_LABEL_FORBIDDEN`:

  whole_word_is_a_clock   "19:30"                  -> nothing paintable is left
  clock_inside_word       "天津之眼 19:30 摩天轮"    -> clock out, both name parts stay
  money_inside_word       "瓷房子 门票 ¥60"          -> price out
  duration_inside_word    "五大道 45 分钟 骑行"      -> duration out
  source_inside_word      "海河 © 游船码头"          -> copyright/source out
  clean_control           "古文化街牌坊"             -> must survive untouched

Usage
-----
  python stop_rename_fixture_r1.py --db <sqlite file> --journey <uuid> --apply
  python stop_rename_fixture_r1.py --db <sqlite file> --journey <uuid> --read
  python stop_rename_fixture_r1.py --db <sqlite file> --journey <uuid> --revert

`--apply` records the title it replaced in a plan file next to the database, so `--revert` restores the
exact previous bytes rather than a guess. Reads and reverts are idempotent. Exit codes: 0 ok, 3 the
database or journey is not there, 4 fewer located stops than cases (the gate would be judging less than
it claims).
"""

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

# One row per class the rule names, plus a control that must not be cut.
CASES = [
    ("whole_word_is_a_clock", "19:30"),
    ("clock_inside_word", "天津之眼 19:30 摩天轮"),
    ("money_inside_word", "瓷房子 门票 ¥60"),
    ("duration_inside_word", "五大道 45 分钟 骑行"),
    ("source_inside_word", "海河 © 游船码头"),
    ("clean_control", "古文化街牌坊"),
]


def connect(db: Path) -> sqlite3.Connection:
    """A short busy timeout, because the backend holding this file is the normal case, not a fault:
    the gate writes while its own uvicorn is listening (same shape as the ord0520 G7 arm)."""
    connection = sqlite3.connect(str(db), timeout=30.0, isolation_level="DEFERRED")
    connection.row_factory = sqlite3.Row
    return connection


def located_stops(connection: sqlite3.Connection, journey_id: str) -> list[sqlite3.Row]:
    """Stops on this journey's active plan that the map is able to stand somewhere.

    `MapPanel.activityCoordinate()` needs `location.latitude/longitude`, and the projection builds that
    from the place row, so "located" here means the activity carries a place that carries coordinates.
    Renaming a stop with no position would add a word the glass never shows and quietly shrink the
    denominator the gate reports.
    """
    rows = connection.execute(
        """
        select a.id as activity_id, a.sequence_no, a.title as current_title, a.place_id, p.name as place_name
          from activities a
          join journeys j on j.id = ?
          join plan_versions pv on pv.id = j.active_plan_version_id
          left join places p on p.id = a.place_id
         where a.plan_version_id = pv.id
           and p.latitude is not null
           and p.longitude is not null
         order by a.sequence_no, a.id
        """,
        (journey_id,),
    ).fetchall()
    return rows


def plan_file(db: Path) -> Path:
    return db.with_name(db.name + ".ord0415-plan.json")


def apply(db: Path, journey_id: str) -> int:
    stops = None
    with connect(db) as connection:
        stops = located_stops(connection, journey_id)
    if stops is None:  # pragma: no cover - defensive, connect() raises first
        return 3
    if len(stops) < len(CASES):
        print(json.dumps({
            "ok": False,
            "reason": "fewer located stops than cases",
            "located_stops": len(stops),
            "cases": len(CASES),
        }, ensure_ascii=False))
        return 4
    # Deterministic pairing: the first `len(CASES)` located stops in sequence order.
    targets = list(stops[: len(CASES)])
    # Idempotent: every browser arm of the gate calls this, and a second pass must not record the dirty
    # word it wrote itself as the name to restore. The first plan file's `previous_title` wins.
    previous_plan: dict[str, dict] = {}
    path = plan_file(db)
    if path.exists():
        for row in json.loads(path.read_text(encoding="utf-8")).get("written", []):
            previous_plan[row["activity_id"]] = row
    if previous_plan and {row["activity_id"] for row in targets} != set(previous_plan):
        # The plan file is what `--revert` restores from. Pairing a different set of stops now would
        # leave rows renamed with no record of their original words, so this refuses instead.
        print(json.dumps({
            "ok": False,
            "reason": "the plan file pairs a different set of activities than this apply would",
            "planned": sorted(previous_plan),
            "targets": sorted(row["activity_id"] for row in targets),
        }, ensure_ascii=False))
        return 4
    written = []
    with connect(db) as connection:
        for (case, title), stop in zip(CASES, targets):
            connection.execute("update activities set title = ? where id = ?", (title, stop["activity_id"]))
            carried = previous_plan.get(stop["activity_id"], {})
            written.append({
                "case": case,
                "painted_word": title,
                "activity_id": stop["activity_id"],
                "sequence_no": stop["sequence_no"],
                "previous_title": carried.get("previous_title", stop["current_title"]),
                "previous_place_name": carried.get("previous_place_name", stop["place_name"]),
                "reused_original_title": stop["activity_id"] in previous_plan,
            })
        connection.commit()
    plan_file(db).write_text(json.dumps({"journey_id": journey_id, "written": written}, ensure_ascii=False, indent=1), encoding="utf-8")
    read_back = []
    with connect(db) as connection:
        for row in written:
            current = connection.execute("select title from activities where id = ?", (row["activity_id"],)).fetchone()
            row["title_now"] = current["title"] if current else None
            read_back.append({"case": row["case"], "landed": current["title"] == row["painted_word"] if current else False})
    print(json.dumps({
        "ok": all(item["landed"] for item in read_back),
        "journey_id": journey_id,
        "located_stops_on_plan": len(stops),
        "renamed": len(written),
        "cases": [row["case"] for row in written],
        "titles_now": [row["title_now"] for row in written],
        "read_back": read_back,
        "plan_file": str(plan_file(db)),
    }, ensure_ascii=False))
    return 0


def revert(db: Path) -> int:
    path = plan_file(db)
    if not path.exists():
        print(json.dumps({"ok": True, "reverted": 0, "note": "no plan file: nothing was applied"}))
        return 0
    plan = json.loads(path.read_text(encoding="utf-8"))
    restored = 0
    with connect(db) as connection:
        for row in plan["written"]:
            connection.execute("update activities set title = ? where id = ?", (row["previous_title"], row["activity_id"]))
            restored += 1
        connection.commit()
    check = 0
    with connect(db) as connection:
        for row in plan["written"]:
            current = connection.execute("select title from activities where id = ?", (row["activity_id"],)).fetchone()
            if current and current["title"] == row["previous_title"]:
                check += 1
    path.unlink(missing_ok=True)
    print(json.dumps({"ok": check == restored, "reverted": restored, "restored_exact": check}, ensure_ascii=False))
    return 0


def read(db: Path, journey_id: str) -> int:
    with connect(db) as connection:
        stops = located_stops(connection, journey_id)
    print(json.dumps({
        "located_stops": len(stops),
        "titles": [{"sequence_no": s["sequence_no"], "title": s["current_title"], "place_name": s["place_name"]} for s in stops],
    }, ensure_ascii=False))
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", required=True)
    parser.add_argument("--journey", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--revert", action="store_true")
    parser.add_argument("--read", action="store_true")
    args = parser.parse_args(argv)

    db = Path(args.db)
    if not db.exists():
        print(json.dumps({"ok": False, "reason": f"no such database file: {db}"}), file=sys.stderr)
        return 3
    if args.revert:
        return revert(db)
    if not args.journey:
        print(json.dumps({"ok": False, "reason": "--journey is required for --apply and --read"}), file=sys.stderr)
        return 3
    if args.read:
        return read(db, args.journey)
    # Retry the whole apply once on a locked file: the backend commits on its own schedule and this
    # write is expected to land between its requests, not to fight one.
    for attempt in range(2):
        try:
            return apply(db, args.journey)
        except sqlite3.OperationalError as error:
            if "locked" not in str(error) or attempt == 1:
                raise
            time.sleep(2.0)
    return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
