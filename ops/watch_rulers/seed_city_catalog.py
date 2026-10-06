"""Additively seed the CN-BEIJING catalogue into ONE database file, without `demo/reset`.

Why this exists: `seed_demo()` calls `reset_all()`, which deletes 52 tables — every traveler,
journey, audit row and commitment. On the live preview that is the user's own data, and today
(18:1x) their phone journey 94669bae「北京 · journey」is open against it. So the only supported
way to get Beijing into a running database is measured here as a defect, and this script is the
workaround: insert the same rows `seed_demo()` would write for CN-BEIJING, skip anything already
present, and never delete.

Usage:  python seed_city_catalog.py <db path> [--dry-run]
Prints row counts before/after and the journeys it did not touch.
"""

from __future__ import annotations

import io
import json
import sqlite3
import sys
import time
from pathlib import Path

MOCK = Path(r"D:\moodle\_qoder_cmdr_ref_20260921\data\mock")
DB = sys.argv[1]
DRY = "--dry-run" in sys.argv
CITY = "CN-BEIJING"
NOW = "2026-10-01T00:00:00+00:00"


def rows(table: str) -> list[tuple]:
    return list(con.execute(f"SELECT city_code, count(*) FROM {table} GROUP BY city_code"))


def put(table: str, payload: dict, *, fixed: dict) -> int:
    cols = {r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}
    row = {}
    for key, value in {**payload, **fixed}.items():
        if key not in cols:
            continue
        row[key] = json.dumps(value) if isinstance(value, (dict, list)) else value
    if "id" not in row:
        raise RuntimeError(f"{table}: no id in {payload}")
    if con.execute(f"SELECT 1 FROM {table} WHERE id=?", (row["id"],)).fetchone():
        return 0
    if not DRY:
        con.execute(
            f"INSERT INTO {table} ({', '.join(row)}) VALUES ({', '.join(':' + k for k in row)})",
            row,
        )
    return 1


con = sqlite3.connect(DB, timeout=45)
con.execute("PRAGMA busy_timeout=45000")
print("target:", DB, "dry-run:", DRY)
print("places before:", rows("places"))
print("services before:", rows("city_services"))
print("journeys before:", con.execute(
    "SELECT count(*), group_concat(DISTINCT city_code) FROM journeys").fetchone())

places = [p for p in json.load(io.open(MOCK / "places.json", encoding="utf-8"))
          if p["city_code"] == CITY]
services = [s for s in json.load(io.open(MOCK / "city_services.json", encoding="utf-8"))
            if s["city_code"] == CITY]
added_p = added_s = 0
for item in places:
    added_p += put("places", {
        **item,
        "latitude": item["location"]["latitude"],
        "longitude": item["location"]["longitude"],
        "opening_hours_json": {"open": item["open"], "close": item["close"]},
        "tags_json": item["tags"],
        "metadata_json": {"duration_min": item["duration_min"],
                          "cost_minor": item["cost_minor"]},
    }, fixed={"created_at": NOW, "updated_at": NOW})
for item in services:
    added_s += put("city_services", {**item, "availability_json": item.get("availability", {})},
                   fixed={"created_at": NOW, "updated_at": NOW, "metadata_json": {}})

if DRY:
    con.rollback()
else:
    for attempt in range(3):
        try:
            con.commit()
            break
        except sqlite3.OperationalError as exc:  # the live server may be mid-write
            print(f"commit attempt {attempt + 1} refused: {exc}")
            time.sleep(2)
    else:
        raise SystemExit("could not commit — the database stayed locked")
print(f"added places +{added_p} services +{added_s}")
print("places after:", rows("places"))
print("services after:", rows("city_services"))
print("journeys after:", con.execute(
    "SELECT id, city_code, status FROM journeys").fetchall())
print("integrity:", con.execute("PRAGMA integrity_check").fetchone()[0])
con.close()
