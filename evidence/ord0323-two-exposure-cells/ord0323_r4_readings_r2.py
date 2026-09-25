"""ORD-0323 requirement (3), in the ruler that supersedes the one the order named.

S4's ORD-0322 delivered `ui_exposure_taint_ast_r1.cjs` (blob eb262f59e54d5142ad0e8041704e751eac473ace), an
AST taint ruler that decides only at DOM sinks; its own receipt proves 21 of r3's full-tree lines are not
sinks at all. r3 is pattern-bound per line, r4 is sink-bound per flow -- so a cell is only closed when the
newer ruler agrees. Both are run here on the two generations, from `git show`, never from the working tree.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0323_20260926")
R4 = pathlib.Path(r"D:\moodle\_qoder_spike_20260921\ui_exposure_taint_ast_r1.cjs")
R4_BLOB = "eb262f59e54d5142ad0e8041704e751eac473ace"
BASE = "9a669c8bec863fadf31d5158f4a1be66aec49f23"
CAND = subprocess.run(["git", "-C", str(LANE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
PATHS = {"ProductErrorBoundary.tsx": "frontend/src/components/ProductErrorBoundary.tsx",
         "JourneyInboxWorkbench.tsx": "frontend/src/features/inbox/JourneyInboxWorkbench.tsx",
         "PlanWithAiSheet.tsx": "frontend/src/features/planning/PlanWithAiSheet.tsx"}
OUT = WORK / "r3"


def show(ref, path):
    return subprocess.run(["git", "-C", str(LANE), "show", f"{ref}:{path}"],
                          capture_output=True, check=True).stdout


def materialize(ref, tag):
    files = []
    for name, path in PATHS.items():
        body = show(ref, path)
        f = OUT / f"{name}__{tag}.tsx"
        f.write_bytes(body)
        assert f.read_bytes() == body
        files.append(f.name)
    return files


def run(files, out_name):
    # the ruler resolves --file against its own process cwd, and subprocesses do not inherit the `cd`
    # of the shell line that started this script -- so hand it the same cwd it would have had.
    p = OUT / out_name
    r = subprocess.run(["node", str(R4), "--file", ",".join(files), "--out", str(p)],
                       cwd=str(OUT),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    if r.returncode != 0 or not p.exists():
        raise SystemExit("r4 did not answer: rc=" + str(r.returncode) + (r.stderr or "")[-300:])
    return json.loads(p.read_text(encoding="utf-8"))


def cells(body):
    return sorted("%s@%s:%d[%s]" % (h["rule"], h["file"].split("__")[0], h["line"], h.get("sink"))
                  for h in body["hits"])


def shapes(body):
    """Identity without the line number: a sink stays the same sink when lines are added above it."""
    return sorted("%s@%s[%s]" % (h["rule"], h["file"].split("__")[0], h.get("sink"))
                  for h in body["hits"])


def per_file(body):
    out = {}
    for h in body["hits"]:
        out.setdefault(h["file"].split("__")[0], []).append(h["line"])
    return {k: sorted(v) for k, v in out.items()}


git_blob = subprocess.run(["git", "-C", str(LANE), "hash-object", str(R4)], capture_output=True,
                          text=True).stdout.strip()
if git_blob != R4_BLOB:
    raise SystemExit(f"the ruler I am holding is not the published one: {git_blob}")
selftest = json.loads((OUT / "r4_selftest.json").read_text(encoding="utf-8")) if (OUT / "r4_selftest.json").exists() else None
before = run(materialize(BASE, "base"), "r4_before_base.json")
after = run(materialize(CAND, "cand"), "r4_after_candidate.json")
b, a = cells(before), cells(after)
bs, as_ = shapes(before), shapes(after)
pf_b, pf_a = per_file(before), per_file(after)
paired = []
for name in sorted(set(pf_b) | set(pf_a)):
    paired.append({"file": name, "lines_before": pf_b.get(name, []), "lines_after": pf_a.get(name, []),
                   "shift_if_same_count": (pf_a.get(name, [None])[0] - pf_b.get(name, [None])[0])
                   if len(pf_b.get(name, [])) == len(pf_a.get(name, [])) and pf_b.get(name) else None})
report = {
    "schema": "CNX_ORD0323_R4_READINGS_R1", "order": "ORD-0323", "lane": "B c01d72a3",
    "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "ruler": {"path": "live_checks/ui_exposure_taint_ast_r1.cjs", "published_blob": R4_BLOB,
              "local_git_hash_object": git_blob, "typescript": before["typescript"],
              "supersedes": "44e062e6ce9c7b5d97d78e09e432072da102292c",
              "selftest_verdict": selftest["verdict"] if selftest else None,
              "selftest_assertions_met": f"{selftest['n_assertions_met']}/{selftest['n_fixtures']}" if selftest else None},
    "generations": {"before": BASE, "after": CAND},
    "before": {"verdict": before["verdict"], "hit_count": len(before["hits"]), "cells": b,
               "truncated": before["resolution_truncated_total"], "files_failed": before["files_failed"]},
    "after": {"verdict": after["verdict"], "hit_count": len(after["hits"]), "cells": a,
              "truncated": after["resolution_truncated_total"], "files_failed": after["files_failed"]},
    "gone": sorted(set(b) - set(a)), "remaining": sorted(set(a) - set(b)),
    "by_shape_identity": {"before": bs, "after": as_,
                          "cleared": sorted(set(bs) - set(as_)), "still_there": sorted(set(as_))},
    "per_file_lines": paired,
    "traces_remaining": [h["taint_chain"] for h in after["hits"]],
    "reading": (f"sink-bound shapes at the tip {len(b)}, at the candidate {len(a)}; "
                f"by shape identity {len(set(bs) - set(as_))} cleared and {len(set(as_) - set(bs))} new; "
                f"per file {json.dumps([{'f': p['file'], 'before': len(p['lines_before']), 'after': len(p['lines_after'])} for p in paired], ensure_ascii=False)}; "
                f"depth-cut truncation {after['resolution_truncated_total']}"),
    "interpretation_limit": "r4 decides by flow, not by content: a sink that can be handed `error.message` is "
                            "reported no matter what this lane's own error now carries in it. Which sentences "
                            "actually reach the screen is judged by the e2e arms.",
    "claim_kind": "ast_flow_determined", "claimed_result": None, "derived_result": None,
}
txt = json.dumps(report, ensure_ascii=False, indent=1)
(WORK / "ord0323_r4_readings.json").write_text(txt, "utf-8", newline="\n")
print(report["reading"])
print("gone:", json.dumps(report["gone"], ensure_ascii=False))
print("left:", json.dumps(report["remaining"], ensure_ascii=False))
print("ruler selftest:", report["ruler"]["selftest_verdict"], report["ruler"]["selftest_assertions_met"])
print("bytes", len(txt.encode("utf-8")), "sha256", hashlib.sha256(txt.encode("utf-8")).hexdigest()[:12])
