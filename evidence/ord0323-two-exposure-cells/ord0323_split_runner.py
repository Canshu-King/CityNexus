"""Per-leg arms in ORD-0323's matrix runner: eight legs become eight keys, and the expectations say what
each mutant may and may not redden.

`fixed` green is no longer one claim: it is eleven -- the boundary panel, the two mount-time reads, the
confirmation fold, and one leg per cell D numbered T06-T13. A leg that cannot run reddens only itself, which
is the difference between a measurement and a guess about which leg broke.
"""
from __future__ import annotations

import ast
import pathlib

P = pathlib.Path(r"D:\moodle\_qoder_spike_20260921\ord0323_run_arms_r2.py")
t = P.read_text(encoding="utf-8")
fail = []


def rep(old, new):
    global t
    if t.count(old) != 1:
        fail.append(f"{t.count(old)}x :: {old[:58]!r}")
        return
    t = t.replace(old, new)


rep('ARMS = ("N1", "N2", "N3", "N4")',
    'LEGS = ("T06", "T07", "T08", "T09", "T10", "T11", "T12", "T13")\nARMS = ("N1", "N2", "N3") + LEGS')
rep('m = re.match(r"^(N[1234])_", sp.get("title", ""))',
    'm = re.match(r"^(N[123])_", sp.get("title", "")) or re.match(r"^N4_(T\\d\\d)_", sp.get("title", ""))')
rep('''    "cell2_baseline_throw": {"file": WORKBENCH, "bytes": BASELINE_WORKBENCH,
                             "expect": dict(ALL_GREEN, N2="failed", N3="failed", N4="failed")},''',
    '''    "cell2_baseline_throw": {"file": WORKBENCH, "bytes": BASELINE_WORKBENCH,
                             "expect": dict(ALL_GREEN, **{a: "failed" for a in ("N2", "N3") + LEGS})},''')
rep('''    "cell2_fields_blind": {"patches": [(WORKBENCH, C2_COPY, C2_COPY_BLIND), (WORKBENCH, C2_FIELDS_LINE, C2_FIELDS_BLIND)],
                           "expect": dict(ALL_GREEN, N2="failed", N3="failed", N4="failed"),
                           "intended": "positive_only"},''',
    '''    "cell2_fields_blind": {"patches": [(WORKBENCH, C2_COPY, C2_COPY_BLIND), (WORKBENCH, C2_FIELDS_LINE, C2_FIELDS_BLIND)],
                           "expect": dict(ALL_GREEN, **{a: "failed" for a in ("N2", "N3") + LEGS}),
                           "intended": "positive_only"},''')
rep('''    "cell2_status_frozen": {"patches": [(WORKBENCH, C2_FIELDS_LINE, C2_STATUS_FROZEN)],
                            "expect": dict(ALL_GREEN, N3="failed", N4="failed"),
                            "intended": "attribution_only"},''',
    '''    "cell2_status_frozen": {"patches": [(WORKBENCH, C2_FIELDS_LINE, C2_STATUS_FROZEN)],
                            "expect": dict(ALL_GREEN, T12="failed"),
                            "intended": "attribution_only"},''')
rep('''                note = ""
                if a == "N4":
                    ls = rd.get("legs") or []
                    note = "legs_bad=" + json.dumps(
                        [l["cell"] for l in ls if l.get("needles_found") or not l.get("status_in_slot")
                         or l.get("foreign_status_found")], ensure_ascii=False)
                print(f"   {a} want={cfg['expect'].get(a, '-'):7s} got={str(res['per_arm'].get(a)):7s} "
                      f"leaks={json.dumps(rd.get('leaked_needles_still_on_screen'), ensure_ascii=False)[:48] if rd.get('leaked_needles_still_on_screen') is not None else '-'}"
                      f" {note[:70]} err={str(rd.get('error_head'))[:58]}")''',
    '''                own = rd.get("status_in_slot")
                found = rd.get("needles_found")
                print(f"   {a} want={cfg['expect'].get(a, '-'):7s} got={str(res['per_arm'].get(a)):7s} "
                      f"own_status={str(own):5s} needles={json.dumps(found, ensure_ascii=False)[:24] if found is not None else '-'} "
                      f"asked={rd.get('status_asked', '-')} err={str(rd.get('error_head'))[:46]}")''')
rep('''                                              "fold_code_visible", "status_line", "leaked_needles_still_on_screen", "test_status", "error_head")}''',
    '''                                              "fold_code_visible", "status_line", "leaked_needles_still_on_screen",
                                              "cell", "route", "method", "status_asked", "slot_text",
                                              "status_in_slot", "needles_found", "foreign_status_found",
                                              "internal_token_on_screen", "test_status", "error_head")}''')
rep('''                    for a in ARMS:
                rd''', '''                    for a in ARMS:
                rd''')
if t.count('if shape == "fixed" and not res["meets_expectation"]') != 1:
    fail.append("fail-fast guard missing")
rep('''            if shape == "fixed" and not res["meets_expectation"]:
                raise SystemExit("the candidate itself is not green; the matrix would only measure a broken fix")''',
    '''            if shape == "fixed" and not res["meets_expectation"]:
                raise SystemExit("the candidate itself is not green ("
                                 + json.dumps({a: res["per_arm"].get(a) for a in ARMS
                                               if res["per_arm"].get(a) != "passed"}, ensure_ascii=False)
                                 + "); the matrix would only measure a broken fix")''')
rep('  revision_of": "ord0323_run_arms.py', '  revision_of": "ord0323_run_arms.py')
P.write_text(t, encoding="utf-8", newline="\n")
if not fail:
    ast.parse(t)
    print("runner now speaks per-leg")
else:
    for f in fail:
        print("  WARN", f)
    P.write_text(t, encoding="utf-8", newline="\n")
    raise SystemExit(2)
