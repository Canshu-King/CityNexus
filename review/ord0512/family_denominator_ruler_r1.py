r"""ORD-0512 -- is a family red set a fact about the code, or about the run? r1

A lane that changes the map panel is judged against the accepted map family: run the eighteen specs, take
the set of red tests, compare it with the same run on the line's own bytes. New red means the change broke
something. That denominator was trusted as if it were a measurement of the code, and it is not always one:
this lane read the family twice on the SAME bytes and got 15 red in one round and 17 in the next, and the
two that moved belonged to another order's arm (`reach ... @320`, `reach ... @414` in
`qoder-map-ord0403-named-control-and-labels.spec.ts`), which fails on the area where the basemap notice
overlaps a control -- a notice that only exists when tiles did not load.

So this file turns that observation into an instrument. It reads N family logs and answers one question:
does the red multiset move when nothing changed? Titles are kept whole and compared as multisets, because
cutting at the first em dash collapses `@320`/`@360`/`@390`/`@414` into one name, and a difference of two
then reads as no difference at all.

The comparator is tested against itself with `--selfcheck`, which feeds it three synthetic pairs and
refuses to ship unless it gets them all right -- including the one that must come back STABLE. A ruler
that can only say "moved" is as blind as one that can only say "same".

usage: python ord0512_family_denominator_r1.py --logs <a.log> <b.log> [<c.log> ...]
       python ord0512_family_denominator_r1.py --selfcheck [--out <file.json>]
"""
from __future__ import annotations

import io
import json
import re
import sys
from collections import Counter

# Playwright's failure-summary block: four spaces, the project in brackets, the file:line:col, then the
# title. Progress lines ("[5/18] [chromium] ...") name every test that RAN and must never be read as a
# failure -- that turned a 7-red run into a list of nine once.
BLOCK = re.compile(r"^\s{4}\[([a-z-]+)\] › (\S+) › (\S.*)$", re.M)
TOTAL = re.compile(r"^\s*(\d+) (failed|passed)", re.M)


def reds_from_text(text: str) -> Counter:
    return Counter("%s :: %s" % (location.replace("\\", "/"), title.strip())
                   for _project, location, title in BLOCK.findall(text))


def reds(log_path: str) -> Counter:
    return reds_from_text(io.open(log_path, encoding="utf-8", errors="replace").read())


def totals(log_path: str) -> dict:
    text = io.open(log_path, encoding="utf-8", errors="replace").read()
    found = {word: int(num) for num, word in TOTAL.findall(text)}
    return {k: found.get(k) for k in ("failed", "passed")}


def compare(rounds: Counter) -> dict:
    """rounds maps a label to the multiset of red titles read in that round."""
    labels = sorted(rounds)
    if len(labels) < 2:
        return {"verdict": "NOT_MEASURED", "why": "one log is not a comparison", "rounds": labels}
    if all(rounds[labels[0]] == rounds[lbl] for lbl in labels[1:]):
        return {"verdict": "DENOMINATOR_STABLE",
                "why": "%d rounds read the same multiset" % len(labels),
                "rounds": {lbl: sorted(rounds[lbl]) for lbl in labels},
                "moved_arms": []}
    every = set().union(*[set(rounds[lbl]) for lbl in labels])
    moved = sorted(title for title in every if len({rounds[lbl][title] for lbl in labels}) > 1)
    counts = {lbl: sum(rounds[lbl].values()) for lbl in labels}
    return {"verdict": "DENOMINATOR_UNSTABLE",
            "why": "same bytes, red totals differ across rounds: %s" % json.dumps(counts, ensure_ascii=False),
            "moved_arms": [{"title": title, "per_round": {lbl: rounds[lbl][title] for lbl in labels}}
                           for title in moved],
            "moved_arm_count": len(moved),
            "rounds": {lbl: sorted(rounds[lbl]) for lbl in labels}}


def selfcheck() -> dict:
    """Three readings the comparator must get right, two of them in the direction that is easy to fake."""
    base = ("    [chromium] › e2e/a.spec.ts:1:1 › first arm\n"
            "    [chromium] › e2e/b.spec.ts:2:1 › reach \u2014 the control is hittable @320\n")
    same = base
    added = base + "    [chromium] › e2e/b.spec.ts:2:1 › reach \u2014 the control is hittable @414\n"
    moved = base.replace("@320", "@360")
    cases = {
        "identical_logs_must_read_stable": ({"r1": base, "r2": same}, "DENOMINATOR_STABLE"),
        "an_extra_arm_must_read_unstable": ({"r1": base, "r2": added}, "DENOMINATOR_UNSTABLE"),
        "an_arm_that_changes_width_must_read_unstable": ({"r1": base, "r2": moved}, "DENOMINATOR_UNSTABLE"),
        "a_single_round_must_not_claim_anything": ({"r1": base}, "NOT_MEASURED"),
    }
    out = {}
    ok = True
    for name, (rounds, expected) in cases.items():
        got = compare({lbl: reds_from_text(txt) for lbl, txt in rounds.items()})["verdict"]
        out[name] = {"expected": expected, "got": got, "as_expected": got == expected}
        ok = ok and got == expected
    out["all_cases_as_expected"] = ok
    return out


def main() -> int:
    argv = sys.argv[1:]
    if "--selfcheck" in argv:
        report = selfcheck()
        text = json.dumps(report, indent=1, ensure_ascii=False)
        if "--out" in argv:
            dest = argv[argv.index("--out") + 1]
            io.open(dest, "w", encoding="utf-8", newline="\n").write(text + "\n")
        sys.stdout.buffer.write((text + "\n").encode("utf-8", "replace"))
        print("SELFCHECK_RC=", 0 if report["all_cases_as_expected"] else 7)
        return 0 if report["all_cases_as_expected"] else 7
    if "--logs" not in argv:
        print(__doc__)
        return 2
    paths = []
    for token in argv[argv.index("--logs") + 1:]:
        if token.startswith("--"):
            break  # the next flag's own value must not be read as another log
        paths.append(token)
    rounds = {}
    for index, path in enumerate(paths, start=1):
        rounds["round%d" % index] = reds(path)
    report = compare(rounds)
    report["logs"] = paths
    report["totals_per_round"] = {("round%d" % i): totals(p) for i, p in enumerate(paths, start=1)}
    text = json.dumps(report, indent=1, ensure_ascii=False)
    if "--out" in argv:
        dest = argv[argv.index("--out") + 1]
        io.open(dest, "w", encoding="utf-8", newline="\n").write(text + "\n")
    sys.stdout.buffer.write((json.dumps({k: report[k] for k in ("verdict", "why") if k in report},
                                        ensure_ascii=False, indent=1) + "\n").encode("utf-8", "replace"))
    print("WROTE=", argv[argv.index("--out") + 1] if "--out" in argv else "stdout only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
