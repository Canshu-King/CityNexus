"""Measure the ledger block with both sentence gauges, then reconcile every ruler run into one manifest.

Two separate things go wrong if this is folded into the main gate: the block's bytes only exist after the
insert, and re-running the gate keeps appending verdicts to the receipt it is measuring.  So the block is
judged here, over the bytes extracted from the ledger, and all runs -- stage a, stage b, this one -- are
listed together with the exact object each one measured.
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
HEAD = "### 1a986a24 HJ-P1 · ORD-0297r @"
GAUGES = [("claim_coordinate_check_r3.py", "e653e597c2e6fd74a5f8d3be65fe60e017b03017"),
          ("claim_coordinate_check_r4b.py", "efa6b7a383e094e2ede89f5dd8565b12feed0171")]


def sha1b(b):
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


# ---- 1. extract my block from the ledger: ends at the next heading, bytes verbatim --------------
rows = io.open(LEDGER, encoding="utf-8", newline="").read().split("\n")
i0 = [n for n, l in enumerate(rows) if l.startswith(HEAD)]
assert len(i0) == 1, "my block heading appears %d times in the ledger" % len(i0)
j = i0[0] + 1
while j < len(rows) and not rows[j].startswith(("### ", "## ")):
    j += 1
block = "\n".join(rows[i0[0]:j])
BF = os.path.join(LANE, "o297r_ledger_block_as_inserted.txt")
io.open(BF, "w", encoding="utf-8", newline="").write(block)
composed = io.open(os.path.join(LANE, "_blk_0297r.md"), encoding="utf-8", newline="").read().rstrip("\n")
block_proof = {"ledger_lines": [i0[0] + 1, j], "bytes": len(block.encode("utf-8")),
               "blob40": sha1b(block.encode("utf-8")),
               "identical_to_what_i_composed": block.rstrip("\n") == composed}

# ---- 2. run both sentence gauges over exactly those bytes --------------------------------------
runs = []
for script, blob in GAUGES:
    raw = io.open(os.path.join(LANE, script), "rb").read()
    st = subprocess.run([sys.executable, os.path.join(LANE, script), "--selftest"],
                        capture_output=True, text=True, timeout=300)
    rr = subprocess.run([sys.executable, os.path.join(LANE, script), "--text", BF],
                        capture_output=True, text=True, timeout=300)
    out_name = "gate_%s_on_block_final.txt" % ("r3" if "r3" in script else "r4b")
    io.open(os.path.join(LANE, out_name), "w", encoding="utf-8", newline="").write(rr.stdout)
    import re
    m = re.search(r"claims checked (\d+)( \| exempt (\{[^|]*\}))? \| overall (\S+) \| findings (\S+)",
                  rr.stdout or "")
    runs.append({"script": script, "blob40_expected": blob,
                 "local_bytes": len(raw), "local_sha1_matches_blob_id": sha1b(raw) == blob,
                 "selftest_rc": st.returncode, "rc": rr.returncode,
                 "claims_checked": int(m.group(1)) if m else None,
                 "exempt": m.group(3) if m and m.group(3) else None,
                 "overall": m.group(4) if m else None, "findings": m.group(5) if m else None,
                 "transcript": out_name, "measured_object": os.path.basename(BF),
                 "measured_object_blob40": block_proof["blob40"],
                 "verbatim": rr.stdout})
    print(out_name, "->", (runs[-1]["overall"], runs[-1]["claims_checked"], runs[-1]["findings"]),
          "rc", rr.returncode, flush=True)

# ---- 3. reconcile every ruler run this package makes claim about --------------------------------
ga, gb = {}, {}
for fn, tgt in (("o297r_gate.json", ga), ("o297r_gate_b.json", gb)):
    if os.path.exists(os.path.join(LANE, fn)):
        tgt.update(json.load(io.open(os.path.join(LANE, fn), encoding="utf-8")))


def entry(stage, key, obj):
    d = (stage.get(key) or {}).get(obj)
    if not isinstance(d, dict):
        return None
    s = d.get("parsed") or d.get("summary") or {}
    return {"ruler": {"q38_r2": "receipt_cell_derivation_check_r2.py",
                      "q43_r3": "claim_coordinate_check_r3.py",
                      "q43_r4b": "claim_coordinate_check_r4b.py"}[key],
            "blob40": d.get("blob40"),
            "local_sha1_matches_blob_id": d.get("local_sha1_matches_blob_id"),
            "selftest_rc": d.get("selftest_rc"), "rc": d.get("rc"),
            "cells_found": s.get("cells_found"), "claims_checked": s.get("claims_checked"),
            "overall": s.get("overall"), "hard": s.get("hard"), "soft": s.get("soft"),
            "exempt": s.get("exempt"),
            "findings": s.get("findings"), "judged_object": obj,
            "judged_object_top_level_key_count": d.get("judged_object_top_level_key_count"),
            "judged_object_top_level_keys": d.get("judged_object_top_level_keys")}


all_runs = []
for src, stagename in ((ga, "a (receipt exactly as derived)"),
                       (gb, "b (after stage a's verdicts were appended to it)")):
    frozen = src.get("measured_object_frozen_as")
    r2 = src.get("q38_r2")
    if isinstance(r2, dict):                       # r2 has one result, not a per-target map
        p = r2.get("parsed") or {}
        all_runs.append({"stage": stagename, "ruler": "receipt_cell_derivation_check_r2.py",
                         "blob40": r2.get("blob40"),
                         "local_sha1_matches_blob_id": r2.get("local_sha1_matches_blob_id"),
                         "selftest_rc": r2.get("selftest_rc"), "rc": r2.get("rc"),
                         "cells_found": p.get("cells_found"), "overall": p.get("overall"),
                         "hard": p.get("hard"), "soft": p.get("soft"),
                         "judged_object": frozen,
                         "judged_object_top_level_key_count": r2.get("judged_object_top_level_key_count"),
                         "judged_object_top_level_keys": r2.get("judged_object_top_level_keys")})
    for key in ("q43_r3", "q43_r4b"):
        for obj in (src.get(key) or {}):
            if not isinstance(obj, str):
                continue
            v = entry(src, key, obj)
            if not v:
                continue
            v["stage"] = stagename if obj == frozen else stagename.split(" (")[0] + " (ledger block face)"
            all_runs.append(v)
for r in runs:
    all_runs.append({"stage": "c (block re-measured after the extraction bug was fixed)",
                     "ruler": r["script"], "blob40": r["blob40_expected"],
                     "local_sha1_matches_blob_id": r["local_sha1_matches_blob_id"],
                     "selftest_rc": r["selftest_rc"], "rc": r["rc"],
                     "claims_checked": r["claims_checked"], "exempt": r["exempt"],
                     "overall": r["overall"], "findings": r["findings"],
                     "judged_object": r["measured_object"],
                     "judged_object_blob40": r["measured_object_blob40"]})

out = {"stamped": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
       "block_extracted_from_ledger": block_proof,
       "extraction_bug_named": ("the first block measurement walked 200 ledger lines from my heading, "
                                "so it judged the following lanes' text and printed a RED that was never "
                                "about my block; the extraction now stops at the next heading and writes "
                                "the bytes verbatim (a previous version also let Python flip LF to CRLF, "
                                "so the file judged was not the file inserted). Both stage-b transcripts "
                                "are kept here as they printed, and stage c is the corrected measurement."),
       "runs": all_runs,
       "ruler_copies_are_not_republished": "each ruler is addressed by its 40-hex blob on the arbiter's ref path",
       "q50_scope": ("Q50=1 (issuecomment-5829176662, relayed by the commander): the machine-generated "
                     "table face is RULER_OUT_OF_SCOPE for the sentence gauge -- the JSON runs below are "
                     "published as they printed, without me converting them into a verdict on the cells")}
io.open(os.path.join(LANE, "o297r_ruler_runs.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps({"block": block_proof,
                  "final": [{k: r.get(k) for k in ("stage", "ruler", "overall", "claims_checked",
                                                   "findings", "cells_found", "rc")} for r in all_runs]},
                 ensure_ascii=False, indent=1))
assert all(r["local_sha1_matches_blob_id"] for r in runs), "a gauge ran whose bytes were not the named blob"
