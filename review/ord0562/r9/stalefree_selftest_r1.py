# -*- coding: utf-8 -*-
"""A self-test for the readiness ruler that cannot go stale, without editing the ruler.

Why this exists: the published ruler's own self-test pins a fixed (branch, path, base_tip) triple as its
"LANDED must read LANDED" fixture. That file was later changed by another lane on the tip, so the fixture
no longer describes the tip and the self-test prints red -- a fixture aged out, not a deaf ruler. Fixing
that means editing measuring code, which CMDR's no-rewrite rule forbids without a nod, so this file does
not edit it. It imports the published ruler's own `judge()` and supplies fixtures that are true BY
CONSTRUCTION at run time, so none of them can age out:

  MISSING         a path that does not exist in the tip at all -- permanently unresolvable.
  LANDED          branch := the tip itself, so branch blob == tip blob by definition, forever.
  CLEAN           base := the tip, so tip blob == base blob by definition, forever.
  DRIFTED_ON_TIP  base := a recorded older tip and a path the tip has since changed, so tip blob !=
                  base blob; the difference is read from the objects and asserted before the verdict counts.

It also proves it bites: a case that MUST read DRIFTED_ON_TIP and one that MUST read LANDED, and it exits
non-zero if the ruler ever stops discriminating. The ruler is read out of git with cat-file; nothing in
it is executed from a working tree or modified.
"""

import importlib.util
import json
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
RULER_BRANCH = "refs/heads/review/cff87c64-landing-readiness-ruler-r1"
RULER_PATH = "tools/cff87c64_landing_readiness_r1.py"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
OUT = r"D:/moodle/_ord0568_r3/r8/stalefree_selftest_r1.json"

env = dict(__import__("os").environ)
for gone in ("HTTP_PROXY", "HTTPS_PROXY"):
    env.pop(gone, None)


def git(*args):
    proc = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, env=env)
    out = proc.stdout.decode("utf-8", "replace").strip()
    return proc.returncode, out, proc.stderr.decode("utf-8", "replace").strip()


def remote(ref):
    rc, out, err = git("ls-remote", "--refs", "origin", ref)
    assert rc == 0 and out, "cannot read %s: %s" % (ref, err[:120])
    return out.split()[0]


def blob(sha, path):
    rc, out, err = git("rev-parse", "%s:%s" % (sha, path))
    assert rc == 0 and len(out) == 40, "no blob for %s:%s" % (sha, path)
    return out


