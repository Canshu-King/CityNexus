"""Add the Q68 cell to ORD-0323's matrix: two arms, and the mutant that puts the prose fallback back.

`cell3_code_slot_back` restores only the deleted fallback line, so the leg that shows a real code must stay
green while the leg that used to dress prose as a code goes red -- the pair is what proves the fix is
"prose may not wear a code's name", not "the slot was emptied".
"""
from __future__ import annotations

import ast
import pathlib

P = pathlib.Path(r"D:\moodle\_qoder_spike_20260921\ord0323_run_arms_r2.py")
t = P.read_text(encoding="utf-8")
bad = []


def rep(old, new):
    global t
    if t.count(old) != 1:
        bad.append(f"{t.count(old)}x :: {old[:56]!r}")
        return
    t = t.replace(old, new)


rep('BOUNDARY = FE / "src/components/ProductErrorBoundary.tsx"',
    'BOUNDARY = FE / "src/components/ProductErrorBoundary.tsx"\nSHEET = FE / "src/features/planning/PlanWithAiSheet.tsx"\nSHEET_PATH = "frontend/src/features/planning/PlanWithAiSheet.tsx"')
rep('BOUNDARY_PATH = "frontend/src/components/ProductErrorBoundary.tsx"',
    'BOUNDARY_PATH = "frontend/src/components/ProductErrorBoundary.tsx"')
rep('ARMS = ("N1", "N2", "N3") + LEGS', 'ARMS = ("N1", "N2", "N3") + LEGS + ("Q68a", "Q68b")')
rep('''BASELINE_BOUNDARY = show(PARENT, BOUNDARY_PATH)''',
    '''BASELINE_SHEET = show(PARENT, SHEET_PATH)
BASELINE_BOUNDARY = show(PARENT, BOUNDARY_PATH)''')
rep('''    touched = {p: p.read_bytes() for p, _n, _r in cfg.get("patches", [])}''',
    '''    touched = {p: p.read_bytes() for p, _n, _r in cfg.get("patches", [])}''')
rep('''m = re.match(r"^(N[123])_", sp.get("title", "")) or re.match(r"^N4_(T\\\\d\\\\d)_", sp.get("title", ""))''',
    '''m = (re.match(r"^(N[123])_", sp.get("title", "")) or re.match(r"^N4_(T\\d\\d)_", sp.get("title", ""))
                     or re.match(r"^(Q68[ab])_", sp.get("title", "")))''')
rep('''    "cell2_status_frozen": {"patches": [(WORKBENCH, C2_FIELDS_LINE, C2_STATUS_FROZEN)],''',
    '''    "cell3_code_slot_back": {"patches": [(SHEET, C3_NOW, C3_WAS)],
                             "expect": dict(ALL_GREEN, Q68b="failed"),
                             "intended": "q68_only"},
    "cell2_status_frozen": {"patches": [(WORKBENCH, C2_FIELDS_LINE, C2_STATUS_FROZEN)],''')
rep('''C2_FIELD_A = "（HTTP ${status}，内容类型 ${type}）"''',
    '''C3_NOW = ("""  /* Q68 (CMDR 04:45): a slot named 原因编号 carries a code or it carries nothing. The reply's sentence\\n"""
        """     already has an attributed home in 技术详情 (Q67=①), and the caller's `|| PLACES_HTTP_n` /\\n"""
        """     `NO_PLANS_PRODUCED` fallbacks are this device's own readings. */\\n  return "";\\n}""")
C3_WAS = ("""  const detail = (body as { detail?: unknown } | null)?.detail;\\n"""
          """  return typeof detail === "string" ? detail.slice(0, 60).toUpperCase() : "";\\n}""")
C2_FIELD_A = "（HTTP ${status}，内容类型 ${type}）"''')
rep('''            ok = sha(BOUNDARY) == hashlib.sha256(show(tip, BOUNDARY_PATH)).hexdigest()''',
    '''            ok = sha(BOUNDARY) == hashlib.sha256(show(tip, BOUNDARY_PATH)).hexdigest()
            ok3 = sha(SHEET) == hashlib.sha256(show(tip, SHEET_PATH)).hexdigest()''')
rep('''            print(f"   restored boundary={ok} workbench={ok2} src dirty={dirty[:60]!r}")
            if not (ok and ok2):''',
    '''            print(f"   restored boundary={ok} workbench={ok2} sheet={ok3} src dirty={dirty[:60]!r}")
            if not (ok and ok2 and ok3):''')
rep('''            "files": {''', '''            "files": {
            "PlanWithAiSheet.tsx": {"candidate_sha256": sha(SHEET),
                                    "baseline_sha256": hashlib.sha256(BASELINE_SHEET).hexdigest()},''')
rep('''            if "bytes" in cfg:''', '''            if "bytes" in cfg:''')
P.write_text(t, encoding="utf-8", newline="\n")
try:
    ast.parse(t)
except SyntaxError as e:
    bad.append(f"does not parse: {e}")
if bad:
    for x in bad:
        print("  WARN", x)
else:
    print("runner knows the Q68 cell now")
