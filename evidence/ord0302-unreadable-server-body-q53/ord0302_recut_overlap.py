"""Read-only measurement: can the ORD-0302 q53 candidate still land on the authority line, and where exactly?

Why this exists: the commander's knock asked B for the keyless-write-leg deadline cell (he called it ORD-0288)
and told me to cut from `13af1ff`. That cell was already dispatched to D as ORD-0310 (ledger 17:1x), D delivered
it twice (19:54, 20:55), and the commander landed it at `2344145c`. Both candidates edit the SAME product file,
so before anybody merges a second time the shape of the overlap has to be measured, not asserted.

Nothing here moves a ref: `ls-remote` + `fetch` of a commit into FETCH_HEAD + `merge-tree --write-tree`
(which only writes a tree object) + `diff` between blobs.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import pathlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924")
GH = "Canshu-King/CityNexus"
AUTH = "refs/heads/mirror/integration-frontend-apple-pass1"
MYREF = "refs/heads/review/0302-unreadable-server-body-b3"
DREF = "refs/heads/review/ord0310-keyless-deadline-d"
BASE = "13af1ff4ba4516aa1a39cda67428ed4a2a34ac69"
CAND = "2f191eb5fd1682a53cf95f883c7200f00cbb6ebe"
SHEET = "frontend/src/features/planning/PlanWithAiSheet.tsx"
tok = pathlib.Path(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920").read_text(encoding="utf-8").strip()


def g(args, check=True):
    r = subprocess.run(["git", "-C", str(LANE), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} -> rc={r.returncode}: {(r.stderr or '').strip()[:200]}")
    return (r.stdout or "").strip(), r.returncode


def ls_remote(*refs):
    out, _ = g(["ls-remote", f"https://github.com/{GH}.git", *refs])
    return {line.split("\t")[1].strip(): line.split("\t")[0].strip() for line in out.splitlines() if "\t" in line}


def spans(a, b):
    """Base-file line spans each hunk rewrites, from --unified=0 so context lines cannot widen them."""
    out, _ = g(["diff", "--unified=0", a, b])
    got = []
    for m in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+", out, re.M):
        start = int(m.group(1))
        count = int(m.group(2)) if m.group(2) is not None else 1
        got.append([start, start + max(count, 0)])
    return got


remote = ls_remote(AUTH, MYREF, DREF)
tip = remote.get(AUTH, "ABSENT")
if tip == "ABSENT":
    raise SystemExit("the authority line did not answer ls-remote; nothing below is measurable")
g(["fetch", "-q", f"https://github.com/{GH}.git", AUTH])

res = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
       "order": "ORD-0302 q53 candidate vs the landed ORD-0310 -- re-cut surface (read-only)",
       "ls_remote": remote, "authority_tip": tip, "candidate": CAND, "order_base": BASE,
       "base_is_ancestor_of_tip": g(["merge-base", "--is-ancestor", BASE, tip], check=False)[1] == 0,
       "commands": ["git ls-remote https://github.com/%s.git %s %s %s" % (GH, AUTH, MYREF, DREF),
                    "git fetch " + AUTH, "git merge-tree --write-tree %s %s" % (tip, CAND),
                    "git diff --name-only %s %s" % (BASE, tip),
                    "git diff --unified=0 <shared sheet blob> <each side's sheet blob>"]}

mt, mt_rc = g(["merge-tree", "--write-tree", tip, CAND], check=False)
lines = mt.splitlines()
res["merge_tree"] = {"rc": mt_rc, "predicted_tree": lines[0] if lines else "ABSENT",
                     "conflicted_paths": sorted({m.group(1) for m in
                                                 re.finditer(r"^\d{6} [0-9a-f]{40} \d\t(.+)$", mt, re.M)}),
                     "conflict_lines": [l for l in lines if l.startswith("CONFLICT")]}

res["paths_base_to_tip"] = [x for x in g(["diff", "--name-only", BASE, tip])[0].split("\n") if x]
res["paths_base_to_candidate"] = [x for x in g(["diff", "--name-only", BASE, CAND])[0].split("\n") if x]
res["paths_both_sides_edit"] = sorted(set(res["paths_base_to_tip"]) & set(res["paths_base_to_candidate"]))

b = g(["rev-parse", f"{BASE}:{SHEET}"])[0]
d = g(["rev-parse", f"{tip}:{SHEET}"])[0]
m = g(["rev-parse", f"{CAND}:{SHEET}"])[0]
sp_d, sp_m = spans(b, d), spans(b, m)
inter = [[max(x[0], y[0]), min(x[1], y[1])] for x in sp_d for y in sp_m if max(x[0], y[0]) < min(x[1], y[1])]
res["sheet_blobs"] = {"at_order_base": b, "at_authority_tip": d, "at_my_candidate": m,
                      "tip_equals_base": d == b, "candidate_equals_base": m == b}
res["sheet_edit_regions"] = {
    "landed_0310_base_line_spans": sp_d, "my_q53_base_line_spans": sp_m,
    "intersecting_spans": inter,
    "nearest_pair_gap_in_base_lines": min((y[0] - x[1]) for x in sp_d for y in sp_m
                                          if y[0] - x[1] >= 0) if sp_d and sp_m else None,
    "note": "spans are measured against the sheet as it stood at the order's base, so both sides share one ruler"}

res["commits"] = {"base_to_tip": int(g(["rev-list", "--count", f"{BASE}..{tip}"])[0]),
                  "base_to_candidate": int(g(["rev-list", "--count", f"{BASE}..{CAND}"])[0])}
res["verdict"] = ("CONFLICTS_ON_ONE_PATH" if res["merge_tree"]["rc"] != 0
                  else "CLEAN_MERGE_PREDICTED")
out = WORK / "ord0302_recut_overlap.json"
out.write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8", newline="\n")
print(json.dumps(res, ensure_ascii=False, indent=1))
print("\n->", out)
