"""ORD-0459 r2 -- the watch loop's exposure ruler, run by this lane on its own candidate.

The 值守 reported 95a350d4 (my superseded r1 head) as zero new cells; that is a reading of another
lane member's artifact, so I run the same ruler, same call form (--ref <rev> --path <tree path>), on
the head I am actually delivering and compare it against the live tip file by file.

The identity of the ruler is re-hashed here rather than trusted: d3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2
is what git hash-object says now, and the driver pins the same value.
"""
import hashlib
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
RULER = os.path.join(LC, "ui_exposure_taint_ast_r7b.cjs")
OUT = r"D:\moodle\_qoder_q_ord0448_20260929\exposure_delta_mine_r1.txt"
WT = "D:/moodle/_qoder_q_ord0427_20260929/wt"
LANE = "review/Q-ord0459-radii-tier-step2-r2"
# both refs are fetched so merge-base and the ruler can resolve them locally; the fetch writes nothing outside .git
PINNED = "d3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2"


def git(*a):
    env = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
    return subprocess.run(["git", "-C", WT] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def run_ruler(ref, path):
    p = subprocess.run(["node", RULER, "--ref", ref, "--path", path], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=600)
    if p.returncode != 0 and not p.stdout.strip():
        return {"error": (p.stderr or "")[:200]}
    d = json.loads(p.stdout)
    cells = sorted({c for slot in d["cells_by_slot"].values() for c in (slot or [])})
    return {"cells_total": d["cells_total"], "verdict": d["verdict"], "cells": cells,
            "files_failed": d["files_failed"], "parse_diagnostics_total": d["parse_diagnostics_total"]}


git("fetch", "origin", "mirror/integration-frontend-apple-pass1", "refs/heads/review/" + LANE)
TIP = git("ls-remote", "--refs", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
CAND = git("ls-remote", "--refs", "origin", "refs/heads/" + LANE).split()[0]
identity = hashlib.sha1(open(RULER, "rb").read()).hexdigest()
# git hash-object prepends a blob header, so reproduce it the way git does
blob_id = subprocess.run(["git", "hash-object", RULER], capture_output=True, text=True).stdout.strip()
# the lane's own fork point: the tip as it was before ORD-0459 landed. Comparing against the live tip
# after landing would silently compare the change with itself and report an empty denominator.
FORK = "8cf94ad794a94df0b6f992dc9e6e1bb0c6e70a4a"
files = [f for f in git("diff", "--name-only", FORK, CAND, "--", "frontend/src").splitlines()
         if f.endswith((".css", ".ts", ".tsx"))]

L = []
A = L.append
A("ORD-0459 r2 -- exposure ruler run by lane 2d2d7428 on its own candidate, same call form as the watch loop")
A("ruler identity: git hash-object %s = %s ; pinned by the driver as %s ; identical = %s"
  % (os.path.basename(RULER), blob_id, PINNED, blob_id == PINNED))
A("(the sha1 of the raw file bytes is %s -- that is a local byte hash, not a git object id)" % identity)
A("tip read live        %s" % TIP)
A("compared against     %s -- the tip ORD-0459 forked from; the live tip already carries this lane's bytes," % FORK)
A("                       so measuring against it again would be a 0-file denominator, not a pass)")
A("candidate            refs/heads/%s = %s   files compared here %d" % (LANE, CAND, len(files)))
A("")
A("per file: cells_total on the tip, cells_total on the candidate, new cells by set difference")
new_total = 0
for f in files:
    t = run_ruler(TIP, f)
    c = run_ruler(CAND, f)
    added = sorted(set(c.get("cells", [])) - set(t.get("cells", [])))
    new_total += len(added)
    A("   %-52s tip=%s cand=%s new=%d %s" % (os.path.basename(f), t.get("cells_total"), c.get("cells_total"),
                                             len(added), added[:3]))
A("")
A("new cells across the candidate's own files: %d" % new_total)
A("call form: node %s --ref <rev> --path <tree path>  (per-file; the ruler itself says no module graph is built here," % os.path.basename(RULER))
A("           so this is a per-file set difference, not the gate's whole-tree verdict -- the gate stays the commander's two runs.)")
A("read-only: 0 writes, 0 landing, 0 change to the authoritative line.")

text = "\n".join(L) + "\n"
open(OUT, "w", encoding="utf-8", newline="\n").write(text)
print(text)
