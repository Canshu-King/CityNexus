"""ORD-0556 follow-up, tenth leg: which way do the 163 differing files move?

Leg five measured that of the 6542 paths the two generations share, 163 carry a different blob; it never
said which side is bigger. The direction is the closest measurable proxy for the question the commander
asked (was the live tip pruned, or is it simply an earlier generation): a pruned tree would differ in one
direction at a time, a genuinely older snapshot would mostly be SMALLER on this side.

Read-only: ls-tree both refs, then a cat-file/read per differing path. No ports, no product bytes.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

WT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496")
OUT = WT / "review/ord0556/readouts"
RUN = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
SWEEP_BASE = "4d43f8bc25a1a2f4e4c752afe08851032ab6c71d"


def git(*a: str) -> str:
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
        e.pop(k, None)
    e["NO_PROXY"] = "*"
    r = subprocess.run(["git", "-C", str(WT), *a], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=e)
    if r.returncode != 0:
        raise SystemExit(f"ABORT git {' '.join(a)}: {(r.stderr or '')[:160]}")
    return r.stdout


def main() -> int:
    tip = git("ls-remote", "origin", "HEAD").split()[0]
    refs = {"live_tip": tip, "sweep_base": SWEEP_BASE}

    def tree(ref: str) -> dict[str, str]:
        return {ln.split()[3]: ln.split()[2] for ln in git("ls-tree", "-r", ref).split("\n") if ln.strip()}

    trees = {label: tree(ref) for label, ref in refs.items()}
    live, old = trees["live_tip"], trees["sweep_base"]
    common = sorted(set(live) & set(old))
    differing = [p for p in common if live[p] != old[p]]
    BINARY = (".png", ".jpg", ".jpeg", ".gif", ".ico", ".db", ".woff", ".woff2", ".ttf", ".pdf")
    smaller, larger, same = [], [], []
    binary_skipped = 0
    for p in differing:
        # Reading a PNG as text and counting its "lines" measures the byte soup, not the file: every
        # binary entry was noise in the first run of this leg, so binaries are counted aside.
        if p.lower().endswith(BINARY):
            binary_skipped += 1
            continue
        a = len(git("show", f"{tip}:{p}").splitlines())
        b = len(git("show", f"{SWEEP_BASE}:{p}").splitlines())
        rec = {"path": p, "live_tip_lines": a, "sweep_base_lines": b, "delta": a - b}
        (smaller if a < b else larger if a > b else same).append(rec)
    smaller.sort(key=lambda r: r["delta"])
    larger.sort(key=lambda r: -r["delta"])
    doc = {"generation": {"run": RUN, "live_tip": tip, "sweep_base": SWEEP_BASE, "read_only": True},
           "counts": {"common_paths": len(common), "differing_blobs": len(differing),
                      "binary_skipped": binary_skipped,
                      "text_compared": len(smaller) + len(larger) + len(same),
                      "live_tip_smaller": len(smaller), "live_tip_larger": len(larger),
                      "same_line_count": len(same)},
           "live_tip_smaller_top": smaller[:12], "live_tip_larger_top": larger[:12],
           "verdict": "DIRECTION_READ"}
    OUT.joinpath(f"direction_{RUN}.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    c = doc["counts"]
    print(f"live_tip={tip} sweep_base={SWEEP_BASE}")
    print(f"common={c['common_paths']} differing={c['differing_blobs']} "
          f"tip_smaller={c['live_tip_smaller']} tip_larger={c['live_tip_larger']} same={c['same_line_count']}")
    for r in doc["live_tip_larger_top"][:5]:
        print(f"larger {r['path']} tip={r['live_tip_lines']} sweep={r['sweep_base_lines']}")
    for r in doc["live_tip_smaller_top"][:5]:
        print(f"smaller {r['path']} tip={r['live_tip_lines']} sweep={r['sweep_base_lines']}")
    print("receipt direction_" + RUN + ".json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
