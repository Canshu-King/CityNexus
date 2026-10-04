# -*- coding: utf-8 -*-
"""Which of this lane's own shipping legs would self-report green on an empty denominator?

Question per leg file: before the FIRST mutating statement (git push / commit-tree / contents POST / bus send /
file write), is there any refusal an empty input could reach - a `raise SystemExit(...)`, an `assert`, or a
floor over an empty collection (`if not X`, `len(X) == 0`, ABORT-style wording)?

Static only: these scripts push to GitHub and post to the bus, so none of them is executed here.  The analyzer is
validated against three cases already measured by real runs today:
  block_census_r3_r1.py            guarded   (empty listing -> named ABORT, measured)
  anchor_drift_survey_r3.py        unguarded (empty tree -> exit code 0, measured)
  empty_denominator_scan_r2.py     guarded   (empty root -> named ABORT, measured)

The self-test refuses to report anything when the denominator is empty, and fails if the three known cases
do not come out as measured.
"""
import ast
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "empty_leg_reachability_r1.json")

MUTATE_RE = re.compile(
    r'"push"|\bpush\b.*origin|commit-tree|update-ref|contents|bus\.py|send\b.*--kind'
    r'|open\([^)]*["\'][wax]', re.I)
REFUSE_RE = re.compile(r"raise SystemExit|sys\.exit|assert \w|raise [A-Z]\w*Error|HookGuard")
FLOOR_WORDS = re.compile(r"nothing|no such|empty|enumerates|refus|ABORT|no \.py|zero", re.I)

KNOWN = {"block_census_r3_r1.py": "guarded",
         "anchor_drift_survey_r3.py": "unguarded",
         "empty_denominator_scan_r2.py": "guarded"}


def first_mutating_line(src):
    for i, line in enumerate(src.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#") or s.startswith('"'):
            continue
        if MUTATE_RE.search(s):
            return i, s[:120]
    return None, ""


def refusal_points(src):
    out = []
    for i, line in enumerate(src.splitlines(), 1):
        if REFUSE_RE.search(line):
            out.append({"line": i, "text": line.strip()[:120], "floor_word": bool(FLOOR_WORDS.search(line))})
    return out


def empty_floors_before(src, cut):
    """`if not X:` / `if len(X) == 0` style guards whose test appears before the first mutation."""
    hits = []
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return hits, "unparseable"
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and node.lineno < cut:
            t = ast.dump(node.test)
            if ("UnOp(Not" in t or "Compare" in t and ("Constant(value=0)" in t or "Constant(value=False)" in t)):
                body = ast.dump(node.body[0]) if node.body else ""
                hits.append({"line": node.lineno, "refuses": "Raise" in body or "Assert" in body,
                             "test": ast.unparse(node.test)[:90]})
    return hits, "parsed"


def analyse(path):
    name = os.path.basename(path)
    src = io.open(path, encoding="utf-8", errors="replace").read()
    cut, snippet = first_mutating_line(src)
    refs = refusal_points(src)
    res = {"file": name, "bytes": len(src.encode("utf-8")), "first_mutation_line": cut,
           "first_mutation": snippet, "refusal_points": len(refs),
           "refusal_before_mutation": [r["line"] for r in refs if cut and r["line"] < cut]}
    if cut is None:
        res["verdict"] = "no-mutation-leg"
        return res
    floors, parse_state = empty_floors_before(src, cut)
    res["empty_floor_before_mutation"] = [f["line"] for f in floors if f["refuses"]]
    res["parse"] = parse_state
    guarded = bool(res["refusal_before_mutation"]) or bool(res["empty_floor_before_mutation"])
    res["verdict"] = "guarded" if guarded else "unguarded"
    return res


def main():
    files = sorted(f for f in os.listdir(HERE) if f.endswith(".py") and os.path.isfile(os.path.join(HERE, f)))
    rows = [analyse(os.path.join(HERE, f)) for f in files]
    if not rows:
        raise SystemExit("ABORT: no .py legs under %s - refusing to call an empty denominator a clean audit" % HERE)
    legs = [r for r in rows if r["verdict"] in ("guarded", "unguarded")]
    counts = {"guarded": sum(1 for r in legs if r["verdict"] == "guarded"),
              "unguarded": sum(1 for r in legs if r["verdict"] == "unguarded"),
              "no-mutation-leg": sum(1 for r in rows if r["verdict"] == "no-mutation-leg")}
    known = {}
    by_name = {r["file"]: r for r in rows}
    for name, want in KNOWN.items():
        got = by_name.get(name, {}).get("verdict")
        known[name] = {"expected_from_real_runs": want, "analyzer_says": got, "agrees": got == want}
    out = {"root": HERE, "py_files": len(rows), "shipping_legs": len(legs), "counts": counts,
           "known_cases": known, "self_test_empty_denominator": "refuses above",
           "legs": [r for r in legs]}
    json.dump(out, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"py_files": len(rows), "shipping_legs": len(legs), "counts": counts,
                      "known_cases": known}, ensure_ascii=False, indent=1))
    for r in legs:
        if r["verdict"] == "unguarded":
            print("UNGUARDED %-38s first mutation at line %-5s %s" %
                  (r["file"], r["first_mutation_line"], r["first_mutation"][:70]))
    bad = [n for n, v in known.items() if not v["agrees"]]
    return 3 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
