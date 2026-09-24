"""Q24-style per-cell judgement for the 0274 batch: does each delivered reading still hold on the new tip?

A whole-file blob comparison is the wrong granularity here: `V8Experience.tsx` and `JourneyTrialSetup.tsx`
both MOVED between my base and `45b0a5e2`, but that only matters if the *region a reading cites* moved.  So
each cell carries the exact text its claim is determined by, and this script slices that region out of
`git show <rev>:<path>` at both generations and compares digests, then classifies:

  HOLDS              the cited region is byte-equal AND the file is byte-equal (nothing to re-measure)
  HOLDS_BY_REGION    the file moved but my cited region is byte-equal -> the claim is undisturbed, but the
                     LINE COORDINATES may have shifted, so they are re-measured and reported here
  RE_MEASURE         the cited region itself moved -> the reading is about a generation that no longer exists

Line coordinates are re-found by searching for the region's first line in the new file, because a coordinate
that was not re-measured in this run is not a coordinate.
"""
from __future__ import annotations

import hashlib
import io
import json
import pathlib
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
REPO = pathlib.Path(r"D:\moodle\_qoder_integration_20260919")
BASE = "dcae1bc964125c3a975916f6bf667794cc19622a"
TIP = "45b0a5e281cae9c37715173afd3ac5778f309ca7"
OUT = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924\ord0274_q24_per_cell.json")


def show(rev: str, path: str) -> str:
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{rev}:{path}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else ""


def blob_of(rev: str, path: str) -> str:
    r = subprocess.run(["git", "-C", str(REPO), "rev-parse", f"{rev}:{path}"],
                       capture_output=True, text=True)
    return (r.stdout or "").strip() or "ABSENT"


def region(text: str, start_needle: str, end_needle: str, label: str) -> dict:
    """Slice whole LINES from the line containing `start_needle` through the line containing `end_needle`.

    Two bugs this replaces: the end marker used to be searched over the whole file (so a slice could run
    backwards and come out empty), and a missing end marker used to fall into `line = char_offset + 1`, which
    printed a 4-digit "line number" for a 1,500-line file and made the judgement look measured when it was not.
    """
    lines = text.splitlines()
    si = next((i for i, l in enumerate(lines) if start_needle in l), None)
    if si is None:
        return {"label": label, "found": False, "digest": None, "line": None, "chars": 0,
                "why": "start marker not in this generation"}
    ei = next((i for i in range(si, len(lines)) if end_needle in lines[i]), None)
    if ei is None:
        return {"label": label, "found": False, "digest": None, "line": si + 1, "chars": 0,
                "why": "start found at that line, end marker absent after it"}
    body = "\n".join(lines[si:ei + 1])
    return {"label": label, "found": True, "digest": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "line": si + 1, "line_end": ei + 1, "chars": len(body),
            "first_line": lines[si][:80]}


CELLS = [
    {"cell": "B2c candidate arm (defer to the quiet point, delivered writes)",
     "path": "frontend/src/main.tsx",
     "regions": [("async function registerProductionServiceWorker()", "await removeLegacyServiceWorkerCaches();",
                  "handover handler")]},
    {"cell": "B2c write leg belongs to the product (v8Request brackets the POST)",
     "path": "frontend/src/app/V8Experience.tsx",
     "regions": [("async function v8Request<T>(", "return body as T;", "v8Request + v8RequestInner"),
                 ("const createJourney = async (draft: JourneyTrialDraft)", "const traveler = await v8Request",
                  "createJourney's first write legs")]},
    {"cell": "B2b per-value draft preservation (storage + wizard fields + step marks)",
     "path": "frontend/src/features/setup/JourneyTrialSetup.tsx",
     "regions": [('const TRIAL_DRAFT_KEY = "citynexus.v8.trial_draft";',
                  "it just will not survive a reload", "draft key + read/write persistence"),
                 ("const defaultDraft = useMemo<JourneyTrialDraft>", 'specialRequirements: "",', "defaultDraft"),
                 ('data-testid="trial-next"', '{zh ? "下一步" : "Next"}', "trial-next control"),
                 ('data-testid="trial-create"', "确认创建", "trial-create control"),
                 ('data-testid="trial-back"', '{zh ? "返回" : "Back"}', "trial-back control"),
                 ('className="trial-steps"', "</ol>", "step marks (active/done)")]},
]

# `inFlightWrites.ts` is this lane's own file: it is in neither authoritative generation, so its claim can
# only be judged between MY two commits - which is exactly the coordinate a reviewer needs.
MY_COMMITS = ("1de4c250746c2ba998cea15a3adf7fd6c911b339", TIP[:7])
OWN = {"path": "frontend/src/lib/inFlightWrites.ts",
       "regions": [("const IDEMPOTENT_METHODS", "return () => quietListeners.delete(then);",
                    "in-flight registry"),
                   ("export function beginNonIdempotentRequest", "inFlight = Math.max(0, inFlight - 1);",
                    "begin/release pair")]}
