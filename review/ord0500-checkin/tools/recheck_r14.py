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


def main():
    rc, listed = sh(["ls-remote", "--refs", "origin", TIP_REF])
    tip = next((l.split()[0] for l in listed.splitlines() if len(l.split()) == 2), None)
    if not tip:
        raise SystemExit("ABORT_NO_TIP %s" % listed[:160])
    head = sh(["rev-parse", "HEAD"], cwd=WT)[1].strip()
    main_src = show(tip, "backend/app/main.py")
    spec = show(tip, "backend/tests/test_qoder_ord0500_journey_refusal.py")
    anchors, span = R.read_anchors(main_src.splitlines())
    cited = {lab: int(re.search(pat, spec).group(1)) for lab, pat in R.PATTERNS}
    eq = {}
    for p in PATHS:
        a = show(tip, p)
        b = sh(["show", "HEAD:%s" % p], cwd=WT)[1]
        eq[p] = {"tip": subprocess.run(["git", "-C", WT, "rev-parse", "%s:%s" % (tip, p)],
                                       stdout=subprocess.PIPE, timeout=120).stdout.decode().strip(),
                 "branch_equal": a == b}
    out = {"tool": os.environ.get("RECHECK_TOOL") or "anchor_recheck_r14", "tip": tip, "branch_head": head,
           "main_lines": len(main_src.splitlines()), "route_span": list(span),
           "anchors": anchors, "cited": cited,
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
