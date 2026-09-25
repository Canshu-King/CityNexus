"""Name the sealed batches so the next shift does not re-run arms that were dropped on purpose.

The commander's suggestion after accepting ORD-0297r: the receipt proves which four rounds are cited, but it
does not show the SHAPE of the superseded batches -- a lane reading only the receipt cannot tell whether the
missing rounds were hidden or deliberately retired.  So this enumerates each sealed batch by directory name,
run id, the instrument bytes that produced it and why it was retired, and proves two things mechanically:
no judged run id appears inside a sealed folder, and every sealed run id is absent from the deriver's glob.

This file is a side-car: the published receipt is not touched, so no ruler has to be re-run for it.
"""
import glob
import hashlib
import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
ROOT = os.path.join(LANE, "o297r_superseded")
REC = json.load(io.open(os.path.join(LANE, "o297r_derived_r1.json"), encoding="utf-8"))
PROV = json.load(io.open(os.path.join(LANE, "o297r_derive_provenance.json"), encoding="utf-8"))

judged = {v["run_id"]: k for k, v in REC["arms"].items()}
folders = sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d)))
batches = []
for f in folders:
    d = os.path.join(ROOT, f)
    note = json.load(io.open(os.path.join(d, "SUPERSEDED.json"), encoding="utf-8"))
    run_ids = note["run_ids"]
    inst = (note.get("instrument_that_produced_them") or {}).get("per_run_fingerprints") or []
    blobs = sorted({i.get("git_blob_sha1") for i in inst if i.get("git_blob_sha1")})
    files = sorted(os.listdir(d))
    # the instrument's identity has to come from the round's OWN run record, which is the only place that
    # says "these bytes launched this session".  The notes also carry a seal-time hash of the file on disk;
    # that number changes as soon as I edit the instrument, so it can never be attributed to a batch.
    prints = []
    for rid in run_ids:
        rp = os.path.join(d, "o297r_run_%s.json" % rid)
        rec = json.load(io.open(rp, encoding="utf-8")) if os.path.exists(rp) else {}
        ins = rec.get("instrument") or {}
        prints.append({"run_id": rid, "git_blob_sha1": ins.get("git_blob_sha1"),
                       "bytes": ins.get("bytes"),
                       "source": "the round's own run record (instrument field written at launch)"
                                 if ins else "NOT RECORDED: this runner did not fingerprint the instrument yet"})
    blobs = sorted({p["git_blob_sha1"] for p in prints if p["git_blob_sha1"]})
    unrecorded = [p["run_id"] for p in prints if not p["git_blob_sha1"]]
    batches.append({
        "folder_name": f,
        "folder_path_relative_to_lane": os.path.join("o297r_superseded", f),
        "name_shape": "batch<N>_<what_the_instrument_lacked>",
        "run_ids": run_ids,
        "arms": [r.split("-")[1] + "-" + r.split("-")[2] for r in run_ids],
        "file_count_in_folder": len(files),
        "artifact_files_per_run": sorted({n.split("_")[1] if n.startswith("o297r_") else n
                                          for n in files if not n.endswith("/")})[:12],
        "instrument_per_run": prints,
        "instrument_git_blob_sha1_all_recorded": (blobs[0] if len(blobs) == 1 else blobs) or None,
        "instrument_fingerprint_unrecorded": unrecorded,
        "seal_time_hash_in_the_note_must_not_be_read_as_the_instrument":
            (note.get("instrument_that_produced_them") or {}).get(
                "hash_of_the_file_at_seal_time_which_is_NOT_this_batch")
            or note.get("lane_cjs_at_seal_time_git_blob_sha1"),
        "why_superseded": note.get("why_superseded"),
        "instrument_change_after": note.get("instrument_change"),
        "corrections_in_this_note": note.get("corrections") or note.get("correction") or [],
        "readings_are_published_in": "SUPERSEDED.json (field readings_of_these_rounds)",
        "cited_by_any_cell": False,
        "measured_by_any_ruler": False})