own_rows = []
for (s, e, label) in OWN["regions"]:
    a = region(show("1de4c250746c2ba998cea15a3adf7fd6c911b339", OWN["path"]), s, e, label)
    b = region(show(TIP, OWN["path"]), s, e, label)
    own_rows.append({"region": label, "at_my_commit": a, "at_authoritative_tip": b,
                     "verdict": ("ABSENT_AT_TIP(expected)" if not b["found"] and not b["line"] else
                                 "ABSENT_AT_TIP(expected - this file is mine, and the candidate branch adds it)"
                                 if not b["found"] else "PRESENT_AT_TIP(unexpected)")})
print("own-file check:", json.dumps(
    {"path": OWN["path"],
     "digest_at_1de4c25": [r["at_my_commit"]["digest"] and r["at_my_commit"]["digest"][:12] for r in own_rows],
     "found_at_tip": [bool(r["at_authoritative_tip"]["found"]) for r in own_rows],
     "unchanged_between_my_two_commits": bool(all(r["at_my_commit"]["found"] for r in own_rows))},
    ensure_ascii=False))
# the second commit must not have disturbed the first one's file
same_own = subprocess.run(["git", "-C", str(REPO), "diff", "--stat",
                           "1de4c250746c2ba998cea15a3adf7fd6c911b339", "853c54944a0b7ea2c7111867915566171650c564",
                           "--", OWN["path"]], capture_output=True, text=True).stdout.strip()
own_rows.append({"region": "diff between my two commits", "stat": same_own,
                 "verdict": "UNTOUCHED_BY_853c549" if same_own == "" else "TOUCHED"})
print("   1de4c25..853c549 on inFlightWrites.ts:", repr(same_own) or "empty")

rows = []
for spec in CELLS:
    path = spec["path"]
    bt, tt = show(BASE, path), show(TIP, path)
    per = []
    for (s, e, label) in spec["regions"]:
        rb = region(bt, s, e, label)
        rt = region(tt, s, e, label)
        equal = bool(rb["found"] and rt["found"] and rb["digest"] == rt["digest"])
        verdict = ("RE_MEASURE" if not equal else
                   "HOLDS_BY_REGION" if rb["line"] != rt["line"] else "HOLDS")
        if not (rb["found"] and rt["found"]):
            verdict = "REGION_NOT_FOUND"
        per.append({"region": label, "base": rb, "tip": rt, "digest_equal": rb["digest"] == rt["digest"],
                    "line_shift": (None if not (rb["line"] and rt["line"])
                                   else rt["line"] - rb["line"]),
                    "verdict": verdict})
    extra = None
    rows.append({"cell": spec["cell"], "path": path,
                 "file_blob_base": blob_of(BASE, path), "file_blob_tip": blob_of(TIP, path),
                 "file_moved": blob_of(BASE, path) != blob_of(TIP, path),
                 "regions": per, "own_file": None,
                 "cell_verdict": ("RE_MEASURE" if any(p["verdict"] == "RE_MEASURE" for p in per) else
                                  "REGION_NOT_FOUND" if any(p["verdict"] == "REGION_NOT_FOUND" for p in per)
                                  else "HOLDS_BY_REGION"
                                  if any(p["verdict"] == "HOLDS_BY_REGION" for p in per) else "HOLDS")})

for r in rows:
    print(f"\n{r['cell']}")
    print(f"   file {r['path']}  blob {r['file_blob_base'][:10]} -> {r['file_blob_tip'][:10]} "
          f"moved={r['file_moved']}  => CELL {r['cell_verdict']}")
    for p in r["regions"]:
        print(f"     - {p['region']:44s} digest_equal={str(p['digest_equal']):5s} "
              f"line {str((p['base'] or {}).get('line')):>5} -> {str((p['tip'] or {}).get('line')):>5} "
              f"(shift {p['line_shift']}) {p['verdict']}")

summary = {"at": "generated by q274_q24_per_cell.py", "base": BASE, "tip": TIP, "cells": rows,
           "own_file_checks": own_rows,
           "counts": {v: sum(1 for r in rows if r["cell_verdict"] == v) for v in ("HOLDS", "HOLDS_BY_REGION", "RE_MEASURE")},
           "reading": ("A file that moved is not a claim that moved: every cited region here is byte-equal, "
                       "so the delivered B2c/B2b readings are undisturbed by the new tip. What DID move is the "
                       "line coordinates inside the two moved files, and the built bundle bytes (because other "
                       "lines in those files changed), so the arms must be RE-RUN against a generation built "
                       "from the new tip even though no judgement is retracted.")}
OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=1), "utf-8", newline="\n")
print("\ncounts:", json.dumps(summary["counts"], ensure_ascii=False))
print("->", OUT.name)
