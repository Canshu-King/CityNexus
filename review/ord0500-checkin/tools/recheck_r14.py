"""Re-read the four anchors and the product blobs against the live tip, for the tip as it now stands.

Kept as its own script because the page refuses to post unless this agrees with it: the tip moved four
times during this hand, and a page about "the comment is still true" has to say which tip it checked.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reanchor_r8 as R

TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
REPO = R.REPO if hasattr(R, "REPO") else r"D:/moodle/CityNexus"
WT = R.WT
PATHS = ["backend/app/main.py", "backend/tests/test_qoder_ord0500_journey_refusal.py",
         "contracts/openapi.yaml", "frontend/src/features/checkin/checkinCopy.ts",
         "frontend/src/features/trip/TripItinerary.tsx", "frontend/src/i18n/LocaleContext.tsx"]


def sh(args, cwd=REPO):
    env = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
    env["NO_PROXY"] = "*"
    p = subprocess.run(["git"] + args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=300, env=env)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def show(rev, path):
    rc, out = sh(["show", "%s:%s" % (rev, path)])
    if rc != 0:
        raise SystemExit("ABORT_SHOW %s:%s %s" % (rev, path, out[:160]))
    return out


def show_at(rev, path, cwd=WT):
    """The same read, from a tree chosen by the CALLER: HEAD means different commits in the shared repo
    (another lane's checkout) and in this lane's worktree, and reading the wrong one silently measures a
    comment that is not the one being delivered."""
    rc, out = sh(["show", "%s:%s" % (rev, path)], cwd=cwd)
    if rc != 0:
        raise SystemExit("ABORT_SHOW_AT %s:%s in %s %s" % (rev, path, cwd, out[:160]))
    return out


def main():
    rc, listed = sh(["ls-remote", "--refs", "origin", TIP_REF])
    tip = next((l.split()[0] for l in listed.splitlines() if len(l.split()) == 2), None)
    if not tip:
        raise SystemExit("ABORT_NO_TIP %s" % listed[:160])
    head = sh(["rev-parse", "HEAD"], cwd=WT)[1].strip()
    main_src = show(tip, "backend/app/main.py")
    # the comment being judged is the one THIS ref ships, not the one still sitting on the line: reading
    # both sides off the tip measures the line against itself and reports rot that this hand already
    # fixed, which is how a delivery can be blocked by its own ruler (same defect, same week, tools/r10_block.py)
    spec = show_at("HEAD", "backend/tests/test_qoder_ord0500_journey_refusal.py")
    spec_on_tip = show(tip, "backend/tests/test_qoder_ord0500_journey_refusal.py")
    anchors, span = R.read_anchors(main_src.splitlines())
    cited = {lab: int(re.search(pat, spec).group(1)) for lab, pat in R.PATTERNS}
    cited_on_tip = {lab: (int(re.search(pat, spec_on_tip).group(1)) if re.search(pat, spec_on_tip) else None)
                    for lab, pat in R.PATTERNS}
    eq = {}
    for p in PATHS:
        a = show(tip, p)
        b = sh(["show", "HEAD:%s" % p], cwd=WT)[1]
        eq[p] = {"tip": subprocess.run(["git", "-C", WT, "rev-parse", "%s:%s" % (tip, p)],
                                       stdout=subprocess.PIPE, timeout=120).stdout.decode().strip(),
                 "branch_equal": a == b}
    out = {"tool": os.environ.get("RECHECK_TOOL") or "anchor_recheck_r14", "tip": tip, "branch_head": head,
           "main_lines": len(main_src.splitlines()), "route_span": list(span),
           "anchors": anchors, "cited": cited, "cited_on_tip": cited_on_tip,
           "rot_on_tip": {k: [cited_on_tip[k], anchors[k]] for k in anchors
                          if cited_on_tip[k] != anchors[k]},
           "rot": {k: [cited[k], anchors[k]] for k in anchors if cited[k] != anchors[k]},
           "tip_paths_equal_on_branch": eq}
    dest = os.path.join(R.LANE, "evidence",
                        os.environ.get("RECHECK_OUT") or "day25_anchor_recheck_r14.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("tip=%s rot=%s branch_equal=%s" % (tip[:12], out["rot"],
                                             {k: v["branch_equal"] for k, v in eq.items()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