leak = [j for j in judged for b in batches if j in b["run_ids"]]
glob_now = sorted(os.path.basename(p) for p in glob.glob(os.path.join(LANE, "o297r_run_*.json")))
glob_ids = sorted(g.replace("o297r_run_", "").replace(".json", "") for g in glob_now)
# a sealed round must be invisible to the deriver: if any sealed run id still sits in the lane glob, the
# receipt could be regenerated onto a round that was retired on purpose
sealed_in_glob = sorted({rid for b in batches for rid in b["run_ids"] if rid in glob_ids})

out = {
    "order": "ORD-0297r", "side_car_of": "o297r_derived_r1.json (untouched)",
    "stamped": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "why_this_file_exists": ("the commander accepted the four cited cells and asked that the retired batches "
                            "be named by SHAPE, so a later shift can tell 'deliberately retired' from 'hidden' "
                            "without re-running an arm to find out"),
    "base_tip": REC["base_tip"],
    "judged_runs_in_the_receipt": [{"run_id": rid, "arm": arm} for arm, rid in sorted(judged.items())],
    "sealed_batches": batches,
    "counts": {"batches_sealed": len(batches), "rounds_sealed": sum(len(b["run_ids"]) for b in batches),
               "rounds_judged": len(judged),
               "rounds_total_on_machine": sum(len(b["run_ids"]) for b in batches) + len(judged)},
    "mutual_exclusion": {
        "no_judged_run_id_appears_in_a_sealed_folder": not leak,
        "sealed_run_ids_still_in_the_deriver_glob_must_be_empty": sealed_in_glob,
        "deriver_glob_ids": glob_ids,
        "deriver_glob_now_holds_exactly_the_judged_four": glob_ids == sorted(judged)},
    "how_to_read_a_name": ("batch<N> tells the chronological attempt on this base; the suffix states what the "
                           "INSTRUMENT of that batch could not record -- it is never a product finding. Each "
                           "folder keeps its own SUPERSEDED.json whose readings_of_these_rounds were recomputed "
                           "from those rounds' artifacts at seal time, so a retired round stays auditable."),
    "for_the_next_shift": ("do not re-run these arms to recover a verdict: batch 4 is the only cited one and it "
                           "already answers B3 and A on `dc964086c9d412573ac19d70b24b30e6c3ee6168`. If a new "
                           "claim is needed, it must come with a NEW cell and its own control, not with a "
                           "re-judged round from these folders. Red team signs `derived_result` under ORD-0309; "
                           "the instrument bytes for the cited batch are `bafd7fd335568fd1ec34b86dd42f17a6f2ace643`."),
    "receipt_untouched_therefore_no_ruler_rerun": (
        "this adds no field to o297r_derived_r1.json, so the Q38 r2 reading the commander recomputed (blob "
        "aa13e20472870e4f5b5d5a49d3edf5f6b8b574f2 for the stage-b object) still refers to the same bytes")}
io.open(os.path.join(LANE, "o297r_sealed_batches_r1.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps({"folders": folders,
                  "counts": out["counts"],
                  "mutual_exclusion": out["mutual_exclusion"],
                  "batches": [{"folder_name": b["folder_name"], "run_ids": b["run_ids"],
                               "instrument_git_blob_sha1_all_recorded": b["instrument_git_blob_sha1_all_recorded"],
                               "unrecorded_runs": b["instrument_fingerprint_unrecorded"],
                               "file_count_in_folder": b["file_count_in_folder"]} for b in batches]},
                 ensure_ascii=False, indent=1))
assert not leak, "a judged run id also appears inside a sealed folder"
assert not sealed_in_glob, "a sealed round is still visible to the deriver: %s" % sealed_in_glob
assert glob_ids == sorted(judged), "the deriver glob holds more than the cited four: %s" % glob_ids
assert sum(len(b["run_ids"]) for b in batches) + len(judged) == len(PROV["rounds"]), "batch accounting disagrees"
