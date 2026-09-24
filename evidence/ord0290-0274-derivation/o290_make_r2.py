"""Build o290_derive_r2.py out of the published r1 signer, then run it.

r2 changes only what ORD-0294 asked for:
  1. B2c gains a second control arm (installed on a tree with no B2a convergence at all), and
     every control names the FIELD it is supposed to discriminate;
  2. `why` is computed per cell from that cell's own numbers - never a shared sentence;
  3. a self-check reddens any cell whose `why` string is identical to another cell's.

r1's script and receipt stay on disk and on the branch untouched; the output is a new filename.
Anchors below are single lines with no escape sequences, on purpose: two earlier attempts broke
because a multi-line anchor's backslashes were eaten before Python ever saw them.
"""
import io
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
src = io.open(os.path.join(LANE, "o290_derive.py"), encoding="utf-8").read()


def sub(old, new, count=1):
    global src
    assert src.count(old) == count, ("anchor", old[:70], src.count(old))
    src = src.replace(old, new)


# 1 - extra control arm, declared after the PAIRS literal closes
sub('         "B2c_inflight_write_safe_point": ("b2c_restored", "b2c_notrestored")}',
    '         "B2c_inflight_write_safe_point": ("b2c_restored", "b2c_notrestored")}\n'
    'EXTRA_CONTROLS = {"B2c_inflight_write_safe_point": ["b2c_noconvergence"]}')

# 2 - new verdict machinery, with per-cell field-named controls
start = src.index("def cell_verdict(cell, pos, neg):")
end = src.index('out = {"order": "ORD-0290", "verifier"')
src = src[:start] + io.open(os.path.join(LANE, "_r2_verdict_block.py.txt"), encoding="utf-8").read() \
    + src[end:]

# 3 - load and judge the extra arm(s), keep their run records for the isolation section
sub("""        pr, pa_, pq = read(pa)
        nr, na_, nq = read(na)""",
    """        pr, pa_, pq = read(pa)
        nr, na_, nq = read(na)
        extra, extra_runs = {}, {}
        for xa in EXTRA_CONTROLS.get(cell, []):
            xr, xa_, xq = read(xa)
            extra[xa] = judge(xa, xr, xa_, xq)
            extra_runs[xa] = xr
            out["arms"][xa] = extra[xa]""")
sub("    P, N = judge(pa, pr, pa_, pq), judge(na, nr, na_, nq)\n"
    "    verdict, why = cell_verdict(cell, P, N)",
    "    P, N = judge(pa, pr, pa_, pq), judge(na, nr, na_, nq)\n"
    "    verdict, why, teeth = cell_verdict(cell, P, N, extra)")
sub('        "derived_result": verdict, "why": why,',
    '        "derived_result": verdict, "why": why,\n'
    '        "controls": [{"arm": a["arm"], "sha": a["installed_commit"], "discriminating_field": f,\n'
    '                      "measured": got, "expected_to_see": exp} for (a, f, got, exp) in teeth],\n'
    '        "field_lines": field_lines(P, N, extra),')
sub('        "isolation": {pa: pr["isolation"], na: nr["isolation"]},',
    '        "isolation": dict([(pa, pr["isolation"]), (na, nr["isolation"])] +\n'
    '                           [(k, v["isolation"]) for k, v in extra_runs.items()]),')

# 4 - mark the revision, add the duplicate-`why` self-check, write to a new filename
sub('out = {"order": "ORD-0290", "verifier"', 'out = {"order": "ORD-0290", "revision": "r2", "verifier"')
sub('io.open(os.path.join(LANE, "o290_derived.json"), "w", encoding="utf-8").write(',
    'whys = [v.get("why", "") for v in out["cells"].values()]\n'
    'dups = sorted({w for w in whys if whys.count(w) > 1})\n'
    'out["selftest_duplicate_why"] = {"cells": len(whys), "distinct_why_strings": len(set(whys)),\n'
    '                                 "duplicates": dups,\n'
    '                                 "result": "PASS" if not dups else "FAIL"}\n'
    'if dups:\n'
    '    for k, v in out["cells"].items():\n'
    '        if v.get("why") in dups:\n'
    '            v["derived_result"] = "SELFTEST_DUPLICATE_WHY"\n'
    'io.open(os.path.join(LANE, "o290_derived_r2.json"), "w", encoding="utf-8").write(')

io.open(os.path.join(LANE, "o290_derive_r2.py"), "w", encoding="utf-8", newline="").write(src)
import ast
ast.parse(src)
print("o290_derive_r2.py written and parses; r1 file still present:",
      os.path.exists(os.path.join(LANE, "o290_derive.py")),
      "| r1 receipt still present:", os.path.exists(os.path.join(LANE, "o290_derived.json")))
