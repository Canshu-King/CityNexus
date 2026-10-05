# -*- coding: utf-8 -*-
"""Delivery-time readiness for ORD-0562 r6 -- a caller, not a new ruler.

The published ruler (tools/cff87c64_landing_readiness_r1.py on review/cff87c64-landing-readiness-ruler-r1)
is measuring code under CMDR's no-rewrite rule, so its ITEMS list is not edited and nothing in it is
re-run through a copy of its own source. This file imports the published blob's own `judge` and
`published_sha` and asks it one question this lane is allowed to ask at delivery time: is my named file
still a pure apply on the tip as the server holds it right now?

The blob is read out of git with `git cat-file`, never from a working tree, so the bytes being judged are
the bytes the server has.
"""

import importlib.util
import json
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
RULER_BRANCH = "refs/heads/review/cff87c64-landing-readiness-ruler-r1"
RULER_PATH = "tools/cff87c64_landing_readiness_r1.py"

env_clean = None  # proxy is dropped by the caller's environment, see the bash line that runs this


def git(*args):
    proc = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)
    return proc.returncode, proc.stdout.decode("utf-8", "replace").strip()


rc, head = git("ls-remote", "--refs", "origin", RULER_BRANCH)
assert rc == 0 and head, "the ruler branch head could not be read"
ruler_sha = head.split()[0]
rc, blob = git("rev-parse", "%s:%s" % (ruler_sha, RULER_PATH))
assert rc == 0 and len(blob) == 40, "the ruler blob could not be read"
rc, source = git("cat-file", "blob", "%s:%s" % (ruler_sha, RULER_PATH))
assert rc == 0 and len(source) > 1000, "the ruler source could not be read"

extracted = r"D:/moodle/_ord0568_r3/r7/ruler_blob_%s.py" % blob[:12]
with open(extracted, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(source)

spec = importlib.util.spec_from_file_location("published_readiness_ruler", extracted)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

tip_sha, why = module.published_sha(module.TIP_REF)
assert tip_sha, "the tip could not be read: " + str(why)

CASES = [
    {"name": "singular_plural_component_r6",
     "branch": "refs/heads/review/cff87c64-ord0562-english-count-nouns-r6",
     "path": "frontend/src/app/V8Experience.tsx",
     "base_tip": "aac1142e1d25aab0a5bb4fbaa204f3a90668bd0f"},
    {"name": "count_noun_ruler_r6",
     "branch": "refs/heads/review/cff87c64-ord0562-english-count-nouns-r6",
     "path": "frontend/e2e/qoder-cff87c64-ord0562-english-count-nouns-r1.spec.ts",
     "base_tip": "aac1142e1d25aab0a5bb4fbaa204f3a90668bd0f"},
    {"name": "route_provenance_vocabulary",
     "branch": "refs/heads/review/cff87c64-ord0568-route-provenance-gloss-r3",
     "path": "frontend/src/lib/displayVocabulary.ts",
     "base_tip": "eaf4069e5d07a3dacc1ec33a0be515119208e16e"},
    {"name": "route_provenance_panel",
     "branch": "refs/heads/review/cff87c64-ord0568-route-provenance-gloss-r3",
     "path": "frontend/src/features/recovery/V14RecoveryTruthPanel.tsx",
     "base_tip": "eaf4069e5d07a3dacc1ec33a0be515119208e16e"},
]

rows = [module.judge(c["name"], c["branch"], c["path"], c["base_tip"], tip_sha) for c in CASES]
counts = {}
for row in rows:
    counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    print("%-34s %-16s %s" % (row["name"], row["verdict"], row["path"]))

selftest = [module.judge(s["name"], s["branch"], s["path"], s["base_tip"], tip_sha)
            for s in module.SELFTEST]
selftest_ok = all(p["verdict"] == s["expect"] for p, s in zip(selftest, module.SELFTEST))
print("selftest: " + json.dumps([p["verdict"] for p in selftest]) + " ok=" + str(selftest_ok))
print("tip_sha: " + tip_sha)
print("ruler_blob: " + blob)
print("counts: " + json.dumps(counts, sort_keys=True))

with open(r"D:/moodle/_ord0568_r3/r7/readiness_r7.json", "w", encoding="utf-8", newline="\n") as fh:
    json.dump({"tip_sha": tip_sha, "ruler_branch_sha": ruler_sha, "ruler_blob": blob,
               "ruler_path": RULER_PATH, "items": rows,
               "selftest": selftest, "counts": counts, "selftest_ok": selftest_ok},
              fh, ensure_ascii=False, indent=1)

sys.exit(0 if selftest_ok else 3)
