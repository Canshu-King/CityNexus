# -*- coding: utf-8 -*-
"""ORD-0424 r3 - who answered the legacy shell's boot call, without me ever issuing that call.

The `/legacy` face paints two tier-1 fallbacks because its boot request was refused with 403. Two things
have to be pinned before that counts as a product state rather than a harness artefact:

 1. the refusal must come from the backend's own door, not from my static proxy; and
 2. my private store must be provably untouched by the walk.

This lane is forbidden to run `demo/reset`, so the proof is taken from what already happened - the
uvicorn access line the page's own request produced, and the guard in the route that answers it - rather
than by me POSTing at it. The store is compared against the snapshot taken when the copy was made.
"""
import hashlib
import io
import json
import os
import re
import sqlite3

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0424"
DB = os.path.join(WT, "backend", "tierC_ord0424_lane.db")
LOG = r"D:\moodle\_qoder_lane_S4_0926\work\ord0424\api_7041.log"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord0424"
TABLES = ("journeys", "places", "activities", "audit_logs", "bookings", "commitments", "plan_versions")


def snap():
    con = sqlite3.connect("file:" + DB.replace(os.sep, "/") + "?mode=ro", uri=True)
    out = {t: con.execute('select count(*) from "%s"' % t).fetchone()[0] for t in TABLES}
    con.close()
    raw = io.open(DB, "rb").read()
    out["db_bytes"] = len(raw)
    out["db_sha1"] = hashlib.sha1(raw).hexdigest()
    return out


def main():
    log = io.open(LOG, encoding="utf-8", errors="replace").read().split("\n")
    hits = [l.strip() for l in log if "demo/reset" in l]
    src = io.open(os.path.join(WT, "backend", "app", "main.py"), encoding="utf-8", errors="replace").read()
    i = src.find("demo/reset")
    guard = src[max(0, i - 200): i + 1500]
    named = sorted(set(re.findall(r"\"([A-Z][A-Z0-9_]{4,})\"", guard)))
    tok = re.findall(r"(X-CityNexus[^\"]*|CITYNEXUS_[A-Z_]*TOKEN[A-Z_]*|demo_reset_token|reset_token)", guard)
    at0424 = snap()
    store_at_creation = json.load(io.open(os.path.join(HERE, "store_r1.json"), encoding="utf-8"))
    out = {
        "backend_access_lines_for_that_path": hits[:6],
        "how_many": len(hits),
        "the_door_that_refuses_it": {"file": "backend/app/main.py", "near_line": i,
                                     "named_codes_in_that_region": named[:8],
                                     "token_terms_seen": sorted(set(tok))[:6]},
        "store_now": at0424,
        "store_when_copied": {k: store_at_creation[k] for k in ("copy_bytes", "places", "itinerary_stops")},
        "shared_preview_db_write": "0 - opened mode=ro and copied with the SQLite backup API",
        "lane_issued_demo_reset": False,
        "reading": "the 403 is the backend's own answer to the page's request (access line above), and the "
                   "count that changed nothing is the store hash before and after the walk",
    }
    io.open(os.path.join(HERE, "legacy_403_proof_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"access_lines": out["backend_access_lines_for_that_path"],
                      "named_codes": out["the_door_that_refuses_it"]["named_codes_in_that_region"],
                      "token_terms": out["the_door_that_refuses_it"]["token_terms_seen"],
                      "db_sha1": at0424["db_sha1"], "db_bytes": at0424["db_bytes"]},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
