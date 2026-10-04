# -*- coding: utf-8 -*-
"""Leg reachability audit r2 - the predicate r1 got wrong, corrected against today's real runs.

r1 counted ANY refusal before the first mutation as a floor.  Measured truth says otherwise:
`anchor_drift_survey_r3.py` refuses when git *fails* but exits code 0 when git *succeeds with nothing* (real run
against the empty tree), so a failure-path raise is not an empty-input floor.

An empty-input floor here means a refusal that is reachable when the input exists but is EMPTY:
  - inside `if not X:` / `if len(X) == 0:` style tests, or
  - carrying floor wording (nothing / empty / enumerates / no .py / refused / ABORT-on-count).

Three cases measured today are the positive controls and the tool refuses (exit code 3) unless all three agree.
Static only - none of these legs is executed, because they push to GitHub and post to the bus.
"""
import ast
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "empty_leg_reachability_r2.json")

MUT = re.compile(r'"push",|"push"\s*\)|commit-tree|update-ref|refs/heads/|"--apply"|bus\.py|subprocess'
                 r'|os\.replace|shutil\.(move|copy)|\.write\(|"w"|\'w\'|"a\'|open\(', re.I)
MUT_STRONG = re.compile(r"commit-tree|update-ref|refs/heads/|bus\.py|subprocess\.run|\"push\"|'push'", re.I)
WRITE_TOKEN = re.compile(r"""\bopen\([^)]*['\"][wax]""", re.I)
FLOOR_MSG = re.compile(r"nothing|no such|empty|enumerates|refus|no \.py|zero|count|does not exist|missing", re.I)
RAISE = re.compile(r"raise SystemExit|sys\.exit|raise [A-Z]\w*Error|assert ")


def mutating_line(lines):
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if WRITE_TOKEN.search(s) or MUT_STRONG.search(s):
            return i, s[:130]
    return None, ""


def refuse_kind(line):
    return bool(RAISE.search(line))


def empty_tests(src, cut):
    """Locations of `if <emptiness test>:` whose body raises - the shape that bites on an empty denominator."""
    hits = []
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return hits, "unparseable"
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or node.lineno >= cut:
            continue
        t = ast.unparse(node.test)
        empty_shape = ("not " in t) or re.search(r"len\([^)]*\)\s*==\s*0", t) or t.endswith("== 0")
        if not empty_shape:
            continue
        body_txt = "\n".join(ast.unparse(n) for n in node.body)
        if RAISE.search(body_txt) or "SystemExit" in body_txt:
            hits.append({"line": node.lineno, "test": t[:100]})
    return hits, "parsed"


def analyse(path):
    name = os.path.basename(path)
    src = io.open(path, encoding="utf-8", errors="replace").read()
    lines = src.splitlines()
    cut, snippet = mutating_line(lines)
    r = {"file": name, "bytes": len(src.encode("utf-8")), "first_mutation_line": cut,
         "first_mutation": snippet}
    if cut is None:
        r["verdict"] = "no-write-leg"
        return r
    floors, state = empty_tests(src, cut)
    msg_floors = [{"line": i, "text": l.strip()[:120]} for i, l in enumerate(lines, 1)
                  if i < cut and refuse_kind(l) and FLOOR_MSG.search(l)]
    r["parse"] = state
    r["emptiness_guard_lines"] = [f["line"] for f in floors]
    r["floor_worded_refusal_lines"] = [m["line"] for m in msg_floors]
    r["failure_only_refusals_ignored"] = sum(1 for i, l in enumerate(lines, 1)
                                             if i < cut and refuse_kind(l) and not FLOOR_MSG.search(l))
    guarded = bool(floors or msg_floors)
    r["verdict"] = "guarded" if guarded else "unguarded"
    return r


KNOWN = {"block_census_r3_r1.py": "guarded",          # measured: empty listing -> named ABORT
         "anchor_drift_survey_r3.py": "unguarded",    # measured: empty tree -> exit code 0
         "empty_denominator_scan_r2.py": "guarded"}   # measured: empty root -> named ABORT


def main():
    files = sorted(f for f in os.listdir(HERE) if f.endswith(".py"))
    rows = [analyse(os.path.join(HERE, f)) for f in files]
    if not rows:
        raise SystemExit("ABORT: no .py files under %s" % HERE)
    legs = [r for r in rows if r["verdict"] in ("guarded", "unguarded")]
    counts = {"guarded": sum(1 for r in legs if r["verdict"] == "guarded"),
              "unguarded": sum(1 for r in legs if r["verdict"] == "unguarded"),
              "no-write-leg": sum(1 for r in rows if r["verdict"] == "no-write-leg")}
    by = {r["file"]: r for r in rows}
    known = {}
    for n, want in KNOWN.items():
        got = by.get(n, {}).get("verdict")
        known[n] = {"measured": want, "analyzer": got, "agrees": got == want}
    bad = [n for n, v in known.items() if not v["agrees"]]
    out = {"root": HERE, "py_files": len(rows), "write_legs": len(legs), "counts": counts,
           "known_cases": known, "mismatched_controls": bad,
           "unguarded_legs": [r for r in legs if r["verdict"] == "unguarded"],
           "legs": legs}
    json.dump(out, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"py_files": len(rows), "write_legs": len(legs), "counts": counts,
                      "known_cases": known, "mismatched_controls": bad}, ensure_ascii=False, indent=1))
    for r in out["unguarded_legs"][:12]:
        print("UNGUARDED %-34s mutation@%-5s %s" % (r["file"], r["first_mutation_line"], r["first_mutation"][:64]))
    return 3 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
