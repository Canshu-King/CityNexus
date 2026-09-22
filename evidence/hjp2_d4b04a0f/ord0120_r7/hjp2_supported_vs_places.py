"""HJ-P2 finding d4b04a0f/01 as a machine check - no browser needed, re-runnable.

Two facts are compared:
  (a) the destination names the wizard advertises under 「看支持的目的地」, parsed out of the
      frontend source (the list is derived from CITY_FACTS, i.e. country/timezone/currency
      knowledge, not from whether the store holds any place rows);
  (b) which city_codes actually have rows in `places`, read from a store in mode=ro.
It then prints, for every journey this lane created through the visible wizard, the city_code
that journey ended up with and how many places exist for that code - so the mismatch is derived
from data rather than transcribed from a screenshot.

Usage: hjp2_supported_vs_places.py [--store PATH] [--src PATH] [--out PATH]
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import socket
import sqlite3
import sys

DEF_STORE = r"D:/moodle/_qoder_cmdr_gate_20260921/backend/_live.db"
DEF_SRC = r"D:/moodle/_qoder_integration_20260919/frontend/src/features/setup/JourneyTrialSetup.tsx"
LANE_JOURNEYS = {
    "f34c8ff0": "杭州 typed at the destination field (round 6)",
    "68f8c7a1": "苏州 typed at the destination field (round 6)",
    "5e9fd913": "北京 typed at the destination field (round 7)",
}
OWN_COPY = r"D:/moodle/_qoder_hjp2_r6_20260922/_hjp2_r6.db"


def blob_sha1(path):
    b = open(path, "rb").read()
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest(), len(b)


def advertised_zh(src):
    """CITY_FACTS keys are the source of SUPPORTED_CITIES (JourneyTrialSetup.tsx:163-168)."""
    text = open(src, encoding="utf-8").read()
    m = re.search(r"const CITY_FACTS[^=]*=\s*\{(.*?)\n\};", text, re.S)
    if not m:
        return None, None
    keys = re.findall(r'^\s*"([^"\x00-\x7F]+)"\s*:', m.group(1), re.M)
    line = text[: m.start()].count("\n") + 1
    return keys, line


def places_by_code(store):
    con = sqlite3.connect(f"file:{store}?mode=ro", uri=True)
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "places" not in tables:
            return None, None, None
        by = {r[0]: r[1] for r in con.execute("SELECT city_code, count(*) FROM places GROUP BY city_code")}
        rows = con.execute("SELECT id, city_code, title FROM journeys ORDER BY created_at").fetchall()
        return by, rows, len(tables)
    finally:
        con.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default=DEF_STORE)
    ap.add_argument("--src", default=DEF_SRC)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    names, src_line = advertised_zh(a.src)
    sha_src, src_bytes = blob_sha1(a.src)
    by, rows, tc = places_by_code(a.store)
    by_own, rows_own, _ = places_by_code(OWN_COPY)

    lanes = []
    for prefix, how in LANE_JOURNEYS.items():
        hit = next((r for r in (rows_own or []) if r[0].startswith(prefix)), None)
        if not hit:
            lanes.append({"journey_prefix": prefix, "found_in_own_copy": False})
            continue
        code = hit[1]
        lanes.append({
            "journey_id_prefix": prefix,
            "how_created": how,
            "city_code_stored": code,
            "code_was_typed_verbatim": bool(re.search(r"[一-鿿]", code or "")),
            "places_for_that_code_own_copy": (by_own or {}).get(code, 0),
            "places_for_that_code_served_store": (by or {}).get(code, 0),
        })

    codes_with_places = sorted([k for k, v in (by or {}).items() if v > 0])
    out = {
        "check": "hjp2_supported_vs_places",
        "session": "d4b04a0f",
        "lane": "HJ-P2 commitment-intensive traveller",
        "order": "ORD-0120 / finding d4b04a0f/01",
        "run": {
            "started_at_local": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "started_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "pid": os.getpid(), "host": socket.gethostname(),
            "python": sys.version.split()[0], "sqlite_library": sqlite3.sqlite_version,
            "argv": sys.argv[1:],
        },
        "open_mode": "sqlite URI mode=ro",
        "served_store": a.store,
        "own_copy_store": OWN_COPY,
        "source_under_test": {
            "file": a.src,
            "git_blob_sha1": sha_src,
            "bytes": src_bytes,
            "CITY_FACTS_starts_at_line": src_line,
            "note": "SUPPORTED_CITIES at :163-168 is Object.keys(CITY_FACTS) filtered by script, so the advertised list is country/timezone/currency knowledge, not data coverage",
        },
        "advertised_destinations": {"count": len(names or []), "names": names, "printed_under": "看支持的目的地"},
        "places_coverage_in_served_store": {"distinct_city_codes": len(by or {}), "codes_with_places": codes_with_places, "counts": by, "table_count": tc},
        "this_lanes_journeys_measured": lanes,
        "verdict": {
            "advertised_count": len(names or []),
            "codes_with_any_place_row_in_served_store": len(codes_with_places),
            "mismatch": len(names or []) > len(codes_with_places),
            "invented_city_code_seen": any(l.get("code_was_typed_verbatim") for l in lanes),
            "planner_can_only_answer_cities_in": codes_with_places,
        },
    }
    txt = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True)
    dst = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "pub", "supported_vs_places.json")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "w", encoding="utf-8", newline="\n").write(txt + "\n")
    print("WROTE", dst, len(txt) + 1, "B")
    print(ascii(json.dumps(out["verdict"])))
    print(ascii(json.dumps(lanes)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
