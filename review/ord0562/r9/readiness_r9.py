# -*- coding: utf-8 -*-
"""Delivery-time readiness for the ORD-0562 r8 open set (five paths, one branch), against the tip the
server holds right now. A caller of the published ruler's own judge(), not a new ruler: the published
blob is read with git cat-file and imported; nothing in it is edited.
"""

import importlib.util
import json
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
RULER_BRANCH = "refs/heads/review/cff87c64-landing-readiness-ruler-r1"
RULER_PATH = "tools/cff87c64_landing_readiness_r1.py"
BRANCH = "refs/heads/review/cff87c64-ord0562-english-count-nouns-r8"
OUT = r"D:/moodle/_ord0568_r3/r8/readiness_r9.json"

env = {"GIT_TERMINAL_PROMPT": "0"}


def git(*args):
    proc = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)
    return proc.returncode, proc.stdout.decode("utf-8", "replace").strip()


rc, head = git("ls-remote", "--refs", "origin", RULER_BRANCH)
assert rc == 0 and head, "ruler branch head unreadable"
ruler_sha = head.split()[0]
rc, blob = git("rev-parse", "%s:%s" % (ruler_sha, RULER_PATH))
assert rc == 0 and len(blob) == 40
rc, source = git("cat-file", "blob", "%s:%s" % (ruler_sha, RULER_PATH))
assert rc == 0 and len(source) > 1000

extracted = r"D:/moodle/_ord0568_r3/r8/ruler_blob_%s.py" % blob[:12]
with open(extracted, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(source)

spec = importlib.util.spec_from_file_location("published_readiness_ruler", extracted)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

tip_sha, why = mod.published_sha(mod.TIP_REF)
assert tip_sha, "tip unreadable: " + str(why)

# base_tip is the tip this branch was cut on; if the tip has moved since, the DRIFTED_ON_TIP verdict is
# the honest one and the branch must be re-cut before landing.
BASE = "79daa3c4ff8f37304d352177b456133d4b9c2a45"
CASES = [
    ("component_v8", "frontend/src/app/V8Experience.tsx"),
    ("count_noun_ruler", "frontend/e2e/qoder-cff87c64-ord0562-english-count-nouns-r1.spec.ts"),
    ("live_recovery", "frontend/src/features/execution/LiveRecovery.tsx"),
    ("simulation_adapter", "frontend/src/features/simulation/simulationAdapter.ts"),
    ("pretrip_checklist", "frontend/src/lib/pretripChecklist.ts"),
]

rows = [mod.judge(name, BRANCH, path, BASE, tip_sha) for name, path in CASES]
counts = {}
for row in rows:
    counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    print("%-22s %-16s %s" % (row["name"], row["verdict"], row["path"]))

selftest = [mod.judge(s["name"], s["branch"], s["path"], s["base_tip"], tip_sha) for s in mod.SELFTEST]
selftest_ok = all(p["verdict"] == s["expect"] for p, s in zip(selftest, mod.SELFTEST))
print("selftest:", [p["verdict"] for p in selftest], "ok=" + str(selftest_ok))
print("tip_sha:", tip_sha, "base_tip:", BASE)
print("counts:", json.dumps(counts, sort_keys=True))

with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump({"tip_sha": tip_sha, "base_tip": BASE, "ruler_blob": blob, "ruler_branch_sha": ruler_sha,
               "branch": BRANCH, "items": rows, "selftest": selftest, "counts": counts,
               "selftest_ok": selftest_ok}, fh, ensure_ascii=False, indent=1)
print("wrote", OUT)
