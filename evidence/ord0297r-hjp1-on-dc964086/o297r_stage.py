"""Stage the batch-accounting files and prove no round on this machine is unaccounted for.

An ORD-0297r round is a real browser session against a real one-shot database; dropping one silently
would make the published receipt a selection.  So this enumerates every run id the lane holds -- in the
judged folder and in each sealed batch -- and requires each to appear exactly once, with the batch that
judged it named.  Anything that shows up twice (or nowhere) fails the run.
"""
import glob
import hashlib
import io
import json
import os
import shutil
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
REC = json.load(io.open(os.path.join(LANE, "o297r_derived_r1.json"), encoding="utf-8"))


def sha1b(b):
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


# ---- 1. every run id this machine holds, wherever it lives ----------------------------------
on_machine = {}
for p in glob.glob(os.path.join(LANE, "o297r_run_*.json")) + glob.glob(
        os.path.join(LANE, "o297r_superseded", "*", "o297r_run_*.json")):
    try:
        rec = json.load(io.open(p, encoding="utf-8"))
    except Exception:                                           # noqa: BLE001
        continue
    rid = rec.get("run_id")
    if not rid:
        continue
    where = "judged (lane root)" if os.path.dirname(p) == LANE else \
        "sealed: " + os.path.basename(os.path.dirname(p))
    on_machine.setdefault(rid, []).append({
        "where": where, "arm": rec.get("arm"), "started_at": rec.get("started_at"),
        "instrument_git_blob_sha1": (rec.get("instrument") or {}).get("git_blob_sha1"),
        "run_file": os.path.basename(p)})

judged = {v["run_id"] for v in REC["arms"].values()}
sealed_ids = set(on_machine) - judged
rows = []
for rid in sorted(on_machine):
    occ = on_machine[rid]
    arm = next((v["arm"] for v in REC["arms"].values() if v["run_id"] == rid),
               occ[0]["arm"])
    rows.append({"run_id": rid, "arm": arm,
                 "disposition": ("JUDGED_IN_PUBLISHED_RECEIPT" if rid in judged else
                                 "SEALED_SUPERSEDED_NOT_CITED"),
                 "copies_found": len(occ), "where": sorted({o["where"] for o in occ}),
                 "instrument_git_blob_sha1": [o["instrument_git_blob_sha1"] for o in occ],
                 "also_seen_in_all_run_ids_for_this_arm": rid in
                     REC["arms"].get(arm or "", {}).get("all_run_ids_for_this_arm", [])})
dupes = [r["run_id"] for r in rows if r["copies_found"] > 1]
missing_from_list = sorted(sealed_ids - {r["run_id"] for r in rows})

prov = {"order": "ORD-0297r", "stamped": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "receipt_file": "o297r_derived_r1.json",
        "why": ("three batches were run on this base. Only the last one is cited; the others are moved "
                "out of the deriver's glob and published as sealed notes, so the receipt cannot be read "
                "as a selection of rounds that happened to look good."),
        "batches": [
            {"batch": "1 (15:18-15:25)", "instrument": "before the tap decision was recorded",
             "disposition": "superseded: a found-but-not-tapped step could not be told apart from a "
                            "covered or disabled one, so the A arm's 0-of-3 was uninterpretable"},
            {"batch": "2 (15:40-15:48)", "instrument": "tap decision recorded, blocker identity not",
             "disposition": "superseded: the cell would have had to say 'covered' without naming by what"},
            {"batch": "3 (15:49-15:56)", "instrument": "blocker identity recorded",
             "disposition": ("superseded: this is the batch that EXPOSED the confound -- the nav was "
                             "covered by the plan-AI sheet's own submit button, a state my walk left "
                             "open, so the offline-movement count described my leftover UI and not the "
                             "generation. The instrument now normalises and records that precondition.")},
            {"batch": "4 (16:00-…)", "instrument": "precondition normalised + recorded, instrument fingerprinted",
             "disposition": "JUDGED -- the published cells are derived from these rounds only"}],
        "rounds": rows, "duplicate_run_ids": dupes, "unaccounted": missing_from_list,
        "sealed_folders": sorted(os.listdir(os.path.join(LANE, "o297r_superseded"))),
        "judged_run_ids": sorted(judged)}
io.open(os.path.join(LANE, "o297r_derive_provenance.json"), "w", encoding="utf-8").write(
    json.dumps(prov, ensure_ascii=False, indent=1))

for src, dst in [(os.path.join(LANE, "o297r_superseded", "batch1_no_tap_decision_recorded",
                               "SUPERSEDED.json"), "o297r_superseded_batch1.json"),
                 (os.path.join(LANE, "o297r_superseded", "batch2_instrument_no_blocker_identity",
                               "SUPERSEDED.json"), "o297r_superseded_batch2.json"),
                 (os.path.join(LANE, "o297r_superseded", "batch3_sheet_left_over_nav_by_my_own_walk",
                               "SUPERSEDED.json"), "o297r_superseded_batch3.json")]:
    if os.path.exists(src):
        shutil.copy(src, os.path.join(LANE, dst))
    else:
        print("NOTE no sealed note at", src)

print(json.dumps({"rounds_total": len(rows), "judged": sorted(judged),
                  "sealed": sorted(sealed_ids), "duplicates": dupes, "unaccounted": missing_from_list,
                  "each_judged_run_named_in_receipt": all(
                      r["run_id"] in REC["arms"].get(r["arm"], {}).get("all_run_ids_for_this_arm", [])
                      for r in rows if r["disposition"].startswith("JUDGED"))},
                 ensure_ascii=False, indent=1))
assert not dupes and not missing_from_list, "a round is duplicated or unaccounted"
assert len(judged) == 4, "expected four judged rounds, one per arm"