# --- load the published ruler, unmodified, straight out of git ---
ruler_sha = remote(RULER_BRANCH)
rc, ruler_blob, _ = git("rev-parse", "%s:%s" % (ruler_sha, RULER_PATH))
assert rc == 0
rc, source, err = git("cat-file", "blob", "%s:%s" % (ruler_sha, RULER_PATH))
assert rc == 0 and len(source) > 1000, "cannot read the ruler source: " + err[:120]
extracted = r"D:/moodle/_ord0568_r3/r8/ruler_blob_%s.py" % ruler_blob[:12]
with open(extracted, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(source)
spec = importlib.util.spec_from_file_location("published_readiness_ruler", extracted)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

tip = remote(TIP_REF)
# The authoritative line is a rebuilt, parentless tree, so tip^ does not exist and ancestry says nothing
# here. For the DRIFTED fixture I therefore use a recorded older tip as the base and a path the tip has
# since changed; that difference is read out of the objects, so the fixture is real and does not depend on
# ancestry. The other three fixtures are true by construction (a path that is not there, the tip as its own
# branch, the tip as its own base) and cannot age out.
# The DRIFTED fixture needs a base commit that holds DIFFERENT bytes for a path the tip also holds. The
# mirror tip is parentless (a rebuilt tree), so it has no `tip^` to differ from. Instead, search a list of
# earlier tip commits this lane has recorded in its evidence -- real commits that stay in the object store
# -- and take the first whose bytes for some shared path differ from the tip's. Unlike the ruler's fixed
# fixture, this is re-derived every run and asserts the byte relation before trusting the verdict, so it
# cannot age out the way a pinned fixture did.
RECORDED_OLDER_TIPS = [
    "aac1142e1d25aab0a5bb4fbaa204f3a90668bd0f",
    "8996eee4fb9fb4e159588305223ef421728c4e72",
    "3d40efcc1956f49dcc0679a41995dedc5aae8475",
]

def modified_between(a, b):
    rc, out, err = git("diff", "--diff-filter=M", "--name-only", a, b)
    assert rc == 0, "cannot diff %s %s: %s" % (a[:8], b[:8], err[:120])
    return [p for p in out.split("\n") if p.strip()]

DRIFT_PATH = None
OLDER = None
for cand in RECORDED_OLDER_TIPS:
    rc, _, _ = git("cat-file", "-e", cand)
    if rc != 0:
        continue  # an older tip not fetched locally; skip rather than fail, try the next
    paths = modified_between(cand, tip)
    if paths:
        DRIFT_PATH, OLDER = paths[0], cand
        break
assert DRIFT_PATH and OLDER, (
    "no recorded older tip shares a modified path with this tip (nothing to test)")

# CLEAN: a branch that differs from the tip on a path, with the tip as its own base -> tip==base, branch!=tip
CLEAN_BRANCH = "refs/heads/review/cff87c64-ord0562-english-count-nouns-r8"
CLEAN_PATH = "frontend/src/app/V8Experience.tsx"
assert blob(tip, CLEAN_PATH) != blob(remote(CLEAN_BRANCH), CLEAN_PATH), \
    "the clean path does not actually differ between the tip and the branch"
# LANDED: the tip as its own branch on a path both hold -> branch blob == tip blob
LANDED_PATH = "frontend/src/lib/plural.ts"
assert blob(tip, LANDED_PATH) == blob(remote(CLEAN_BRANCH), LANDED_PATH), \
    "the landed path is not identical between the tip and the branch (LANDED needs branch==tip bytes)"
# DRIFTED: base = an older tip holding different bytes for a path both contain -> tip != base
assert blob(tip, DRIFT_PATH) != blob(OLDER, DRIFT_PATH), "the drift path is not actually different"
STABLE = DRIFT_PATH

GONE = "frontend/src/__no_such_file_stalefree_r1__.tsx"

cases = [
    ("must_read_MISSING", "MISSING", mod.judge("must_read_MISSING", TIP_REF, GONE, tip, tip)),
    # LANDED: branch == tip on a path both hold (identical bytes) -> branch blob == tip blob
    ("must_read_LANDED", "LANDED", mod.judge("must_read_LANDED", TIP_REF, LANDED_PATH, tip, tip)),
    # CLEAN: a real branch that differs from the tip on a path, base == tip -> tip==base, branch!=tip
    ("must_read_CLEAN", "CLEAN", mod.judge("must_read_CLEAN", CLEAN_BRANCH, CLEAN_PATH, tip, tip)),
    # DRIFTED: the older tip is both the branch and the base, and holds different bytes than the tip for a
    # path they share -> branch!=tip and base!=tip, which is exactly the DRIFTED_ON_TIP condition.
    ("must_read_DRIFTED_ON_TIP", "DRIFTED_ON_TIP",
     mod.judge("must_read_DRIFTED_ON_TIP", OLDER, DRIFT_PATH, OLDER, tip)),
]

failures = []
for name, want, row in cases:
    print("%-24s %-16s expected=%s" % (name, row["verdict"], want))
    if row["verdict"] != want:
        failures.append("%s read %s, wanted %s" % (name, row["verdict"], want))

report = {
    "ruler_branch_sha": ruler_sha, "ruler_blob": ruler_blob, "tip": tip, "older_tip_base": OLDER,
    "stable_path_used": STABLE, "cases": [{"name": n, "expected": w, "verdict": r["verdict"],
                                           "reason": r.get("reason")} for n, w, r in cases],
    "failures": failures,
}
with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(report, fh, ensure_ascii=False, indent=1)
print("tip:", tip, "older base:", OLDER)
print("stable path used:", STABLE)
print("wrote", OUT)
for line in failures:
    print("SELFTEST RED: " + line)
sys.exit(3 if failures else 0)
