"""Building C cell four: is there ANY real sample that exercises the provider-geometry splice?

Cell three reported BRANCH_NOT_EXERCISED because the canary's stored facts belonged to another trip. The
open question was whether a different journey in the same store would have facts matching its own
consecutive activities. This cell answers it by enumerating every journey that has an active plan and
counting, per journey, how many consecutive activity pairs have a matching `mobility_facts` row.

A zero here is a fact about the sample data, not a measurement failure: it means the splice branch cannot
be covered with real data from this store at all, and stays covered only by the synthetic arm.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sqlite3
from datetime import datetime, timezone

DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0545_data")
OUT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496/review/ord0577/readouts")
CANARY = pathlib.Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/canary_56d20ec.db")
RUN = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    before = sha(CANARY)
    store = DATA / f"_cell4_{RUN}.db"
    shutil.copy2(CANARY, store)
    con = sqlite3.connect(store)
    cur = con.cursor()

    journeys = []
    total_matches = 0
    for jid, plan in cur.execute(
            "select id, active_plan_version_id from journeys "
            "where active_plan_version_id is not null order by id").fetchall():
        acts = [r[0] for r in cur.execute(
            "select a.place_id from activities a where a.place_id is not null "
            "and a.plan_version_id=? order by a.sequence_no", (plan,)).fetchall()]
        pairs = list(zip(acts, acts[1:]))
        matched = [p for p in pairs if cur.execute(
            "select 1 from mobility_facts where journey_id=? and from_key=? and to_key=?",
            (jid, p[0], p[1])).fetchone()]
        # a fact exists for the pair at all (regardless of geometry length)
        with_geom = [p for p in pairs if cur.execute(
            "select geometry_json from mobility_facts where journey_id=? and from_key=? and to_key=?",
            (jid, p[0], p[1])).fetchone()]
        total_matches += len(matched)
        journeys.append({
            "journey": jid, "active_plan": plan,
            "activity_count": len(acts), "consecutive_pairs": len(pairs),
            "pairs_with_matching_fact": len(matched),
            "pairs_with_fact_row": len(with_geom),
            "exercised": len(matched) > 0,
        })
    con.close()

    doc = {
        "generation": {"run": RUN, "store": "copy of commander canary", "read_only": True,
                       "canary_sha_before": before, "canary_sha_after": sha(CANARY),
                       "canary_untouched": sha(CANARY) == before},
        "journeys": journeys,
        "counts": {"journeys_with_active_plan": len(journeys),
                   "journeys_exercising_splice": len([j for j in journeys if j["exercised"]]),
                   "total_matched_pairs": total_matches},
        "verdict": "REAL_SAMPLE_EXISTS" if total_matches else "NO_REAL_SAMPLE_IN_STORE",
    }
    for extra in (store, pathlib.Path(str(store) + "-wal"), pathlib.Path(str(store) + "-shm")):
        try:
            extra.unlink(missing_ok=True)
        except OSError:
            pass

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"provider_sample_census_{RUN}.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    for j in journeys:
        print(f"journey {j['journey']} acts={j['activity_count']} pairs={j['consecutive_pairs']} "
              f"matched={j['pairs_with_matching_fact']} exercised={j['exercised']}")
    print(f"verdict {doc['verdict']} journeys_exercising={doc['counts']['journeys_exercising_splice']} "
          f"total_matched_pairs={doc['counts']['total_matched_pairs']} "
          f"canary_untouched={doc['generation']['canary_untouched']}")
    print("receipt provider_sample_census_" + RUN + ".json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
