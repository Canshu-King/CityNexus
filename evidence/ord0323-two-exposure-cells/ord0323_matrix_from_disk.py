"""Rebuild ORD-0323's arms matrix from the evidence a completed pass left on disk.

Why this exists: the runner used to filter each arm's readings through a key allow-list written before the
Q68 and Q71 fields existed, so the aggregate silently carried less than the evidence files did -- a receipt
cell could then quote a value the matrix never held. The runner now copies each arm's own body whole
(`ord0323_run_arms_r2.py`), but that fix landed after this pass ran, so this file re-derives the aggregate
for candidate 499522db from that pass's primary records: the reporter JSON per shape, the per-arm evidence
the spec itself wrote, and each declared mutant patch re-applied in memory to hash its bytes and restore
the tree byte-exact. No test is re-executed, and no status is asserted here that is not read from those files.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import ord0323_run_arms_r2 as A  # noqa: E402  (the shapes, anchors and expectations are its, not mine)

WORK = A.WORK
LANE = A.LANE
CAND = subprocess.run(["git", "-C", str(LANE), "rev-parse", "HEAD"], capture_output=True,
                      text=True).stdout.strip()
if CAND != "499522db0903790c3eaba5837bf8e8e3764b7463":
    raise SystemExit(f"HEAD is {CAND[:12]}, not the candidate this pass measured -- refusing to relabel")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def committed(path_in_repo):
    return hashlib.sha256(A.show(CAND, path_in_repo)).hexdigest()


# every shape's own run id, recovered from the reporter files on disk (not from memory)
runs = {}
for shape in A.ORDER:
    # by mtime, not by name: two passes left files like 0323c3b5510 and 0323c3b0043, and lexical order
    # picks the *older* one -- which is how this rebuild first reported the Q68 mutant as not reddening
    # anything, contradicting the live log of the newest pass.
    hits = sorted(WORK.glob(f"ord0323_0323{A.SHORT[shape]}*.json"), key=lambda q: q.stat().st_mtime)
    if not hits:
        raise SystemExit(f"no reporter file for shape {shape}")
    runs[shape] = hits[-1].name[len("ord0323_"):-len(".json")]

shapes, readings, digests = {}, {}, {}
for shape in A.ORDER:
    rid = runs[shape]
    rep = json.loads((WORK / f"ord0323_{rid}.json").read_text(encoding="utf-8"))
    reporter = {}

    def walk(n):
        for s in n.get("suites", []) or []:
            walk(s)
        for sp in n.get("specs", []) or []:
            m = (re.match(r"^(N[123])_", sp.get("title", ""))
                 or re.match(r"^N4_(T\d\d)_", sp.get("title", ""))
                 or re.match(r"^N6_(Q68[ab])_", sp.get("title", "")))
            if not m:
                continue
            for tt in sp.get("tests") or []:
                for res in tt.get("results") or []:
                    reporter.setdefault(m.group(1) or m.group(2), res.get("status"))
    walk({"suites": rep.get("suites") or []})
    ev = WORK / f"e2e_{rid}" / "ord0323"
    rows = {}
    for f in sorted(ev.glob("*.json")) if ev.exists() else []:
        body = json.loads(f.read_text(encoding="utf-8"))
        rows[str(body.get("arm"))] = {k: v for k, v in body.items() if k in A.__dict__.get("KEEP", body)} \
            if False else body
    # the mutant's own bytes, recomputed without running anything: apply, hash, restore
    pristine = A.apply(A.RUNS[shape])
    d = {"boundary": sha(A.BOUNDARY), "workbench": sha(A.WORKBENCH), "sheet": sha(A.SHEET)}
    for p, b in pristine.items():
        p.write_bytes(b)
    ok = (sha(A.BOUNDARY) == committed(A.BOUNDARY_PATH) and sha(A.WORKBENCH) == committed(A.WORKBENCH_PATH)
          and sha(A.SHEET) == committed(A.SHEET_PATH))
    if not ok:
        raise SystemExit(f"the tree did not come back byte-exact after probing {shape}; stopping")
    cfg = A.RUNS[shape]
    per_arm = {a: (rows.get(a) or {}).get("test_status") for a in A.ARMS}
    expect = cfg["expect"]
    meets = all(per_arm.get(a) == ("failed" if want == "failed" else want) for a, want in expect.items())
    shapes[shape] = {"rc": int(rep.get("stats", {}).get("suites") is not None and 1 or 1) if False else
                     (0 if all(v == "passed" for v in per_arm.values()) else 1),
                     "run_id": rid, "report": f"ord0323_{rid}.json",
                     "log": f"ord0323_{rid}.log",
                     "reporter_outcomes": reporter, "per_arm": per_arm, "expected": expect,
                     "intended": cfg.get("intended"),
                     "meets_expectation": meets,
                     "arms_without_a_reading": [a for a in expect if a not in rows],
                     "reporter_and_evidence_agree": all(per_arm.get(a) == reporter.get(a) for a in expect),
                     "mutant_digests": d,
                     "restored_byte_exact": ok}
    readings[shape] = rows
    digests[shape] = d

green_fixed = all(shapes["fixed"]["per_arm"].get(a) == "passed" for a in A.ARMS)
verdict = ("TEETH_AND_BASELINE"
           if green_fixed
           and all(s["meets_expectation"] for s in shapes.values())
           and all(s["arms_without_a_reading"] == [] for s in shapes.values())
           and all(s["reporter_and_evidence_agree"] for s in shapes.values())
           and all(s["restored_byte_exact"] for s in shapes.values())
           else "MATRIX_NOT_AS_EXPECTED")
out = {
    "schema": "CNX_ORD0323_ARMS_R3", "order": "ORD-0323", "lane": "B c01d72a3",
    "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "assembled_from": {
        "pass": "the eight shapes ran once against this candidate; the aggregator of that pass crashed with "
                "UnboundLocalError before writing its file (fixed in ord0323_run_arms_r2.py), so this "
                "aggregate is rebuilt from that pass's primary records",
        "primary_records": ["the Playwright JSON reporter per shape (report/log fields)",
                            "the spec's own per-arm evidence files under e2e_<run_id>/ord0323/",
                            "each declared mutant patch, re-applied in memory to hash its bytes and restored"],
        "nothing_re_executed": True,
        "run_ids": runs},
    "measurement_scope": dict(A.__dict__.get("_", {}), **{
        "generation": {"baseline_named_in_the_order": A.BASE, "candidate": CAND,
                       "candidate_parent": A.PARENT, "pre_fix_blob_source": A.PARENT},
        "tree": str(LANE), "spec": A.SPEC,
        "mode": "CITYNEXUS_E2E_AUTHORITATIVE=1, AI disabled, both servers started by that pass's invocation",
        "database_per_run": "one sqlite file per run id, named by CITYNEXUS_DATABASE_URL"}),
    "files": {"ProductErrorBoundary.tsx": {"candidate_sha256": sha(A.BOUNDARY),
                                           "pre_fix_sha256": hashlib.sha256(A.BASELINE_BOUNDARY).hexdigest()},
              "JourneyInboxWorkbench.tsx": {"candidate_sha256": sha(A.WORKBENCH),
                                            "pre_fix_sha256": hashlib.sha256(A.BASELINE_WORKBENCH).hexdigest()},
              "PlanWithAiSheet.tsx": {"candidate_sha256": sha(A.SHEET),
                                      "pre_fix_sha256": hashlib.sha256(A.BASELINE_SHEET).hexdigest()}},
    "arms": list(A.ARMS), "shapes": shapes, "per_arm_readings": readings,
    "verdict": verdict,
    "interpretation_limit": "statuses are each arm's own self-reported test_status cross-checked against the "
                           "reporter; derived_result stays null, signing a level belongs to the red team (B-1).",
    "claimed_result": None, "derived_result": None,
}
txt = json.dumps(out, ensure_ascii=False, indent=1)
(WORK / "ord0323_arms_matrix_r3.json").write_text(txt, "utf-8", newline="\n")
print("verdict:", verdict, "| bytes", len(txt.encode("utf-8")))
for s in A.ORDER:
    print(f"  {s:24s} red={[a for a, v in shapes[s]['per_arm'].items() if v != 'passed']} "
          f"ok={shapes[s]['meets_expectation']} agree={shapes[s]['reporter_and_evidence_agree']}")
