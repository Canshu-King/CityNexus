"""HJ-P2 isolation receipt probe - re-runnable, one process per run.

Shape follows the standard HJ-P1 established under ORD-0223 and the Commander's 23:20 note:
every run stamps its own identity (label, local + UTC start, python/sqlite version, host, pid,
argv) so two runs of the same store are byte-different while their verdict fields must be
identical. A receipt that cannot distinguish "two runs" from "one run copied twice" is not a
receipt.

Read-only: sqlite URI mode=ro only; no write statement, no pragma that mutates.

Usage: hjp2_isolation_probe.py --label runX [--db PATH] [--out PATH]
"""
import argparse
import datetime as dt
import getpass
import hashlib
import json
import os
import platform
import socket
import sqlite3
import sys

COUNTERS = ("journeys", "travelers", "plan_versions", "commitments", "constraints", "bookings")
MY_ID_PREFIXES = ("f34c8ff0", "68f8c7a1", "5e9fd913")
STORES = {
    "own_copy": r"D:/moodle/_qoder_hjp2_r6_20260922/_hjp2_r6.db",
    "shared_cmdr_gate__live": r"D:/moodle/_qoder_cmdr_gate_20260921/backend/_live.db",
    "shared_preview__preview": r"D:/moodle/_qoder_preview_20260920/_preview.db",
}


def now_pair():
    loc = dt.datetime.now().astimezone()
    return loc.isoformat(timespec="seconds"), loc.astimezone(dt.timezone.utc).isoformat(timespec="seconds")


def stat_trio(path):
    out = {}
    for suf in ("", "-wal", "-shm"):
        p = path + suf
        if os.path.exists(p):
            st = os.stat(p)
            out[suf or "-main"] = {"bytes": st.st_size, "mtime": dt.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")}
        else:
            out[suf or "-main"] = None
    return out


def probe_store(path):
    rec = {"path": path, "exists": os.path.exists(path)}
    if not rec["exists"]:
        return rec
    rec["stat_before"] = stat_trio(path)
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        rec["table_count"] = len(tables)
        rec["counts"] = {t: (con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] if t in tables else "NO_TABLE") for t in COUNTERS}
        rec["journey_ids"] = [r[0][:8] for r in con.execute("SELECT id FROM journeys ORDER BY created_at")]
        rec["places_by_city_code"] = {r[0]: r[1] for r in con.execute("SELECT city_code, count(*) FROM places GROUP BY city_code ORDER BY 2 DESC") if "places" in tables}
    finally:
        con.close()
    rec["stat_after"] = stat_trio(path)
    rec["main_file_unchanged_by_probe"] = rec["stat_before"]["-main"] == rec["stat_after"]["-main"]
    rec["my_ids_present"] = [m for m in MY_ID_PREFIXES if any(m in j for j in rec["journey_ids"])]
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--db", default=None, help="optional extra store to probe (read-only)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    start_local, start_utc = now_pair()
    stores = {k: probe_store(v) for k, v in STORES.items()}
    if a.db:
        stores["cli_supplied"] = probe_store(a.db)

    own = stores["own_copy"]
    shared = {k: v for k, v in stores.items() if k.startswith("shared")}
    verdict = {
        "own_copy_writable_by_this_lane": True,
        "my_ids_present_in_own_copy": own.get("my_ids_present"),
        "my_ids_present_in_any_shared_store": sorted({m for v in shared.values() for m in v.get("my_ids_present", [])}),
        "shared_main_files_unchanged_by_probe": {k: bool(v.get("main_file_unchanged_by_probe")) for k, v in shared.items()},
        "all_shared_stores_untouched": all(not v.get("my_ids_present") for v in shared.values()) and all(v.get("main_file_unchanged_by_probe") for v in shared.values()),
    }
    out = {
        "receipt": "hjp2_isolation_probe",
        "session": "d4b04a0f",
        "lane": "HJ-P2 commitment-intensive traveller",
        "run": {
            "label": a.label,
            "started_at_local": start_local,
            "started_at_utc": start_utc,
            "argv": sys.argv[1:],
            "pid": os.getpid(),
            "host": socket.gethostname(),
            "user": getpass.getuser(),
            "python": sys.version.split()[0],
            "sqlite_library": sqlite3.sqlite_version,
            "platform": platform.platform(),
            "cwd": os.getcwd(),
        },
        "open_mode": "sqlite URI mode=ro (no write statement issued by this process)",
        "own_store": STORES["own_copy"],
        "counters_reported": list(COUNTERS),
        "stores": stores,
        "verdict": verdict,
    }
    # verdict-only digest: identical across independent runs while the file itself differs
    vb = json.dumps(verdict, ensure_ascii=False, sort_keys=True).encode()
    out["verdict_sha256"] = hashlib.sha256(vb).hexdigest()
    txt = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True)
    dst = a.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "pub", f"isolation_probe_{a.label}.json")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(txt + "\n")
    print("WROTE", dst, len(txt) + 1, "B")
    print("run", a.label, "pid", out["run"]["pid"], "started_utc", start_utc)
    print("verdict_sha256", out["verdict_sha256"][:16], "all_shared_untouched", verdict["all_shared_stores_untouched"])
    print("own_counts", json.dumps(own["counts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
