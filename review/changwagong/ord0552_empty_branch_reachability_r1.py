#!/usr/bin/env python3
"""ORD-0552 / 长瓦工 -- can the "missing empty state" branch ever paint?

The order lists five panels whose list render has no empty branch and asks each lane to add one that
carries an action, with both languages coming from the dictionary.  Before writing copy (which would
mean inventing keys this round forbids) this ruler asks the cheaper question per site: what does the
surrounding code say about the empty case?

Three verdicts, all read off the bytes -- nothing is typed in by hand:
  GUARD_SAYS_NONEMPTY  -- an enclosing `X.length > 0 &&` means the `<ul>` only mounts with at least
                          one item, so there is no empty rendering to fill.
  PANEL_UNMOUNTS_WHEN_EMPTY
                        -- an `if (X.length === 0) return null` means the panel is not mounted at all
                          when the list is empty; ORD-0552 forbids turning that into a mount
                          ("那改了产品语义"), so a compliant empty state cannot be added here either.
  NO_GUARD_FOUND        -- nothing above the render line, within WINDOW lines, requires a non-empty
                          array.  A live gap only if a caller can actually hand it an empty one --
                          the ruler does not look across files, so that half is reported separately.

Usage: python ord0552_empty_branch_reachability_r1.py --repo D:/moodle/CityNexus --tip <40-hex>
"""

import argparse
import io
import re
import subprocess
import sys

# (file, array whose render the order pointed at) -- the array name is matched on the render line,
# the guard is looked for above it.  Kept as data so a later tip can be re-measured without editing.
SITES = [
    ("frontend/src/features/planning/PlanComparison.tsx", "candidates"),
    ("frontend/src/features/studio/V12TripStudioPanel.tsx", "gateReasons"),
    ("frontend/src/features/agent/AgentRunRail.tsx", "steps"),
    ("frontend/src/features/trip/ActivityDetail.tsx", "nearbyOrdered"),
    ("frontend/src/features/recovery/RecoveryRequiredPanel.tsx", "failures"),
]
WINDOW = 80


def show(repo, tip, path):
    p = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (tip, path)],
                       capture_output=True, shell=False)
    if p.returncode:
        return None
    return p.stdout.decode("utf-8", "replace").split("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--tip", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()

    lines = ["# ORD-0552 长瓦工 -- empty-branch reachability, read off tip=%s" % a.tip]
    tally = {}
    for path, name in SITES:
        body = show(a.repo, a.tip, path)
        if body is None:
            lines.append("MISSING %s | tip=%s" % (path, a.tip))
            tally["MISSING"] = tally.get("MISSING", 0) + 1
            continue
        render = [(i + 1, ln) for i, ln in enumerate(body)
                  if re.search(r"\b%s\.(map|slice)\(" % re.escape(name), ln)]
        if not render:
            lines.append("NO_RENDER %s | array=%s" % (path, name))
            tally["NO_RENDER"] = tally.get("NO_RENDER", 0) + 1
            continue
        rline, rtxt = render[0]
        guard_nonempty = guard_hide = None
        for i in range(rline - 2, max(-1, rline - 2 - WINDOW), -1):
            ln = body[i]
            # The guard may name the array the render line does not: ActivityDetail renders
            # `nearbyOrdered.slice(...)` behind a `nearby.length > 0` guard.  Match any identifier
            # that shares a stem with the render array, and print the name actually found so the
            # reader can judge the pairing instead of trusting this ruler's.
            for ident, op in re.findall(r"\b([A-Za-z_]\w*)\.length\s*(>\s*0|===\s*0)\b", ln):
                related = ident == name or ident.startswith(name) or name.startswith(ident)
                if not related:
                    continue
                g = (i + 1, ln.strip(), ident)
                if op.startswith(">") and guard_nonempty is None:
                    guard_nonempty = g
                if op.startswith("===") and guard_hide is None and re.search(
                        r"if\s*\(\s*%s\.length\s*===\s*0\s*\)\s*return\s+null" % re.escape(ident), ln):
                    guard_hide = g
            if guard_nonempty or guard_hide:
                break
        if guard_hide:
            verdict = "PANEL_UNMOUNTS_WHEN_EMPTY"
            g = guard_hide
        elif guard_nonempty:
            verdict = "GUARD_SAYS_NONEMPTY"
            g = guard_nonempty
        else:
            verdict = "NO_GUARD_FOUND"
            g = (0, "", "")
        tally[verdict] = tally.get(verdict, 0) + 1
        lines.append("%s | %s:%d | render: %s" % (verdict, path, rline, rtxt.strip()[:96]))
        if g[0]:
            lines.append("    guard %s:%d | names=%s | %s" % (path, g[0], g[2], g[1][:96]))
    lines.append("verdicts: " + ", ".join("%s=%d" % (k, v) for k, v in sorted(tally.items())))
    text = "\n".join(lines) + "\n"
    sys.stdout.buffer.write(text.encode("utf-8"))
    if a.out:
        with io.open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
