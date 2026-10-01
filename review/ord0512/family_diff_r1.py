"""ORD-0512 family diff r1 -- red sets of two generations, compared as sets of test titles.

Written because the first version of the lane's own parser counted Playwright's *progress* lines
("[5/9] [chromium] › ...") as failures, which turned a 7-red run into a 9-red list: a red set that
includes every test that ran is worse than no red set, because it hides the new one. Only the failure
summary block -- lines indented four spaces, one per red test -- names what was red.

The two sets are printed as sets, not as "no new reds": a generation that inherits fifteen reds from
the tip is not this order's to claim, and one that adds a sixteenth is not either.

usage: python ord0512_family_diff_r1.py <base.log> <candidate.log>
"""
import io
import json
import re
import sys

# Playwright's failure block is four spaces, the project in brackets, `›`, the file:line:col, `›`, then
# the title. The title is taken to end-of-line rather than up to an em dash, because several accepted
# map gates carry an em dash inside their own title -- with the dash as terminator the parser dropped
# those lines silently, and a base run of "15 failed" came out as a six-title set.
BLOCK = re.compile(r"^\s{4}\[([a-z-]+)\] › (\S+) › (\S.*)$", re.M)


def reds(path: str) -> list:
    text = io.open(path, encoding="utf-8", errors="replace").read()
    found = set()
    for project, location, title in BLOCK.findall(text):
        found.add("%s :: %s :: %s" % (project, location.replace("\\", "/"), title.split(" — ")[0].strip()))
    return sorted(found)


def totals(path: str):
    text = io.open(path, encoding="utf-8", errors="replace").read()
    return {kind: int(count) for count, kind in re.findall(r"^\s*(\d+) (passed|failed|flaky|skipped)", text, re.M)}


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    base, cand = reds(sys.argv[1]), reds(sys.argv[2])
    report = {
        "base_totals": totals(sys.argv[1]),
        "candidate_totals": totals(sys.argv[2]),
        "base_red_set": base,
        "candidate_red_set": cand,
        "new_on_candidate": sorted(set(cand) - set(base)),
        "fixed_by_candidate": sorted(set(base) - set(cand)),
    }
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
