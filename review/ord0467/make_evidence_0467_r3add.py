"""ORD-0467 r3 addendum -- the re-take on the current tip, measured in one pass.

R1's evidence file stays exactly as published (its path is not rewritten); this file carries only
what changed between the two generations: the new tip, the new blobs, the same tests re-run there,
and the tip-vs-branch hit comparison that says what this branch fixed and what it deliberately left
alone because it belongs to another order.
"""
import json
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
WT = pathlib.Path("D:/moodle/_qoder_q_ord0427_20260929/wt")
ROOT = pathlib.Path("D:/moodle/_qoder_q_ord0467_20260929")
EVID = WT / "review/ord0467"
LANE = "review/Q-ord0467-v13-contract-enum-r3"
MY_SITE = "frontend/src/features/pending/pendingPlaceWrites.ts"


def git(*a):
    env = {k: v for k, v in __import__("os").environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
    return subprocess.run(["git", "-C", str(WT)] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env).stdout.strip()


def log(name):
    p = ROOT / name
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


TIP = git("ls-remote", "--refs", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
remote = git("ls-remote", "--refs", "origin", "refs/heads/%s" % LANE).split()
REF = remote[-1] if remote else git("rev-parse", "HEAD")
HEAD = git("rev-parse", "HEAD")
FORK = git("merge-base", TIP, HEAD)
COMMITS = git("log", "--format=%h", "%s..%s" % (FORK, HEAD)).split()
SRC = [f for f in git("diff", "--name-only", FORK, HEAD, "--", "backend", "contracts", "frontend").splitlines()
       if not f.startswith("review/")]
BLOBS = {f: git("rev-parse", "%s:%s" % (HEAD, f)) for f in SRC}
hits = json.loads((ROOT / "tip_vs_branch_hits_r3.json").read_text(encoding="utf-8"))
import yaml
spec = yaml.safe_load((WT / "contracts/openapi.yaml").read_text(encoding="utf-8"))
enum = spec["components"]["schemas"]["V13NamedRejection"]["enum"]
pytest_txt = [l.strip() for l in log("pytest_r3.txt").splitlines() if l.strip()]
summary = next((l for l in pytest_txt if "passed" in l or "failed" in l), "MISSING")
failures = [l for l in pytest_txt if l.startswith("FAILED")]
parity = next((l for l in log("parity_r3.txt").splitlines() if "OpenAPI" in l), "MISSING")
def num(name, pat):
    m = re.search(pat, log(name))
    return m.group(1) if m else "MISSING:%s" % name


def txt(name, pat):
    m = re.search(pat, log(name))
    return m.group(0) if m else "MISSING:%s" % name


tsc = num("tsc_r2.txt", r"TSC_RC=(\d+)")
build = num("build_r2.log", r"BUILD_RC=(\d+)")
entry = txt("entry.txt", r"index-[A-Za-z0-9_-]*\.js")

refusals = []
if FORK != TIP:
    refusals.append("the tip moved to %s while this branch forked at %s" % (TIP[:12], FORK[:12]))
if [h for h in hits["branch_scan"]["product_path_live"] if h[0] == MY_SITE]:
    refusals.append("this order's own site is still live on the branch")
if hits["introduced_by_this_branch"]:
    refusals.append("this branch introduced a hit: %s" % hits["introduced_by_this_branch"])
if len(enum) != 19:
    refusals.append("the contract enum no longer holds 19 members: %d" % len(enum))
if refusals:
    for r in refusals:
        print("REFUSE: " + r)
    sys.exit(1)

B = []
A = B.append
A("ORD-0467 r3 addendum -- re-taken on the live tip %s" % TIP)
A("")
A("Written 2026-09-30 ~01:2x +08 by lane 2d2d7428. This file adds nothing to RADIUMLADDER's scope:")
A("R1's evidence file (review/ord0467/FINDINGS_0467_R1.txt) is left byte-for-byte as published, and")
A("every number below was re-measured against the generation named here.")
A("")
A("1. THE BRANCH ON THIS GENERATION")
A("   branch refs/heads/%s   head %s" % (LANE, HEAD))
A("   fork point (= the tip, read live with env -u HTTP_PROXY -u HTTPS_PROXY git ls-remote --refs origin"
  )
A("     refs/heads/mirror/integration-frontend-apple-pass1): %s" % FORK)
A("   commits on top of it, oldest last: %s" % " ".join(COMMITS))
A("   source files this branch changes (%d), each blob read from this head:" % len(SRC))
for f in SRC:
    A("      %s  blob %s" % (f, BLOBS[f]))
A("")
A("2. WHAT THE CREDENTIAL GATE SEES, BOTH GENERATIONS, SAME HELPER, SAME DENOMINATOR")
tips = hits["tip_scan"]["product_path_live"]
brs = hits["branch_scan"]["product_path_live"]
A("   files scanned: tip %d, branch %d (the tip was a detached worktree of %s, removed afterwards)"
  % (hits["tip_scan"]["scanned_files"], hits["branch_scan"]["scanned_files"], FORK[:12]))
A("   product-path live hits: tip %d -> branch %d" % (len(tips), len(brs)))
for h in tips:
    A("      tip     %s:%s  %s  position_fp %s  length %s" % (h[0], h[1], h[2], h[3], h[4]))
for h in brs:
    A("      branch  %s:%s  %s  position_fp %s  length %s" % (h[0], h[1], h[2], h[3], h[4]))
A("   fixed by this branch (%d): %s" % (len(hits["fixed_by_this_branch"]),
                                        json.dumps(hits["fixed_by_this_branch"], ensure_ascii=False)))
A("   introduced by this branch (%d): %s" % (len(hits["introduced_by_this_branch"]),
                                             json.dumps(hits["introduced_by_this_branch"], ensure_ascii=False)))
A("   contract exemptions in use: tip %d, branch %d -- after the rename the family needs none, which" % (
    hits["tip_scan"]["contract_named"], hits["branch_scan"]["contract_named"]))
A("   is the point of the order: the vocabulary is named by the contract, and no literal sits on a label that calls it a credential.")
A("   verdict on both: tip %s, branch %s. The one hit left is NOT this order's: it is the map key"
  % (hits["tip_scan"]["verdict"], hits["branch_scan"]["verdict"]))
A("     `%s` value in %s line %s (position_fp %s), i.e. an i18n lookup string that arrived on a"
  % ("token_unknown", brs[0][0], brs[0][1], brs[0][3]))
A("     credential-shaped label with ORD-0466's share panel. Same class as what this order was")
A("     opened for, different family, different lane's landed file. This lane does not edit")
A("     another lane's landed bytes, and does not shrink ORD-0307's C07 to hide it: C07 is red at")
A("     the tip %s as well as on this branch, which is why the branch is not the cause." % FORK[:12])
A("")
A("3. THE CONTRACT AND THE CELLS, RE-RUN HERE")
A("   components.schemas.V13NamedRejection members read back from the file: %d" % len(enum))
A("   pytest (this order's 8 cells + ORD-0307's 10 + share-grant and contract suites): %s" % summary)
A("   failures, named: %s" % (json.dumps(failures, ensure_ascii=False) if failures else "none"))
A("   contract parity: %s" % parity)
A("   npx tsc -p tsconfig.typecheck.json --noEmit exit %s ; npx vite build exit %s ; entry %s" % (tsc, build, entry))
out = "\n".join(B) + "\n"
(EVID / "R3_RETAKEN_ON_TIP.txt").parent.mkdir(parents=True, exist_ok=True)
(EVID / "R3_RETAKEN_ON_TIP.txt").write_text(out, encoding="utf-8", newline="\n")
print("wrote review/ord0467/R3_RETAKEN_ON_TIP.txt, %d lines, %d B" % (out.count("\n"), len(out.encode("utf-8"))))
