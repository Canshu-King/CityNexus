"""Self-test for the ABORT_READINGS_RED interlock in `r10_block.py` (CMDR 19:45, lane 6a150e1e).

The emitter cannot be run from this lane -- it loads its receipts from the phone lane's evidence
directory and asks for that lane's own ref -- so this test judges the interlock the way the emitter
will: the predicate that decides refusal, the artifact the refusal writes, the ordering that makes a
red reading unable to reach the page write, and the three receipts the family actually shipped.

Nothing here writes outside a scratch directory, and nothing in the emitter's own judgment was edited.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import r10_block as R  # noqa: E402  (the module under test; importing it runs no code)

GREEN_GATE = {"verdict": "GREEN", "tip": "x"}
GREEN_MUT = {"green": True, "every_arm_bit": True, "pairs_with_gate_receipt": R.GATE_RECEIPT}
GREEN_PY = {"exit": 0}

checks = []


def check(name, ok, detail):
    checks.append({"check": name, "pass": bool(ok), "detail": detail})


# 1. nothing refuses when the readings came back green
check("all_green_refuses_nothing", R.readings_red(GREEN_GATE, GREEN_MUT, GREEN_PY) == [],
      R.readings_red(GREEN_GATE, GREEN_MUT, GREEN_PY))

# 2. each red shape refuses, and names the row that refuses
for label, args, field in (
    ("gate_verdict_red", ({"verdict": "RED"}, GREEN_MUT, GREEN_PY), "verdict"),
    ("mutants_not_green", (GREEN_GATE, {"green": False, "every_arm_bit": True}, GREEN_PY), "green"),
    ("arm_never_bit", (GREEN_GATE, {"green": True, "every_arm_bit": False}, GREEN_PY), "every_arm_bit"),
    ("pytest_nonzero", (GREEN_GATE, GREEN_MUT, {"exit": 1}), "exit"),
    ("missing_field_is_red", ({}, GREEN_MUT, GREEN_PY), "verdict"),
):
    rows = R.readings_red(*args)
    check(f"refuses_on_{label}", len(rows) >= 1 and rows[0]["field"] == field, rows)

# 3. the refusal writes a named artifact and no page, into a scratch directory only
scratch = tempfile.mkdtemp(prefix="readings_red_selftest_")
try:
    page_path = os.path.join(scratch, "%s_block_page.md" % R.GEN)
    artifact = R.abort_readings_red([{"receipt": R.GATE_RECEIPT, "field": "verdict", "read": "RED",
                                      "needed": "GREEN"}],
                                    "0" * 40, "1" * 40, scratch)
    written = json.load(open(artifact, encoding="utf-8"))
    check("artifact_named", os.path.basename(artifact) == "page_abort_readings_red_%s.json" % R.GEN,
          artifact)
    check("artifact_reason_and_flag",
          written.get("reason") == "ABORT_READINGS_RED" and written.get("page_written") is False,
          {k: written.get(k) for k in ("reason", "page_written", "generation")})
    check("artifact_carries_the_refusing_row", written.get("refusing_rows") == [
        {"receipt": R.GATE_RECEIPT, "field": "verdict", "read": "RED", "needed": "GREEN"}],
        written.get("refusing_rows"))
    check("no_page_written", not os.path.exists(page_path), page_path)
finally:
    shutil.rmtree(scratch, ignore_errors=True)

# 4. ordering: the red raise sits before the page is ever opened, so red cannot post by accident
body = open(os.path.join(HERE, "r10_block.py"), encoding="utf-8").read().splitlines()
raise_at = next(i for i, line in enumerate(body) if "ABORT_READINGS_RED" in line and "raise" in line)
write_at = next(i for i, line in enumerate(body) if 'open(dest, "w"' in line)
check("refusal_precedes_page_write", raise_at < write_at, {"raise_line": raise_at + 1,
                                                          "page_write_line": write_at + 1})

# 4b. and it is live wiring inside main(), not a dead helper: the guard is `if _red:` and `_red` is
#     assigned by a call to readings_red() before any file write happens in that function
import ast
tree = ast.parse("\n".join(body))
main_fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "main")
guards = [n for n in ast.walk(main_fn)
          if isinstance(n, ast.If) and getattr(n.test, "id", None) == "_red"
          and any(isinstance(x, ast.Raise) for x in ast.walk(n))]
assigns = [n for n in ast.walk(main_fn)
           if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "_red" for t in n.targets)
           and getattr(n.value, "func", None) is not None
           and getattr(n.value.func, "id", "") == "readings_red"]
writes = [n for n in ast.walk(main_fn) if isinstance(n, ast.Call)
          and getattr(n.func, "id", "") == "open" and len(n.args) >= 2
          and isinstance(n.args[1], ast.Constant) and "w" in str(n.args[1].value)]
check("guard_is_live_in_main", len(guards) == 1 and len(assigns) == 1,
      {"guards": len(guards), "assignments": len(assigns),
       "guard_line": guards[0].lineno if guards else None})
check("guard_before_any_open_in_main",
      bool(guards) and bool(assigns) and max(guards[0].lineno, assigns[0].lineno)
      < min((n.lineno for n in writes), default=10 ** 6),
      {"guard_line": guards[0].lineno if guards else None,
       "first_open_line": min((n.lineno for n in writes), default=None)})

# 5. the receipts this family actually shipped do not refuse today's page (the interlock is not a
#    standing red): read the committed copies in ../receipts, not the phone lane's evidence dir
receipts = os.path.normpath(os.path.join(HERE, "..", "receipts"))
for gen in ("r10", "r11", "r12"):
    gate_p, mut_p = (os.path.join(receipts, "citation_gate_%s.json" % gen),
                     os.path.join(receipts, "citation_gate_%s_mutants.json" % gen))
    if not (os.path.exists(gate_p) and os.path.exists(mut_p)):
        check("shipped_receipts_present_%s" % gen, False, "absent in the tree")
        continue
    gate = json.load(open(gate_p, encoding="utf-8"))
    mut = json.load(open(mut_p, encoding="utf-8"))
    rows = R.readings_red(gate, mut, {"exit": 0})
    check("shipped_receipts_green_%s" % gen,
          gate.get("verdict") == "GREEN" and rows == [],
          {"gate_verdict": gate.get("verdict"), "mut_green": mut.get("green"),
           "every_arm_bit": mut.get("every_arm_bit"), "refusing_rows": rows})

report = os.path.join(HERE, "..", "receipts", "readings_red_selftest_r1.json")
summary = {"tool": "review/ord0500-checkin/tools/readings_red_selftest_r1.py",
           "interlock": "ABORT_READINGS_RED added to r10_block.py by CMDR 19:45",
           "checks_total": len(checks), "checks_failed": [c["check"] for c in checks if not c["pass"]],
           "checks": checks}
with open(report, "w", encoding="utf-8", newline="\n") as handle:
    json.dump(summary, handle, ensure_ascii=False, indent=1)
print(json.dumps({"checks_total": summary["checks_total"],
                  "checks_failed": summary["checks_failed"]}, ensure_ascii=False))
print("report: %s" % report)
raise SystemExit(0 if not summary["checks_failed"] else 1)
